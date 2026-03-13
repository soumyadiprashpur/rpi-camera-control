from flask import Flask
from flask_cors import CORS
import paramiko

app = Flask(__name__)
CORS(app)

RPI_IP = "10.92.193.19"
RPI_USER = "pan_tilt"
RPI_PASS = "9876543210"

ssh = None


def connect_ssh():

    global ssh

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(RPI_IP, username=RPI_USER, password=RPI_PASS)

    print("Connected to Raspberry Pi")


def run_command(cmd):

    stdin, stdout, stderr = ssh.exec_command(cmd)

    print(stdout.read().decode())
    print(stderr.read().decode())


def stop_all():

    run_command("pkill -f cam_open.py")
    run_command("pkill -f face_detect.py")
    run_command("pkill -f red_detect.py")


@app.route("/connect")
def connect():

    connect_ssh()
    return "Connected"


@app.route("/disconnect")
def disconnect():

    global ssh

    if ssh:
        ssh.close()

    return "Disconnected"


@app.route("/camera")
def camera():

    stop_all()

    run_command("DISPLAY=:0 python3 cam_open.py &")

    return "Camera started"


@app.route("/face")
def face():

    stop_all()

    run_command("DISPLAY=:0 python3 face_detect.py &")

    return "Face detection started"


@app.route("/red")
def red():

    stop_all()

    run_command("DISPLAY=:0 python3 red_detect.py &")

    return "Red detection started"


@app.route("/kill")
def kill():

    stop_all()

    return "All camera programs stopped"


@app.route("/shutdown")
def shutdown():

    run_command("sudo shutdown now")

    return "Raspberry Pi shutting down"


if __name__ == "__main__":

    app.run(port=5000)
