#!/usr/bin/env python3
"""Camera streaming with face detection (Raspberry Pi optimized)"""

import cv2
import os
from flask import Flask, Response
import argparse

app = Flask(__name__)

# -------------------------------
# Load Haar Cascade
# -------------------------------

cascade_paths = [
    '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
    '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml',
    '/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
]

cascade_path = None

# try cv2.data first
try:
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
except:
    pass

# fallback search
if not cascade_path or not os.path.exists(cascade_path):
    for path in cascade_paths:
        if os.path.exists(path):
            cascade_path = path
            break

if cascade_path is None:
    print("ERROR: Haar cascade not found.")
    print("Install using: sudo apt install opencv-data")
    exit(1)

face_cascade = cv2.CascadeClassifier(cascade_path)

if face_cascade.empty():
    print("ERROR: Failed to load cascade file.")
    exit(1)

print(f"Loaded cascade from: {cascade_path}")


# -------------------------------
# Open Camera (ONLY ONCE)
# -------------------------------

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 24)

if not cap.isOpened():
    print("ERROR: Camera failed to open")
    exit(1)


# -------------------------------
# Frame Generator
# -------------------------------

def generate_frames():
    while True:

        success, frame = cap.read()

        if not success:
            continue

        # Resize frame for faster detection
        small = cv2.resize(frame, (320, 240))

        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.3,
            minNeighbors=5,
            minSize=(30, 30)
        )

        # Draw boxes (scale back to original size)
        for (x, y, w, h) in faces:
            x *= 2
            y *= 2
            w *= 2
            h *= 2

            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            cv2.putText(
                frame,
                "Face",
                (x, y-10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0,255,0),
                2
            )

        cv2.putText(
            frame,
            f"Faces: {len(faces)}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0,255,0),
            2
        )

        ret, buffer = cv2.imencode(
            '.jpg',
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, 80]
        )

        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' +
               frame_bytes +
               b'\r\n')


# -------------------------------
# Flask Routes
# -------------------------------

@app.route('/stream')
def stream():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/health')
def health():
    return "OK"


# -------------------------------
# Main
# -------------------------------

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)

    args = parser.parse_args()

    print(f"Starting Face Detection Stream on port {args.port}")

    app.run(
        host='0.0.0.0',
        port=args.port,
        threaded=True
    )