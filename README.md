# Raspberry Pi Camera Control Interface

## Project Overview

This project provides a web-based control interface for a Raspberry Pi camera system. The system allows users to remotely control camera operations on a Raspberry Pi through a simple web interface running on a laptop.

### Architecture

- **Frontend**: Runs on a laptop using HTML, CSS, and JavaScript
- **Backend**: Runs on the same laptop using Python Flask
- **Connection**: Backend connects to Raspberry Pi via SSH using Paramiko
- **Raspberry Pi**: Runs Python scripts that control a USB camera

## Features

- Connect to Raspberry Pi via SSH
- Disconnect from Raspberry Pi
- Open camera feed
- Face detection mode
- Red object detection mode
- Kill all running camera programs
- Shutdown Raspberry Pi remotely

## Requirements

### Software Dependencies

- Python 3
- Flask
- Paramiko
- Flask-CORS
- OpenCV (must be installed on Raspberry Pi)

### Hardware

- A Raspberry Pi with SSH enabled
- USB camera connected to Raspberry Pi

## Installation

Install the required Python packages using pip:

```bash
pip install flask paramiko flask-cors
```

## Running the Backend

1. Navigate to the backend directory:

```bash
cd backend
```

2. Start the Flask server:

```bash
python server.py
```

The backend will run on `http://localhost:5000`.

## Running the Frontend

1. Start a simple HTTP server in the project root directory:

```bash
python -m http.server 8080
```

2. Open your web browser and navigate to:

```
http://localhost:8080
```

## Usage

1. **Connect to Raspberry Pi**: Click the "Connect" button to establish SSH connection to your Raspberry Pi
2. **Camera Controls**: Use the camera buttons to start different detection modes:
   - Open Camera: Starts basic camera feed
   - Face Detection: Enables face detection mode
   - Red Detection: Enables red object detection mode
3. **Stop Programs**: Use the "Kill All" button to stop all running camera programs
4. **Shutdown Raspberry Pi**: Click the "Shutdown Raspberry Pi" button to safely shut down the Raspberry Pi remotely (sends `sudo shutdown now` command via SSH)

## Notes

- Raspberry Pi scripts (`cam_open.py`, `face_detect.py`, `red_detect.py`) must be present on the Raspberry Pi
- OpenCV must be installed on the Raspberry Pi for camera functionality
- Ensure SSH is enabled on your Raspberry Pi and you have the correct IP address and credentials

## Troubleshooting

- **SSH Connection Issues**: Verify that SSH is enabled on your Raspberry Pi and check the IP address
- **Camera Not Working**: Ensure OpenCV is installed on the Raspberry Pi and the USB camera is properly connected
- **Port Conflicts**: Make sure ports 5000 (backend) and 8080 (frontend) are not in use by other applications
- **Permission Errors**: Ensure you have proper SSH credentials and file permissions on the Raspberry Pi
