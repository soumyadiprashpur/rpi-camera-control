#!/usr/bin/env python3
"""High-quality RPi Camera streaming server using rpicam-vid"""

import subprocess
import signal
import sys
import threading
import time
from flask import Flask, Response
import argparse

app = Flask(__name__)

# Global process reference
camera_process = None


def cleanup(signum=None, frame=None):
    """Clean up camera process on exit"""
    global camera_process
    if camera_process:
        camera_process.terminate()
        camera_process.wait()
        camera_process = None
    sys.exit(0)


signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)


def generate_mjpeg_frames():
    """
    Use rpicam-vid to capture high-quality frames.
    Outputs MJPEG directly - no re-encoding needed!
    """
    global camera_process

    cmd = [
        "rpicam-vid",
        "--codec", "mjpeg",        # Direct MJPEG output (high quality)
        "--width", "1280",          # HD resolution
        "--height", "720",
        "--framerate", "30",
        "--quality", "90",          # JPEG quality (1-100)
        "--nopreview",              # No desktop preview
        "--timeout", "0",           # Run forever
        "--flush",                  # Flush output immediately
        "-o", "-"                   # Output to stdout
    ]

    try:
        camera_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )

        # Read MJPEG frames from stdout
        # MJPEG frames start with FFD8 and end with FFD9
        buffer = b""

        while True:
            chunk = camera_process.stdout.read(4096)
            if not chunk:
                break

            buffer += chunk

            # Find complete JPEG frames
            while True:
                start = buffer.find(b'\xff\xd8')  # JPEG start marker
                if start == -1:
                    buffer = b""
                    break

                end = buffer.find(b'\xff\xd9', start + 2)  # JPEG end marker
                if end == -1:
                    # Keep from start marker onwards, discard before
                    buffer = buffer[start:]
                    break

                # Extract complete JPEG frame
                frame = buffer[start:end + 2]
                buffer = buffer[end + 2:]

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + str(len(frame)).encode() + b'\r\n'
                       b'\r\n' + frame + b'\r\n')

    except Exception as e:
        print(f"❌ Camera error: {e}")
    finally:
        if camera_process:
            camera_process.terminate()
            camera_process.wait()
            camera_process = None


@app.route('/stream')
def stream():
    return Response(
        generate_mjpeg_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Connection': 'keep-alive'
        }
    )


@app.route('/health')
def health():
    return "OK"


@app.route('/snapshot')
def snapshot():
    """Capture a single high-res snapshot"""
    cmd = [
        "rpicam-still",
        "--width", "1920",
        "--height", "1080",
        "--quality", "95",
        "--nopreview",
        "--timeout", "500",
        "-o", "-"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=5)
        if result.returncode == 0:
            return Response(
                result.stdout,
                mimetype='image/jpeg',
                headers={'Content-Disposition': 'inline; filename=snapshot.jpg'}
            )
    except Exception as e:
        return f"Error: {e}", 500

    return "Snapshot failed", 500


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--quality', type=int, default=90)
    args = parser.parse_args()

    print(f"📷 Starting RPi Camera stream: {args.width}x{args.height} @ {args.fps}fps")
    print(f"🌐 Stream URL: http://0.0.0.0:{args.port}/stream")

    app.run(host='0.0.0.0', port=args.port, threaded=True)