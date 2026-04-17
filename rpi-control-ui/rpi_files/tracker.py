# save as tracker.py
import cv2
import numpy as np
from picamera2 import Picamera2
from adafruit_pca9685 import PCA9685
import board
import busio
import time

# ─────────────────────────────────────────────
# PCA9685 SERVO SETUP
# ─────────────────────────────────────────────
i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 50

SERVO_MIN = 120
SERVO_MAX = 520

PAN_CHANNEL  = 0
TILT_CHANNEL = 15

pan_angle  = 90.0
tilt_angle = 90.0

PAN_MIN, PAN_MAX   = 10, 170
TILT_MIN, TILT_MAX = 30, 150


def angle_to_duty(angle):
    angle = max(0, min(180, angle))
    pulse = SERVO_MIN + (angle / 180.0) * (SERVO_MAX - SERVO_MIN)
    duty = int(pulse / 4096 * 65535)
    return duty


def set_servo(channel, angle):
    pca.channels[channel].duty_cycle = angle_to_duty(angle)


# ─────────────────────────────────────────────
# PID CONTROLLER
# ─────────────────────────────────────────────
class PID:
    def __init__(self, kp, ki, kd, output_min, output_max):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = time.time()

    def compute(self, error):
        current_time = time.time()
        dt = current_time - self.prev_time
        if dt <= 0:
            dt = 0.01

        p = self.kp * error

        self.integral += error * dt
        self.integral = max(-50, min(50, self.integral))
        i = self.ki * self.integral

        derivative = (error - self.prev_error) / dt
        d = self.kd * derivative

        output = p + i + d
        output = max(self.output_min, min(self.output_max, output))

        self.prev_error = error
        self.prev_time = current_time
        return output

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = time.time()


# ─────────────────────────────────────────────
# BLUE CAP DETECTOR
# ─────────────────────────────────────────────
def detect_blue_cap(frame):
    blurred = cv2.GaussianBlur(frame, (11, 11), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    # *** UPDATE THESE with values from hsvfind.py ***
    lower_blue = np.array([100, 120, 50])
    upper_blue = np.array([130, 255, 255])

    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.erode(mask, kernel, iterations=2)
    mask = cv2.dilate(mask, kernel, iterations=2)

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if len(contours) == 0:
        return None, mask

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)

    if area < 300:
        return None, mask

    ((cx, cy), radius) = cv2.minEnclosingCircle(largest)

    if radius < 8:
        return None, mask

    return (int(cx), int(cy), int(radius)), mask


# ─────────────────────────────────────────────
# CAMERA SETUP (matching your working style)
# ─────────────────────────────────────────────
print("Starting camera...")
picam2 = Picamera2()

try:
    config = picam2.create_video_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
    picam2.configure(config)
except Exception:
    print("Video config failed, trying still config...")
    config = picam2.create_still_configuration(
        main={"size": (640, 480)}
    )
    picam2.configure(config)

picam2.start()
time.sleep(2)

# Verify camera works
test = picam2.capture_array()
print(f"Camera OK! Frame: {test.shape}")

FRAME_W = test.shape[1]
FRAME_H = test.shape[0]
CENTER_X = FRAME_W // 2
CENTER_Y = FRAME_H // 2
DEAD_ZONE = 20

print(f"Frame size: {FRAME_W}x{FRAME_H}")
print(f"Center: ({CENTER_X}, {CENTER_Y})")

# ─────────────────────────────────────────────
# PID CONTROLLERS
# ─────────────────────────────────────────────
pan_pid  = PID(kp=0.05, ki=0.005, kd=0.01, output_min=-5, output_max=5)
tilt_pid = PID(kp=0.05, ki=0.005, kd=0.01, output_min=-5, output_max=5)

# ─────────────────────────────────────────────
# INITIALIZE SERVOS
# ─────────────────────────────────────────────
set_servo(PAN_CHANNEL, pan_angle)
set_servo(TILT_CHANNEL, tilt_angle)
time.sleep(1)

print("=" * 50)
print("  BLUE CAP TRACKER RUNNING")
print("  Press 'q' to quit | 'c' to center")
print("=" * 50)

no_detection_count = 0
use_display = True

# Check if display is available
try:
    cv2.namedWindow("Test")
    cv2.destroyWindow("Test")
except Exception:
    print("No display available - running headless mode")
    use_display = False

try:
    while True:
        frame = picam2.capture_array()

        # Convert RGB to BGR for OpenCV
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        else:
            frame_bgr = frame

        # Detect blue cap
        detection, mask = detect_blue_cap(frame_bgr)

        if detection is not None:
            cx, cy, radius = detection
            no_detection_count = 0

            error_x = cx - CENTER_X
            error_y = cy - CENTER_Y

            # Apply PID
            if abs(error_x) > DEAD_ZONE:
                pan_adj = pan_pid.compute(error_x)
                pan_angle += pan_adj  # flip sign if wrong direction
            else:
                pan_pid.reset()

            if abs(error_y) > DEAD_ZONE:
                tilt_adj = tilt_pid.compute(error_y)
                tilt_angle -= tilt_adj  # flip sign if wrong direction
            else:
                tilt_pid.reset()

            # Clamp
            pan_angle  = max(PAN_MIN, min(PAN_MAX, pan_angle))
            tilt_angle = max(TILT_MIN, min(TILT_MAX, tilt_angle))

            # Move servos
            set_servo(PAN_CHANNEL, pan_angle)
            set_servo(TILT_CHANNEL, tilt_angle)

            print(f"CAP at ({cx},{cy}) | Error ({error_x},{error_y}) | "
                  f"Pan: {pan_angle:.1f} Tilt: {tilt_angle:.1f}")

            if use_display:
                cv2.circle(frame_bgr, (cx, cy), radius, (0, 255, 0), 2)
                cv2.circle(frame_bgr, (cx, cy), 3, (0, 0, 255), -1)

        else:
            no_detection_count += 1
            if no_detection_count > 30:
                pan_pid.reset()
                tilt_pid.reset()

            if no_detection_count % 15 == 0:
                print("No blue cap detected...")

        if use_display:
            cv2.line(frame_bgr, (CENTER_X-20, CENTER_Y),
                     (CENTER_X+20, CENTER_Y), (255,255,255), 1)
            cv2.line(frame_bgr, (CENTER_X, CENTER_Y-20),
                     (CENTER_X, CENTER_Y+20), (255,255,255), 1)
            cv2.imshow("Tracker", frame_bgr)
            cv2.imshow("Mask", mask)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                pan_angle = 90.0
                tilt_angle = 90.0
                set_servo(PAN_CHANNEL, pan_angle)
                set_servo(TILT_CHANNEL, tilt_angle)
                pan_pid.reset()
                tilt_pid.reset()
                print("Centered!")

except KeyboardInterrupt:
    print("\nStopped by Ctrl+C")

finally:
    print("Cleaning up...")
    set_servo(PAN_CHANNEL, 90)
    set_servo(TILT_CHANNEL, 90)
    pca.deinit()
    picam2.close()
    if use_display:
        cv2.destroyAllWindows()
    print("Done.")