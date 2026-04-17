# save as tracker.py
import cv2
import numpy as np
from picamera2 import Picamera2
from adafruit_pca9685 import PCA9685
import board
import busio
import time
import math

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
    return int(pulse / 4096 * 65535)


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

        # Frame-based derivative ignores time spikes
        d = self.kd * (error - self.prev_error) 

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
# KALMAN FILTER SETUP
# ─────────────────────────────────────────────
kalman = cv2.KalmanFilter(4, 2)

# State = [x, y, vx, vy]
kalman.measurementMatrix = np.array([
    [1, 0, 0, 0],
    [0, 1, 0, 0]
], np.float32)

kalman.transitionMatrix = np.array([
    [1, 0, 1, 0],
    [0, 1, 0, 1],
    [0, 0, 1, 0],
    [0, 0, 0, 1]
], np.float32)

# Let the filter adapt to sudden, fast movements
kalman.processNoiseCov = np.eye(4, dtype=np.float32) * 0.1 
kalman.measurementNoiseCov = np.eye(2, dtype=np.float32) * 0.05


# ─────────────────────────────────────────────
# Green CAP DETECTOR
# ─────────────────────────────────────────────
def detect_blue_cap(frame):
    blurred = cv2.GaussianBlur(frame, (11, 11), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    lower_blue = np.array([50, 130, 50])
    upper_blue = np.array([66, 255, 255])

    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.erode(mask, kernel, iterations=2)
    mask = cv2.dilate(mask, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None, mask

    largest = max(contours, key=cv2.contourArea)

    if cv2.contourArea(largest) < 300:
        return None, mask

    ((cx, cy), radius) = cv2.minEnclosingCircle(largest)

    if radius < 8:
        return None, mask

    return (int(cx), int(cy), int(radius)), mask


# ─────────────────────────────────────────────
# CAMERA SETUP
# ─────────────────────────────────────────────
picam2 = Picamera2()
config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
picam2.configure(config)
picam2.start()
time.sleep(2)

test = picam2.capture_array()

FRAME_W = test.shape[1]
FRAME_H = test.shape[0]
CENTER_X = FRAME_W // 2
CENTER_Y = FRAME_H // 2

DEAD_ZONE = 15

# ─────────────────────────────────────────────
# PID (tuned)
# ─────────────────────────────────────────────
pan_pid  = PID(0.015, 0.000, 0.025, -12, 12) 
tilt_pid = PID(0.012, 0.000, 0.020, -8, 8)

# ─────────────────────────────────────────────
# STATE MACHINE SETUP
# ─────────────────────────────────────────────
system_state = "TRACKING"
lost_frame_count = 0
LOST_THRESHOLD = 30
scan_start_time = 0

# ─────────────────────────────────────────────
# INIT SERVOS
# ─────────────────────────────────────────────
set_servo(PAN_CHANNEL, pan_angle)
set_servo(TILT_CHANNEL, tilt_angle)
time.sleep(1)

# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
try:
    while True:
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        detection, mask = detect_blue_cap(frame_bgr)

        if detection:
            # ─── TARGET FOUND ───
            cx, cy, r = detection
            
            # If recovering from search mode, clean up variables
            if system_state == "SEARCHING":
                system_state = "TRACKING"
                pan_pid.reset()
                tilt_pid.reset()
                
                # Force the entire array to float32 to prevent OpenCV gemm crash
                kalman.statePre = np.array([[cx], [cy], [0], [0]], dtype=np.float32)
                kalman.statePost = np.array([[cx], [cy], [0], [0]], dtype=np.float32)
                
                print("Target Acquired! Resuming tracking.")

            lost_frame_count = 0

            # ───── KALMAN FILTER ─────
            measurement = np.array([[np.float32(cx)], [np.float32(cy)]])
            kalman.predict()
            estimated = kalman.correct(measurement)

            filtered_x = int(estimated[0])
            filtered_y = int(estimated[1])

            error_x = filtered_x - CENTER_X
            error_y = filtered_y - CENTER_Y

            # Track the state BEFORE we adjust tilt
            was_flipped = tilt_angle > 90

            # ───── TILT ─────
            if abs(error_y) > DEAD_ZONE:
                tilt_adj = tilt_pid.compute(error_y)
                tilt_angle -= tilt_adj
            else:
                tilt_pid.reset()

            # Clamp tilt early
            tilt_angle = max(TILT_MIN, min(TILT_MAX, tilt_angle))
            is_flipped = tilt_angle > 90

            # WIPE BOTH PID MEMORIES ON CROSSING
            if was_flipped != is_flipped:
                pan_pid.reset()
                tilt_pid.reset() 

            # ───── PAN ─────
            if abs(error_x) > DEAD_ZONE:
                pan_adj = pan_pid.compute(error_x)
                
                # NARROW CHOKE POINT
                if 85 < tilt_angle < 95:
                    pan_adj *= 0.25 

                # IMMEDIATE FLIP
                if not is_flipped:
                    pan_angle -= pan_adj
                else:
                    pan_angle += pan_adj
            else:
                pan_pid.reset()

            # Clamp pan
            pan_angle = max(PAN_MIN, min(PAN_MAX, pan_angle))
            tilt_angle = max(TILT_MIN, min(TILT_MAX, tilt_angle))

            # Move
            set_servo(PAN_CHANNEL, pan_angle)
            set_servo(TILT_CHANNEL, tilt_angle)

            print(f"Pan:{pan_angle:.1f} Tilt:{tilt_angle:.1f} State:{system_state}")

            # Visualize
            cv2.circle(frame_bgr, (filtered_x, filtered_y), r, (0,255,0), 2)
            cv2.circle(frame_bgr, (cx, cy), 3, (0,0,255), -1)

        else:
            # ─── TARGET LOST (SEARCH MODE) ───
            lost_frame_count += 1

            if lost_frame_count > LOST_THRESHOLD:
                if system_state == "TRACKING":
                    system_state = "SEARCHING"
                    scan_start_time = time.time()
                    print("Target Lost! Initiating Dense Web Scan.")

                # Execute Dense Lissajous Scan
                t = time.time() - scan_start_time

                # 1. WIDER AMPLITUDE: Push the scan to the physical hardware limits.
                # Pan sweeps 80° left and right (Center 90 +/- 80 = 10 to 170)
                # Tilt sweeps 50° up and down (Center 90 +/- 50 = 40 to 140)
                
                # 2. SHIFTING FREQUENCY: Using non-perfect multiples (1.2 and 0.43) 
                # forces the path to constantly shift, drawing a dense web over time 
                # rather than a repeating Figure-8.
                pan_angle = 90.0 + 80.0 * math.sin(1.2 * t)
                tilt_angle = 90.0 + 50.0 * math.sin(0.43 * t)

                # Clamp to safe bounds
                pan_angle = max(PAN_MIN, min(PAN_MAX, pan_angle))
                tilt_angle = max(TILT_MIN, min(TILT_MAX, tilt_angle))

                # Move servos
                set_servo(PAN_CHANNEL, pan_angle)
                set_servo(TILT_CHANNEL, tilt_angle)

                print(f"Searching... Pan:{pan_angle:.1f} Tilt:{tilt_angle:.1f}")

        cv2.imshow("frame", frame_bgr)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    pass

finally:
    set_servo(PAN_CHANNEL, 90)
    set_servo(TILT_CHANNEL, 90)
    pca.deinit()
    picam2.close()
    cv2.destroyAllWindows()
