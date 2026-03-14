const backend = "http://localhost:5000";

let isConnected = false;
let commandCount = 0;
let currentStreamMode = null;
let uptimeInterval = null;
let uptimeSeconds = 0;
let fpsInterval = null;
let monitoringInterval = null;
let monitoringRate = 5000;
let pendingModalAction = null;

// ========== PAGE NAVIGATION ==========
function switchPage(page, navEl) {
  // Hide all pages
  document.querySelectorAll(".page-content").forEach((p) => {
    p.classList.remove("active");
  });

  // Show selected page
  document.getElementById(`page-${page}`).classList.add("active");

  // Update nav
  document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
  navEl.classList.add("active");

  // Update topbar
  const titles = {
    dashboard: "Dashboard",
    camera: "Camera",
    network: "Network",
    monitoring: "Monitoring",
    settings: "Settings",
  };
  document.getElementById("pageTitle").textContent = titles[page];
  document.getElementById("pageBreadcrumb").textContent = `Home / ${titles[page]}`;

  // Close mobile sidebar
  document.querySelector(".sidebar").classList.remove("open");

  // Refresh data when switching to certain pages
  if (page === "monitoring" && isConnected) refreshMonitoring();
  if (page === "network" && isConnected) refreshNetworkInfo();
}

// ========== DATETIME ==========
function updateDateTime() {
  const now = new Date();
  const options = { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" };
  document.getElementById("datetime").textContent = now.toLocaleDateString("en-US", options);
}
setInterval(updateDateTime, 1000);
updateDateTime();

// ========== UPTIME ==========
function startUptime() {
  uptimeSeconds = 0;
  uptimeInterval = setInterval(() => {
    uptimeSeconds++;
    const h = String(Math.floor(uptimeSeconds / 3600)).padStart(2, "0");
    const m = String(Math.floor((uptimeSeconds % 3600) / 60)).padStart(2, "0");
    const s = String(uptimeSeconds % 60).padStart(2, "0");
    document.getElementById("statUptime").textContent = `${h}:${m}:${s}`;
  }, 1000);
}

function stopUptime() {
  clearInterval(uptimeInterval);
  uptimeInterval = null;
  uptimeSeconds = 0;
  document.getElementById("statUptime").textContent = "--:--:--";
}

// ========== TOAST ==========
function showToast(message, type = "info") {
  if (!document.getElementById("settingToasts")?.checked) return;
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  const icons = { success: "fa-check-circle", error: "fa-times-circle", info: "fa-info-circle", warning: "fa-exclamation-circle" };
  toast.innerHTML = `<i class="fas ${icons[type]}"></i><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// ========== LOG ==========
function addLog(message, type = "info") {
  const logEntries = document.getElementById("logEntries");
  const entry = document.createElement("div");
  entry.className = "log-entry";
  const now = new Date();
  const time = now.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
  entry.innerHTML = `<div class="log-time">${time}</div><div class="log-dot ${type}"></div><div class="log-message">${message}</div>`;
  logEntries.insertBefore(entry, logEntries.firstChild);
  while (logEntries.children.length > 50) logEntries.removeChild(logEntries.lastChild);
}

function clearLog() {
  document.getElementById("logEntries").innerHTML = "";
  addLog("Log cleared", "info");
  showToast("Activity log cleared", "info");
}

// ========== STREAM ==========
function startStream(streamUrl, mode) {
  // Dashboard stream
  const img = document.getElementById("streamImage");
  const placeholder = document.getElementById("streamPlaceholder");
  const overlay = document.getElementById("streamOverlay");
  const streamBadge = document.getElementById("streamBadge");
  const modeLabel = document.getElementById("streamModeLabel");

  // Camera page stream
  const camImg = document.getElementById("camStreamImage");
  const camPlaceholder = document.getElementById("camStreamPlaceholder");
  const camOverlay = document.getElementById("camStreamOverlay");
  const camBadge = document.getElementById("camPageStreamBadge");
  const camModeLabel = document.getElementById("camStreamModeLabel");

  const feedUrl = `${backend}/video_feed?t=${Date.now()}`;

  const modeNames = { camera: "Camera", face: "Face Detection", red: "Red Detection" };
  const modeName = modeNames[mode] || mode;

  // Dashboard
  img.src = feedUrl;
  img.style.display = "block";
  placeholder.style.display = "none";
  overlay.style.display = "flex";
  modeLabel.textContent = modeName;
  streamBadge.textContent = "LIVE";
  streamBadge.className = "panel-badge streaming";

  // Camera page
  camImg.src = feedUrl;
  camImg.style.display = "block";
  camPlaceholder.style.display = "none";
  camOverlay.style.display = "flex";
  camModeLabel.textContent = modeName;
  camBadge.textContent = "LIVE";
  camBadge.className = "panel-badge streaming";

  currentStreamMode = mode;
  document.getElementById("statMode").textContent = modeName;
  document.getElementById("camActiveMode").textContent = modeName;

  // Mode cards
  document.querySelectorAll(".mode-card").forEach((c) => c.classList.remove("active"));
  const modeMap = { camera: "modeCamera", face: "modeFace", red: "modeRed" };
  if (modeMap[mode]) document.getElementById(modeMap[mode]).classList.add("active");

  // Error handling with retry
  const handleError = (imgEl) => {
    imgEl.onerror = () => {
      setTimeout(() => {
        if (currentStreamMode) imgEl.src = `${backend}/video_feed?t=${Date.now()}`;
      }, 2000);
    };
  };
  handleError(img);
  handleError(camImg);
}

function stopStream() {
  // Dashboard
  const img = document.getElementById("streamImage");
  document.getElementById("streamPlaceholder").style.display = "flex";
  document.getElementById("streamOverlay").style.display = "none";
  document.getElementById("streamBadge").textContent = "No Feed";
  document.getElementById("streamBadge").className = "panel-badge";
  img.src = "";
  img.style.display = "none";

  // Camera page
  const camImg = document.getElementById("camStreamImage");
  document.getElementById("camStreamPlaceholder").style.display = "flex";
  document.getElementById("camStreamOverlay").style.display = "none";
  document.getElementById("camPageStreamBadge").textContent = "No Feed";
  document.getElementById("camPageStreamBadge").className = "panel-badge";
  camImg.src = "";
  camImg.style.display = "none";

  currentStreamMode = null;
  document.getElementById("statMode").textContent = "None";
  document.getElementById("camActiveMode").textContent = "None";
  document.querySelectorAll(".mode-card").forEach((c) => c.classList.remove("active"));
}

function toggleFullscreen() {
  const container = document.getElementById("streamContainer");
  const camContainer = document.getElementById("streamContainerCam");
  // Toggle whichever page is active
  const activePage = document.querySelector(".page-content.active").id;
  if (activePage === "page-camera") {
    camContainer.classList.toggle("fullscreen");
  } else {
    container.classList.toggle("fullscreen");
  }
}

function takeScreenshot() {
  if (!currentStreamMode) {
    showToast("No active stream to capture", "warning");
    return;
  }

  const gallery = document.getElementById("screenshotsGallery");
  const noScreenshots = gallery.querySelector(".no-screenshots");
  if (noScreenshots) noScreenshots.remove();

  const canvas = document.createElement("canvas");
  const img = document.getElementById("camStreamImage");
  canvas.width = img.naturalWidth || 640;
  canvas.height = img.naturalHeight || 480;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(img, 0, 0);

  const dataUrl = canvas.toDataURL("image/png");
  const now = new Date();
  const time = now.toLocaleTimeString("en-US", { hour12: false });

  const item = document.createElement("div");
  item.className = "screenshot-item";
  item.innerHTML = `<img src="${dataUrl}" alt="Screenshot" /><div class="screenshot-time">${time}</div>`;
  gallery.insertBefore(item, gallery.firstChild);

  addLog("Screenshot captured", "success");
  showToast("Screenshot saved!", "success");
}

function clearScreenshots() {
  document.getElementById("screenshotsGallery").innerHTML = `
    <div class="no-screenshots">
      <i class="fas fa-image"></i>
      <p>No screenshots yet. Click the camera icon above to capture.</p>
    </div>`;
  showToast("Screenshots cleared", "info");
}

// ========== CONNECTION UI ==========
function updateConnectionUI(connected) {
  isConnected = connected;
  const badge = document.getElementById("connectionBadge");
  const dot = document.getElementById("badgeDot");

  if (connected) {
    badge.classList.add("connected");
    dot.classList.add("connected");
    document.getElementById("statusText").textContent = "Connected";
    document.getElementById("statStatus").textContent = "Online";
    document.getElementById("connPanelBadge").textContent = "Online";
    document.getElementById("connPanelBadge").className = "panel-badge online";
    document.getElementById("connPulse").classList.add("active");
    document.querySelector(".conn-node.local").classList.add("active");
    document.getElementById("remoteNode").classList.add("active");
    startUptime();
    startAutoRefresh();
  } else {
    badge.classList.remove("connected");
    dot.classList.remove("connected");
    document.getElementById("statusText").textContent = "Disconnected";
    document.getElementById("statStatus").textContent = "Offline";
    document.getElementById("connPanelBadge").textContent = "Offline";
    document.getElementById("connPanelBadge").className = "panel-badge";
    document.getElementById("connPulse").classList.remove("active");
    document.querySelector(".conn-node.local").classList.remove("active");
    document.getElementById("remoteNode").classList.remove("active");
    stopUptime();
    stopStream();
    stopAutoRefresh();
  }
}

function incrementCommands() {
  commandCount++;
  document.getElementById("statCommands").textContent = commandCount;
}

// ========== ACTIONS ==========
function connect() {
  addLog("Connecting to Raspberry Pi...", "info");
  showToast("Connecting...", "info");

  fetch(`${backend}/connect`)
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        updateConnectionUI(true);
        incrementCommands();
        addLog("Connected to Raspberry Pi", "success");
        showToast("Connected!", "success");
        refreshMonitoring();
        refreshNetworkInfo();
      } else throw new Error(data.message);
    })
    .catch((err) => {
      addLog(`Connection failed: ${err.message}`, "error");
      showToast("Connection failed", "error");
    });
}

function disconnect() {
  fetch(`${backend}/disconnect`)
    .then((r) => r.json())
    .then(() => {
      updateConnectionUI(false);
      incrementCommands();
      addLog("Disconnected", "warning");
      showToast("Disconnected", "warning");
    })
    .catch((err) => {
      addLog(`Error: ${err.message}`, "error");
      showToast("Disconnect failed", "error");
    });
}

function openCamera() {
  if (!isConnected) { showToast("Connect to Pi first", "warning"); return; }
  addLog("Starting camera...", "info");
  fetch(`${backend}/camera`)
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        startStream(data.stream_url, "camera");
        incrementCommands();
        addLog("Camera stream started", "success");
        showToast("Camera is live!", "success");
      } else throw new Error(data.message);
    })
    .catch((err) => {
      addLog(`Camera error: ${err.message}`, "error");
      showToast("Camera failed", "error");
    });
}

function faceDetect() {
  if (!isConnected) { showToast("Connect to Pi first", "warning"); return; }
  addLog("Starting face detection...", "info");
  fetch(`${backend}/face`)
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        startStream(data.stream_url, "face");
        incrementCommands();
        addLog("Face detection started", "success");
        showToast("Face detection live!", "success");
      } else throw new Error(data.message);
    })
    .catch((err) => {
      addLog(`Error: ${err.message}`, "error");
      showToast("Face detection failed", "error");
    });
}

function redDetect() {
  if (!isConnected) { showToast("Connect to Pi first", "warning"); return; }
  addLog("Starting red detection...", "info");
  fetch(`${backend}/red`)
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        startStream(data.stream_url, "red");
        incrementCommands();
        addLog("Red detection started", "success");
        showToast("Red detection live!", "success");
      } else throw new Error(data.message);
    })
    .catch((err) => {
      addLog(`Error: ${err.message}`, "error");
      showToast("Red detection failed", "error");
    });
}

function killAll() {
  fetch(`${backend}/kill`)
    .then((r) => r.json())
    .then(() => {
      stopStream();
      incrementCommands();
      addLog("All programs stopped", "error");
      showToast("All stopped", "warning");
    })
    .catch((err) => {
      addLog(`Error: ${err.message}`, "error");
      showToast("Kill failed", "error");
    });
}

// ========== MODAL ==========
function shutdownPi() {
  pendingModalAction = "shutdown";
  document.getElementById("modalTitle").textContent = "Confirm Shutdown";
  document.getElementById("modalMessage").textContent = "Are you sure you want to shutdown the Raspberry Pi? This requires physical access to restart.";
  document.getElementById("modalConfirmBtn").textContent = "Shutdown";
  document.getElementById("modalOverlay").classList.add("active");
}

function rebootPi() {
  pendingModalAction = "reboot";
  document.getElementById("modalTitle").textContent = "Confirm Reboot";
  document.getElementById("modalMessage").textContent = "Are you sure you want to reboot the Raspberry Pi? You'll need to reconnect after.";
  document.getElementById("modalConfirmBtn").textContent = "Reboot";
  document.getElementById("modalOverlay").classList.add("active");
}

function closeModal() {
  document.getElementById("modalOverlay").classList.remove("active");
  pendingModalAction = null;
}

function confirmShutdown() {
  closeModal();
  if (pendingModalAction === "reboot") {
    fetch(`${backend}/reboot`)
      .then((r) => r.json())
      .then(() => {
        incrementCommands();
        updateConnectionUI(false);
        addLog("Reboot command sent", "warning");
        showToast("Pi is rebooting...", "warning");
      })
      .catch((err) => { addLog(`Error: ${err.message}`, "error"); showToast("Reboot failed", "error"); });
  } else {
    fetch(`${backend}/shutdown`)
      .then((r) => r.json())
      .then(() => {
        incrementCommands();
        updateConnectionUI(false);
        addLog("Shutdown command sent", "error");
        showToast("Pi is shutting down...", "warning");
      })
      .catch((err) => { addLog(`Error: ${err.message}`, "error"); showToast("Shutdown failed", "error"); });
  }
}

// ========== NETWORK PAGE ==========
function refreshNetworkInfo() {
  if (!isConnected) { showToast("Connect to Pi first", "warning"); return; }

  fetch(`${backend}/system/network`)
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        const net = data.data;
        document.getElementById("netIP").textContent = net.ip || "--";
        document.getElementById("netSubnet").textContent = net.subnet || "--";
        document.getElementById("netGateway").textContent = net.gateway || "--";
        document.getElementById("netMAC").textContent = net.mac || "--";
        document.getElementById("netDNS").textContent = net.dns || "--";
        document.getElementById("netHostname").textContent = net.hostname || "--";
        document.getElementById("netConnType").textContent = net.conn_type || "--";
        document.getElementById("netSignal").textContent = net.signal || "--";
        document.getElementById("netLatency").textContent = net.latency || "-- ms";

        // Build interfaces table
        const table = document.getElementById("interfacesTable");
        const header = table.querySelector(".table-header");
        table.innerHTML = "";
        table.appendChild(header);

        if (net.interfaces && net.interfaces.length > 0) {
          net.interfaces.forEach((iface) => {
            const row = document.createElement("div");
            row.className = "table-row";
            row.innerHTML = `
              <span>${iface.name}</span>
              <span>${iface.ip || "N/A"}</span>
              <span><span class="status-badge ${iface.status === 'UP' ? 'up' : 'down'}">${iface.status}</span></span>
              <span>${iface.type}</span>`;
            table.appendChild(row);
          });
        }

        addLog("Network info refreshed", "info");
      }
    })
    .catch((err) => {
      addLog(`Network info error: ${err.message}`, "error");
    });
}

function runPingTest() {
  if (!isConnected) { showToast("Connect to Pi first", "warning"); return; }
  showToast("Running ping test...", "info");

  fetch(`${backend}/system/ping`)
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        const ping = data.data;
        document.getElementById("pingValue").textContent = ping.avg || "--";
        document.getElementById("pingMin").textContent = ping.min ? `${ping.min} ms` : "--";
        document.getElementById("pingAvg").textContent = ping.avg ? `${ping.avg} ms` : "--";
        document.getElementById("pingMax").textContent = ping.max ? `${ping.max} ms` : "--";
        document.getElementById("pingLoss").textContent = ping.loss || "--";
        document.getElementById("netLatency").textContent = ping.avg ? `${ping.avg} ms` : "-- ms";

        const circle = document.getElementById("pingCircle");
        circle.classList.remove("good", "medium", "bad");
        const avg = parseFloat(ping.avg);
        if (avg < 50) circle.classList.add("good");
        else if (avg < 150) circle.classList.add("medium");
        else circle.classList.add("bad");

        addLog(`Ping test: avg=${ping.avg}ms, loss=${ping.loss}`, "success");
        showToast("Ping test completed", "success");
      }
    })
    .catch((err) => {
      addLog(`Ping error: ${err.message}`, "error");
      showToast("Ping test failed", "error");
    });
}

// ========== MONITORING PAGE ==========
function refreshMonitoring() {
  if (!isConnected) return;

  fetch(`${backend}/system/stats`)
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        const stats = data.data;

        // Update stat cards
        document.getElementById("monCPU").textContent = `${stats.cpu}%`;
        document.getElementById("monRAM").textContent = `${stats.ram}%`;
        document.getElementById("monTemp").textContent = `${stats.temp}°C`;
        document.getElementById("monDisk").textContent = `${stats.disk}%`;

        // Update gauges
        updateGauge("cpuGauge", "cpuGaugeVal", stats.cpu);
        updateGauge("ramGauge", "ramGaugeVal", stats.ram);
        updateGauge("tempGauge", "tempGaugeVal", stats.temp, 85); // max 85°C
        updateGauge("diskGauge", "diskGaugeVal", stats.disk);

        // System info
        document.getElementById("sysModel").textContent = stats.model || "--";
        document.getElementById("sysOS").textContent = stats.os || "--";
        document.getElementById("sysKernel").textContent = stats.kernel || "--";
        document.getElementById("sysPython").textContent = stats.python || "--";
        document.getElementById("sysUptime").textContent = stats.sys_uptime || "--";
        document.getElementById("sysTotalRAM").textContent = stats.total_ram || "--";
        document.getElementById("sysTotalDisk").textContent = stats.total_disk || "--";
        document.getElementById("piModelSidebar").textContent = stats.model || "Raspberry Pi";

        // Processes table
        const table = document.getElementById("processesTable");
        const header = table.querySelector(".table-header");
        table.innerHTML = "";
        table.appendChild(header);

        if (stats.processes && stats.processes.length > 0) {
          stats.processes.forEach((proc) => {
            const row = document.createElement("div");
            row.className = "table-row";
            row.innerHTML = `
              <span>${proc.pid}</span>
              <span>${proc.name}</span>
              <span>${proc.cpu}%</span>
              <span>${proc.mem}%</span>`;
            table.appendChild(row);
          });
        }
      }
    })
    .catch(() => {});
}

function updateGauge(gaugeId, valId, value, max = 100) {
  const circumference = 326.73;
  const pct = Math.min(value / max, 1);
  const offset = circumference * (1 - pct);
  document.getElementById(gaugeId).style.strokeDashoffset = offset;
  document.getElementById(valId).textContent = value;
}

function startAutoRefresh() {
  stopAutoRefresh();
  if (document.getElementById("settingAutoRefresh")?.checked) {
    monitoringInterval = setInterval(refreshMonitoring, monitoringRate);
  }
}

function stopAutoRefresh() {
  clearInterval(monitoringInterval);
  monitoringInterval = null;
}

function toggleAutoRefresh() {
  if (document.getElementById("settingAutoRefresh").checked) {
    if (isConnected) startAutoRefresh();
  } else {
    stopAutoRefresh();
  }
}

function updateRefreshRate() {
  monitoringRate = parseInt(document.getElementById("settingRefreshRate").value);
  if (isConnected && document.getElementById("settingAutoRefresh")?.checked) {
    startAutoRefresh();
  }
}

// ========== SETTINGS ==========
function togglePassword() {
  const input = document.getElementById("settingPass");
  const icon = document.getElementById("passEyeIcon");
  if (input.type === "password") {
    input.type = "text";
    icon.className = "fas fa-eye-slash";
  } else {
    input.type = "password";
    icon.className = "fas fa-eye";
  }
}

function saveConnectionSettings() {
  const ip = document.getElementById("settingIP").value;
  const user = document.getElementById("settingUser").value;
  const pass = document.getElementById("settingPass").value;
  const port = document.getElementById("settingPort").value;

  fetch(`${backend}/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ip, username: user, password: pass, stream_port: parseInt(port) }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        addLog("Connection settings saved", "success");
        showToast("Settings saved!", "success");
      } else throw new Error(data.message);
    })
    .catch((err) => {
      addLog(`Settings error: ${err.message}`, "error");
      showToast("Failed to save settings", "error");
    });
}

// ========== TERMINAL ==========
function executeTerminalCmd() {
  const input = document.getElementById("terminalInput");
  const cmd = input.value.trim();
  if (!cmd) return;
  if (!isConnected) { showToast("Connect to Pi first", "warning"); return; }

  const output = document.getElementById("terminalOutput");
  output.innerHTML += `<div class="terminal-line command">$ ${cmd}</div>`;
  input.value = "";

  fetch(`${backend}/terminal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ command: cmd }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.stdout) {
        data.stdout.split("\n").forEach((line) => {
          if (line.trim()) output.innerHTML += `<div class="terminal-line output">${escapeHtml(line)}</div>`;
        });
      }
      if (data.stderr) {
        data.stderr.split("\n").forEach((line) => {
          if (line.trim()) output.innerHTML += `<div class="terminal-line error">${escapeHtml(line)}</div>`;
        });
      }
      if (!data.stdout && !data.stderr) {
        output.innerHTML += `<div class="terminal-line output">(no output)</div>`;
      }
      output.scrollTop = output.scrollHeight;
      incrementCommands();
      addLog(`Terminal: ${cmd}`, "info");
    })
    .catch((err) => {
      output.innerHTML += `<div class="terminal-line error">Error: ${err.message}</div>`;
      output.scrollTop = output.scrollHeight;
    });
}

function clearTerminal() {
  document.getElementById("terminalOutput").innerHTML = `<div class="terminal-line system">Terminal cleared</div>`;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// ========== SIDEBAR & MODAL ==========
document.getElementById("menuToggle").addEventListener("click", () => {
  document.querySelector(".sidebar").classList.toggle("open");
});

document.addEventListener("click", (e) => {
  const sidebar = document.querySelector(".sidebar");
  const toggle = document.getElementById("menuToggle");
  if (sidebar.classList.contains("open") && !sidebar.contains(e.target) && !toggle.contains(e.target)) {
    sidebar.classList.remove("open");
  }
});

document.getElementById("modalOverlay").addEventListener("click", (e) => {
  if (e.target === document.getElementById("modalOverlay")) closeModal();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    closeModal();
    document.getElementById("streamContainer").classList.remove("fullscreen");
    document.getElementById("streamContainerCam").classList.remove("fullscreen");
  }
});

// ========== INIT ==========
updateConnectionUI(false);
addLog("System initialized. Waiting for connection...", "info");