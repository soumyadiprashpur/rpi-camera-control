# #!/usr/bin/env python3
# """Simple camera streaming server - no detection"""

# import cv2
# from flask import Flask, Response
# import argparse

# app = Flask(__name__)

# def generate_frames():
#     cap = cv2.VideoCapture(0)
#     cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
#     cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
#     cap.set(cv2.CAP_PROP_FPS, 30)
    
#     while True:
#         success, frame = cap.read()
#         if not success:
#             break
        
#         ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
#         if not ret:
#             continue
            
#         yield (b'--frame\r\n'
#                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    
#     cap.release()

# @app.route('/stream')
# def stream():
#     return Response(generate_frames(),
#                     mimetype='multipart/x-mixed-replace; boundary=frame')

# @app.route('/health')
# def health():
#     return "OK"

# if __name__ == '__main__':
#     parser = argparse.ArgumentParser()
#     parser.add_argument('--port', type=int, default=8080)
#     args = parser.parse_args()
#     app.run(host='0.0.0.0', port=args.port, threaded=True)


# code for rpi cam
#!/usr/bin/env python3
"""Simple camera streaming server - RPI Camera version"""

import cv2
from flask import Flask, Response
import argparse

app = Flask(__name__)

def generate_frames():
    # GStreamer pipeline for Raspberry Pi camera
    pipeline = (
        "libcamerasrc ! "
        "video/x-raw,width=640,height=480,framerate=30/1 ! "
        "videoconvert ! "
        "appsink"
    )

    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("❌ Cannot open RPI camera")
        return

    while True:
        success, frame = cap.read()
        if not success:
            break
        
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            continue
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    
    cap.release()

@app.route('/stream')
def stream():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/health')
def health():
    return "OK"

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=args.port, threaded=True)