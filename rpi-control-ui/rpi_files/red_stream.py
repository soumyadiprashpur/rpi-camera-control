#!/usr/bin/env python3
"""Camera streaming with red color detection (Raspberry Pi optimized)"""

import cv2
import numpy as np
from flask import Flask, Response
import argparse

app = Flask(__name__)

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

        # Resize for faster processing
        small = cv2.resize(frame, (320, 240))

        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)

        # Red ranges (HSV wrap-around)
        lower_red1 = np.array([0,100,100])
        upper_red1 = np.array([10,255,255])

        lower_red2 = np.array([160,100,100])
        upper_red2 = np.array([180,255,255])

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)

        mask = mask1 | mask2

        # Clean mask
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        red_count = 0

        for contour in contours:

            area = cv2.contourArea(contour)

            if area > 500:

                red_count += 1

                x, y, w, h = cv2.boundingRect(contour)

                # scale back to original frame
                x *= 2
                y *= 2
                w *= 2
                h *= 2

                cv2.rectangle(frame, (x,y), (x+w,y+h), (0,0,255), 2)

                cv2.putText(
                    frame,
                    "RED",
                    (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0,0,255),
                    2
                )

        cv2.putText(
            frame,
            f"Red Objects: {red_count}",
            (10,30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0,0,255),
            2
        )

        ret, buffer = cv2.imencode(
            ".jpg",
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

    print(f"Starting Red Detection Stream on port {args.port}")

    app.run(
        host='0.0.0.0',
        port=args.port,
        threaded=True
    )