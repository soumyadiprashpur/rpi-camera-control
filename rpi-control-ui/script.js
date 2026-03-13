const backend = "http://localhost:5000";

function connect() {
  fetch(`${backend}/connect`).then(() => {
    document.getElementById("statusText").innerText = "Connected";
    document.getElementById("statusIndicator").className =
      "indicator connected";
    document.getElementById("logText").innerText = "Connected to Raspberry Pi";
  });
}

function disconnect() {
  fetch(`${backend}/disconnect`).then(() => {
    document.getElementById("statusText").innerText = "Disconnected";
    document.getElementById("statusIndicator").className =
      "indicator disconnected";
    document.getElementById("logText").innerText =
      "Disconnected from Raspberry Pi";
  });
}

function openCamera() {
  fetch(`${backend}/camera`);
  document.getElementById("logText").innerText = "Camera opened";
}

function faceDetect() {
  fetch(`${backend}/face`);
  document.getElementById("logText").innerText = "Face detection started";
}

function redDetect() {
  fetch(`${backend}/red`);
  document.getElementById("logText").innerText = "Red detection started";
}

function killAll() {
  fetch(`${backend}/kill`);
  document.getElementById("logText").innerText = "All camera programs stopped";
}

function shutdownPi() {
  fetch(`${backend}/shutdown`);
  document.getElementById("logText").innerText =
    "Shutdown command sent to Raspberry Pi";
}

function killAllPrograms() {
  fetch(`${backend}/kill`);
  document.getElementById("logText").innerText = "All programs killed";
}

// Initialize status indicator
document.getElementById("statusIndicator").className = "indicator disconnected";
