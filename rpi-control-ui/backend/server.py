from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import paramiko
import requests
import time
import re

app = Flask(__name__)
CORS(app)

RPI_IP = "10.92.193.19"
RPI_USER = "pan_tilt"
RPI_PASS = "9876543210"
STREAM_PORT = 8080

ssh = None
current_mode = None


def connect_ssh():
    global ssh
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(RPI_IP, username=RPI_USER, password=RPI_PASS)
    print("Connected to Raspberry Pi")


def run_command(cmd, timeout=10):
    if ssh is None:
        return "", "Not connected"
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        return out, err
    except Exception as e:
        return "", str(e)


def stop_all_streams():
    global current_mode
    run_command("pkill -f cam_stream.py")
    run_command("pkill -f face_stream.py")
    run_command("pkill -f red_stream.py")
    run_command("pkill -f cam_open.py")
    run_command("pkill -f face_detect.py")
    run_command("pkill -f red_detect.py")
    current_mode = None
    time.sleep(0.5)


def wait_for_stream(timeout=8):
    url = f"http://{RPI_IP}:{STREAM_PORT}/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                return True
        except:
            pass
        time.sleep(0.3)
    return False


# ========== CONNECTION ==========

@app.route("/connect")
def connect():
    try:
        connect_ssh()
        return jsonify({"status": "success", "message": "Connected"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/disconnect")
def disconnect():
    global ssh
    try:
        stop_all_streams()
    except:
        pass
    if ssh:
        ssh.close()
        ssh = None
    return jsonify({"status": "success", "message": "Disconnected"})


# ========== CAMERA ==========

@app.route("/camera")
def camera():
    global current_mode
    stop_all_streams()
    run_command(f"nohup python3 cam_stream.py --port {STREAM_PORT} > /dev/null 2>&1 &")
    if wait_for_stream():
        current_mode = "camera"
        return jsonify({"status": "success", "message": "Camera started", "stream_url": f"http://{RPI_IP}:{STREAM_PORT}/stream"})
    return jsonify({"status": "error", "message": "Stream failed to start"}), 500


@app.route("/face")
def face():
    global current_mode
    stop_all_streams()
    run_command(f"nohup python3 face_stream.py --port {STREAM_PORT} > /dev/null 2>&1 &")
    if wait_for_stream():
        current_mode = "face"
        return jsonify({"status": "success", "message": "Face detection started", "stream_url": f"http://{RPI_IP}:{STREAM_PORT}/stream"})
    return jsonify({"status": "error", "message": "Stream failed to start"}), 500


@app.route("/red")
def red():
    global current_mode
    stop_all_streams()
    run_command(f"nohup python3 red_stream.py --port {STREAM_PORT} > /dev/null 2>&1 &")
    if wait_for_stream():
        current_mode = "red"
        return jsonify({"status": "success", "message": "Red detection started", "stream_url": f"http://{RPI_IP}:{STREAM_PORT}/stream"})
    return jsonify({"status": "error", "message": "Stream failed to start"}), 500


@app.route("/kill")
def kill():
    stop_all_streams()
    return jsonify({"status": "success", "message": "All stopped"})


@app.route("/shutdown")
def shutdown():
    stop_all_streams()
    run_command("sudo shutdown now")
    return jsonify({"status": "success", "message": "Shutting down"})


@app.route("/reboot")
def reboot():
    stop_all_streams()
    run_command("sudo reboot")
    return jsonify({"status": "success", "message": "Rebooting"})


# ========== VIDEO PROXY ==========

@app.route("/video_feed")
def video_feed():
    def proxy_stream():
        try:
            r = requests.get(f"http://{RPI_IP}:{STREAM_PORT}/stream", stream=True, timeout=10)
            for chunk in r.iter_content(chunk_size=4096):
                yield chunk
        except:
            pass
    return Response(proxy_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')


# ========== SYSTEM STATS ==========

@app.route("/system/stats")
def system_stats():
    try:
        cpu_out, _ = run_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1")
        cpu = round(float(cpu_out)) if cpu_out else 0

        ram_out, _ = run_command("free | grep Mem | awk '{printf \"%.0f\", $3/$2 * 100}'")
        ram = int(ram_out) if ram_out else 0

        temp_out, _ = run_command("cat /sys/class/thermal/thermal_zone0/temp")
        temp = round(int(temp_out) / 1000, 1) if temp_out else 0

        disk_out, _ = run_command("df / | tail -1 | awk '{print $5}' | tr -d '%'")
        disk = int(disk_out) if disk_out else 0

        model_out, _ = run_command("cat /proc/device-tree/model 2>/dev/null || echo 'Raspberry Pi'")
        model = model_out.replace('\x00', '').strip() if model_out else "Raspberry Pi"

        os_out, _ = run_command("cat /etc/os-release | grep PRETTY_NAME | cut -d'\"' -f2")
        kernel_out, _ = run_command("uname -r")
        python_out, _ = run_command("python3 --version")
        uptime_out, _ = run_command("uptime -p")

        total_ram_out, _ = run_command("free -h | grep Mem | awk '{print $2}'")
        total_disk_out, _ = run_command("df -h / | tail -1 | awk '{print $2}'")

        # Top processes
        proc_out, _ = run_command("ps aux --sort=-%cpu | head -8 | tail -7 | awk '{printf \"%s|%s|%s|%s\\n\", $2, $11, $3, $4}'")
        processes = []
        if proc_out:
            for line in proc_out.strip().split("\n"):
                parts = line.split("|")
                if len(parts) == 4:
                    processes.append({
                        "pid": parts[0],
                        "name": parts[1][:30],
                        "cpu": parts[2],
                        "mem": parts[3]
                    })

        return jsonify({
            "status": "success",
            "data": {
                "cpu": cpu, "ram": ram, "temp": temp, "disk": disk,
                "model": model, "os": os_out or "--", "kernel": kernel_out or "--",
                "python": python_out or "--", "sys_uptime": uptime_out or "--",
                "total_ram": total_ram_out or "--", "total_disk": total_disk_out or "--",
                "processes": processes
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ========== NETWORK INFO ==========

@app.route("/system/network")
def system_network():
    try:
        hostname_out, _ = run_command("hostname")
        ip_out, _ = run_command("hostname -I | awk '{print $1}'")
        gateway_out, _ = run_command("ip route | grep default | awk '{print $3}'")
        dns_out, _ = run_command("cat /etc/resolv.conf | grep nameserver | head -1 | awk '{print $2}'")

        # Get primary interface info
        iface_out, _ = run_command("ip -o addr show | grep 'inet ' | grep -v '127.0.0.1'")
        mac_out, _ = run_command("cat /sys/class/net/$(ip route | grep default | awk '{print $5}')/address 2>/dev/null")
        subnet_out, _ = run_command("ip -o addr show | grep 'inet ' | grep -v '127.0.0.1' | head -1 | awk '{print $4}'")

        # Connection type
        default_iface, _ = run_command("ip route | grep default | awk '{print $5}'")
        conn_type = "WiFi" if default_iface and "wlan" in default_iface else "Ethernet"

        # Signal strength (WiFi only)
        signal = "--"
        if "wlan" in (default_iface or ""):
            signal_out, _ = run_command("iwconfig wlan0 2>/dev/null | grep 'Signal level' | awk -F'=' '{print $3}' | awk '{print $1}'")
            if signal_out:
                signal = f"{signal_out} dBm"

        # Build interfaces list
        interfaces = []
        if_out, _ = run_command("ip -o link show | awk '{print $2}' | tr -d ':'")
        if if_out:
            for iface_name in if_out.strip().split("\n"):
                iface_name = iface_name.strip()
                if not iface_name or iface_name == "lo":
                    continue
                iface_ip_out, _ = run_command(f"ip -o addr show {iface_name} 2>/dev/null | grep 'inet ' | awk '{{print $4}}'")
                iface_status_out, _ = run_command(f"cat /sys/class/net/{iface_name}/operstate 2>/dev/null")
                iface_type = "WiFi" if "wlan" in iface_name else "Ethernet" if "eth" in iface_name else "Virtual"
                interfaces.append({
                    "name": iface_name,
                    "ip": iface_ip_out or "N/A",
                    "status": "UP" if iface_status_out and "up" in iface_status_out.lower() else "DOWN",
                    "type": iface_type
                })

        return jsonify({
            "status": "success",
            "data": {
                "hostname": hostname_out or "--",
                "ip": ip_out or "--",
                "subnet": subnet_out or "--",
                "gateway": gateway_out or "--",
                "mac": mac_out or "--",
                "dns": dns_out or "--",
                "conn_type": conn_type,
                "signal": signal,
                "latency": "--",
                "interfaces": interfaces
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ========== PING TEST ==========

@app.route("/system/ping")
def system_ping():
    try:
        ping_out, _ = run_command("ping -c 4 8.8.8.8 2>/dev/null | tail -1")
        # Parse: rtt min/avg/max/mdev = 1.234/5.678/9.012/3.456 ms
        loss_out, _ = run_command("ping -c 4 8.8.8.8 2>/dev/null | grep 'packet loss' | awk '{print $6}'")

        min_val = avg_val = max_val = "--"
        if ping_out and "=" in ping_out:
            stats = ping_out.split("=")[1].strip().split("/")
            if len(stats) >= 3:
                min_val = stats[0].strip()
                avg_val = stats[1].strip()
                max_val = stats[2].strip()

        return jsonify({
            "status": "success",
            "data": {
                "min": min_val, "avg": avg_val, "max": max_val,
                "loss": loss_out or "--"
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ========== TERMINAL ==========

@app.route("/terminal", methods=["POST"])
def terminal():
    data = request.get_json()
    cmd = data.get("command", "")
    if not cmd:
        return jsonify({"stdout": "", "stderr": "No command provided"})

    # Block dangerous commands
    dangerous = ["rm -rf /", "mkfs", "dd if="]
    for d in dangerous:
        if d in cmd:
            return jsonify({"stdout": "", "stderr": f"Blocked dangerous command: {d}"})

    out, err = run_command(cmd, timeout=15)
    return jsonify({"stdout": out, "stderr": err})


# ========== SETTINGS ==========

@app.route("/settings", methods=["POST"])
def update_settings():
    global RPI_IP, RPI_USER, RPI_PASS, STREAM_PORT
    data = request.get_json()

    RPI_IP = data.get("ip", RPI_IP)
    RPI_USER = data.get("username", RPI_USER)
    RPI_PASS = data.get("password", RPI_PASS)
    STREAM_PORT = data.get("stream_port", STREAM_PORT)

    return jsonify({"status": "success", "message": "Settings updated"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)