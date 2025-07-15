const { ipcRenderer } = require('electron');

// DOM elements
const connectBtn = document.getElementById('connect-btn');
const disconnectBtn = document.getElementById('disconnect-btn');
const udpPortInput = document.getElementById('udp-port');
const udpStatusText = document.getElementById('udp-status-text');
const connectionIndicator = document.getElementById('connection-indicator');
const connectionText = document.getElementById('connection-text');

const latitudeInput = document.getElementById('latitude');
const longitudeInput = document.getElementById('longitude');
const altitudeInput = document.getElementById('altitude');
const waitTimeInput = document.getElementById('wait-time');
const startMissionBtn = document.getElementById('start-mission-btn');
const stopMissionBtn = document.getElementById('stop-mission-btn');

const droneStatusEl = document.getElementById('drone-status');
const droneModeEl = document.getElementById('drone-mode');
const droneArmedEl = document.getElementById('drone-armed');
const droneAltitudeEl = document.getElementById('drone-altitude');
const droneLatEl = document.getElementById('drone-lat');
const droneLonEl = document.getElementById('drone-lon');
const droneBatteryEl = document.getElementById('drone-battery');
const distanceTargetEl = document.getElementById('distance-target');

const consoleEl = document.getElementById('console');
const clearConsoleBtn = document.getElementById('clear-console');

// State variables
let isUdpConnected = false;
let isMissionRunning = false;

// Event listeners
connectBtn.addEventListener('click', startUdpServer);
disconnectBtn.addEventListener('click', stopUdpServer);
startMissionBtn.addEventListener('click', startMission);
stopMissionBtn.addEventListener('click', stopMission);
clearConsoleBtn.addEventListener('click', clearConsole);

// IPC event listeners
ipcRenderer.on('udp-status', (event, status) => {
    updateUdpStatus(status);
});

ipcRenderer.on('udp-message', (event, data) => {
    addToConsole(`[UDP] ${data.from}: ${data.message}`, 'info');
});

ipcRenderer.on('udp-error', (event, error) => {
    addToConsole(`[UDP ERROR] ${error}`, 'error');
});

ipcRenderer.on('python-output', (event, output) => {
    addToConsole(`[DRONE] ${output}`, 'success');
});

ipcRenderer.on('python-error', (event, error) => {
    addToConsole(`[DRONE ERROR] ${error}`, 'error');
});

ipcRenderer.on('mission-complete', (event, code) => {
    addToConsole(`[MISSION] Mission completed with code: ${code}`, 'info');
    isMissionRunning = false;
    updateMissionButtons();
});

ipcRenderer.on('drone-status-update', (event, status) => {
    updateDroneStatus(status);
});

// Functions
async function startUdpServer() {
    const port = parseInt(udpPortInput.value) || 14550;
    
    try {
        const result = await ipcRenderer.invoke('start-udp-server', port);
        if (result.success) {
            addToConsole(`[UDP] ${result.message}`, 'success');
        } else {
            addToConsole(`[UDP ERROR] ${result.message}`, 'error');
        }
    } catch (error) {
        addToConsole(`[UDP ERROR] ${error.message}`, 'error');
    }
}

async function stopUdpServer() {
    try {
        const result = await ipcRenderer.invoke('stop-udp-server');
        if (result.success) {
            addToConsole(`[UDP] ${result.message}`, 'info');
        } else {
            addToConsole(`[UDP ERROR] ${result.message}`, 'error');
        }
    } catch (error) {
        addToConsole(`[UDP ERROR] ${error.message}`, 'error');
    }
}

async function startMission() {
    const missionParams = {
        latitude: parseFloat(latitudeInput.value),
        longitude: parseFloat(longitudeInput.value),
        altitude: parseFloat(altitudeInput.value),
        waitTime: parseInt(waitTimeInput.value)
    };
    
    // Validate inputs
    if (isNaN(missionParams.latitude) || isNaN(missionParams.longitude) || 
        isNaN(missionParams.altitude) || isNaN(missionParams.waitTime)) {
        addToConsole('[ERROR] Please enter valid numeric values for all mission parameters', 'error');
        return;
    }
    
    if (missionParams.altitude < 5 || missionParams.altitude > 400) {
        addToConsole('[ERROR] Altitude must be between 5 and 400 meters', 'error');
        return;
    }
    
    try {
        const result = await ipcRenderer.invoke('start-mission', missionParams);
        if (result.success) {
            addToConsole(`[MISSION] ${result.message}`, 'success');
            addToConsole(`[MISSION] Target: ${missionParams.latitude}, ${missionParams.longitude} at ${missionParams.altitude}m`, 'info');
            isMissionRunning = true;
            updateMissionButtons();
        } else {
            addToConsole(`[MISSION ERROR] ${result.message}`, 'error');
        }
    } catch (error) {
        addToConsole(`[MISSION ERROR] ${error.message}`, 'error');
    }
}

async function stopMission() {
    try {
        const result = await ipcRenderer.invoke('stop-mission');
        if (result.success) {
            addToConsole(`[MISSION] ${result.message}`, 'warning');
            isMissionRunning = false;
            updateMissionButtons();
        } else {
            addToConsole(`[MISSION ERROR] ${result.message}`, 'error');
        }
    } catch (error) {
        addToConsole(`[MISSION ERROR] ${error.message}`, 'error');
    }
}

function updateUdpStatus(status) {
    isUdpConnected = status.connected;
    
    if (isUdpConnected) {
        udpStatusText.textContent = `UDP Server: Running on port ${status.port}`;
        connectionIndicator.classList.add('connected');
        connectionText.textContent = 'Connected';
        connectBtn.disabled = false;
        disconnectBtn.disabled = true;
    }
    
    updateMissionButtons();
}

function updateMissionButtons() {
    // Enable mission controls only if UDP is connected
    startMissionBtn.disabled = !isUdpConnected || isMissionRunning;
    stopMissionBtn.disabled = !isMissionRunning;
}

function updateDroneStatus(status) {
    droneStatusEl.textContent = status.status;
    droneModeEl.textContent = status.mode;
    droneArmedEl.textContent = status.armed ? 'Yes' : 'No';
    droneAltitudeEl.textContent = `${status.altitude.toFixed(1)} m`;
    droneLatEl.textContent = status.latitude.toFixed(6);
    droneLonEl.textContent = status.longitude.toFixed(6);
    droneBatteryEl.textContent = `${status.battery}%`;
    distanceTargetEl.textContent = `${status.distanceToTarget.toFixed(1)} m`;
    
    // Update connection indicator based on drone connection
    if (status.connected) {
        connectionIndicator.classList.add('connected');
        connectionText.textContent = 'Drone Connected';
    } else if (isUdpConnected) {
        connectionIndicator.classList.remove('connected');
        connectionText.textContent = 'UDP Connected';
    }
}

function addToConsole(message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const logLine = `[${timestamp}] ${message}\n`;
    
    const span = document.createElement('span');
    span.textContent = logLine;
    
    switch (type) {
        case 'error':
            span.className = 'error-message';
            break;
        case 'success':
            span.className = 'success-message';
            break;
        case 'warning':
            span.className = 'warning-message';
            break;
        default:
            break;
    }
    
    consoleEl.appendChild(span);
    consoleEl.scrollTop = consoleEl.scrollHeight;
}

function clearConsole() {
    consoleEl.innerHTML = '';
    addToConsole('Console cleared', 'info');
}

// Input validation functions
function validateCoordinates() {
    const lat = parseFloat(latitudeInput.value);
    const lon = parseFloat(longitudeInput.value);
    const alt = parseFloat(altitudeInput.value);
    const wait = parseInt(waitTimeInput.value);
    
    let isValid = true;
    let errors = [];
    
    // Validate latitude
    if (isNaN(lat) || lat < -90 || lat > 90) {
        errors.push('Latitude must be between -90 and 90 degrees');
        latitudeInput.style.borderColor = '#e74c3c';
        isValid = false;
    } else {
        latitudeInput.style.borderColor = '#34495e';
    }
    
    // Validate longitude
    if (isNaN(lon) || lon < -180 || lon > 180) {
        errors.push('Longitude must be between -180 and 180 degrees');
        longitudeInput.style.borderColor = '#e74c3c';
        isValid = false;
    } else {
        longitudeInput.style.borderColor = '#34495e';
    }
    
    // Validate altitude
    if (isNaN(alt) || alt < 5 || alt > 400) {
        errors.push('Altitude must be between 5 and 400 meters');
        altitudeInput.style.borderColor = '#e74c3c';
        isValid = false;
    } else {
        altitudeInput.style.borderColor = '#34495e';
    }
    
    // Validate wait time
    if (isNaN(wait) || wait < 5 || wait > 300) {
        errors.push('Wait time must be between 5 and 300 seconds');
        waitTimeInput.style.borderColor = '#e74c3c';
        isValid = false;
    } else {
        waitTimeInput.style.borderColor = '#34495e';
    }
    
    return { isValid, errors };
}

// Real-time validation
function setupValidation() {
    [latitudeInput, longitudeInput, altitudeInput, waitTimeInput].forEach(input => {
        input.addEventListener('input', () => {
            const validation = validateCoordinates();
            if (validation.isValid) {
                startMissionBtn.disabled = !isUdpConnected || isMissionRunning;
            } else {
                startMissionBtn.disabled = true;
            }
        });
    });
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    addToConsole('Drone Controller Application Started', 'success');
    addToConsole('Configure UDP connection and mission parameters to begin', 'info');
    
    // Load saved settings from localStorage
    const savedPort = localStorage.getItem('udp-port');
    if (savedPort) {
        udpPortInput.value = savedPort;
    }
    
    const savedLat = localStorage.getItem('latitude');
    if (savedLat) {
        latitudeInput.value = savedLat;
    }
    
    const savedLon = localStorage.getItem('longitude');
    if (savedLon) {
        longitudeInput.value = savedLon;
    }
    
    const savedAlt = localStorage.getItem('altitude');
    if (savedAlt) {
        altitudeInput.value = savedAlt;
    }
    
    const savedWait = localStorage.getItem('wait-time');
    if (savedWait) {
        waitTimeInput.value = savedWait;
    }
    
    // Setup input validation
    setupValidation();
    
    // Initial validation
    validateCoordinates();
});

// Save settings to localStorage when they change
udpPortInput.addEventListener('change', () => {
    localStorage.setItem('udp-port', udpPortInput.value);
});

latitudeInput.addEventListener('change', () => {
    localStorage.setItem('latitude', latitudeInput.value);
});

longitudeInput.addEventListener('change', () => {
    localStorage.setItem('longitude', longitudeInput.value);
});

altitudeInput.addEventListener('change', () => {
    localStorage.setItem('altitude', altitudeInput.value);
});

waitTimeInput.addEventListener('change', () => {
    localStorage.setItem('wait-time', waitTimeInput.value);
});

// Keyboard shortcuts
document.addEventListener('keydown', (event) => {
    // Ctrl+Enter or Cmd+Enter to start mission
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        if (!startMissionBtn.disabled) {
            startMission();
        }
    }
    
    // Escape to stop mission
    if (event.key === 'Escape') {
        if (!stopMissionBtn.disabled) {
            stopMission();
        }
    }
    
    // Ctrl+L or Cmd+L to clear console
    if ((event.ctrlKey || event.metaKey) && event.key === 'l') {
        event.preventDefault();
        clearConsole();
    }
});

// Auto-refresh drone status every second
setInterval(async () => {
    try {
        const status = await ipcRenderer.invoke('get-drone-status');
        updateDroneStatus(status);
    } catch (error) {
        console.error('Error getting drone status:', error);
    }
}, 1000);

// Connection health check
setInterval(() => {
    if (isUdpConnected && !isMissionRunning) {
        // Send a heartbeat or status check
        addToConsole('Connection active - awaiting mission commands', 'info');
    }
}, 30000); // Every 30 seconds

// Emergency stop functionality
function emergencyStop() {
    if (isMissionRunning) {
        stopMission();
        addToConsole('EMERGENCY STOP ACTIVATED', 'error');
    }
}

// Export functions for potential external use
window.droneController = {
    startMission,
    stopMission,
    emergencyStop,
    clearConsole,
    validateCoordinates
};

// Fix the UDP status update function (the code was cut off)
function updateUdpStatus(status) {
    isUdpConnected = status.connected;
    
    if (isUdpConnected) {
        udpStatusText.textContent = `UDP Server: Running on port ${status.port}`;
        connectionIndicator.classList.add('connected');
        connectionText.textContent = 'Connected';
        connectBtn.disabled = true;
        disconnectBtn.disabled = false;
    } else {
        udpStatusText.textContent = 'UDP Server: Stopped';
        connectionIndicator.classList.remove('connected');
        connectionText.textContent = 'Disconnected';
        connectBtn.disabled = false;
        disconnectBtn.disabled = true;
    }
    
    updateMissionButtons();
}