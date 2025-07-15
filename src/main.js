const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const dgram = require('dgram');
const fs = require('fs');

let mainWindow;
let pythonProcess;
let udpServer;
let droneStatus = {
  connected: false,
  armed: false,
  mode: 'UNKNOWN',
  altitude: 0,
  latitude: 0,
  longitude: 0,
  battery: 0,
  distanceToTarget: 0,
  status: 'Disconnected'
};

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    icon: path.join(__dirname, 'assets/icon.png'),
    title: 'Drone Controller - Herelink UDP'
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer/index.html'));

  // Open DevTools in development
  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools();
  }
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (pythonProcess) {
    pythonProcess.kill();
  }
  if (udpServer) {
    udpServer.close();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// IPC handlers
ipcMain.handle('start-mission', async (event, { latitude, longitude, altitude, waitTime }) => {
  try {
    // Choose the appropriate script based on availability
    let scriptPath;
    
    // Try simple UDP mission first to avoid DroneKit mode errors
    const simpleScriptPath = path.join(__dirname, 'python/simple_udp_mission.py');
    const droneKitScriptPath = path.join(__dirname, 'python/drone_mission.py');
    
    // Check if we should use the simple script or full DroneKit
    const useSimpleScript = true; // Set to false when DroneKit issues are resolved
    
    if (useSimpleScript && fs.existsSync(simpleScriptPath)) {
      scriptPath = simpleScriptPath;
      console.log('Using simple UDP mission script');
    } else if (fs.existsSync(droneKitScriptPath)) {
      scriptPath = droneKitScriptPath;
      console.log('Using full DroneKit mission script');
    } else {
      throw new Error('No mission script found');
    }
    
    // Update the script with new coordinates
    let scriptContent = fs.readFileSync(scriptPath, 'utf8');
    
    // Replace the coordinates in the script
    scriptContent = scriptContent.replace(/LATITUDE = [\d.-]+/, `LATITUDE = ${latitude}`);
    scriptContent = scriptContent.replace(/LONGITUDE = [\d.-]+/, `LONGITUDE = ${longitude}`);
    scriptContent = scriptContent.replace(/ALTITUDE = [\d.-]+/, `ALTITUDE = ${altitude}`);
    scriptContent = scriptContent.replace(/WAIT_TIME_AT_TARGET = [\d.-]+/, `WAIT_TIME_AT_TARGET = ${waitTime}`);
    
    fs.writeFileSync(scriptPath, scriptContent);
    
    // Start the Python process
    pythonProcess = spawn('python', [scriptPath]);
    
    pythonProcess.stdout.on('data', (data) => {
      const output = data.toString();
      console.log('Python output:', output);
      mainWindow.webContents.send('python-output', output);
      
      // Parse output for status updates
      parseStatusFromOutput(output);
    });
    
    pythonProcess.stderr.on('data', (data) => {
      const error = data.toString();
      console.error('Python error:', error);
      mainWindow.webContents.send('python-error', error);
    });
    
    pythonProcess.on('close', (code) => {
      console.log(`Python process exited with code ${code}`);
      mainWindow.webContents.send('mission-complete', code);
    });
    
    return { success: true, message: 'Mission started successfully' };
  } catch (error) {
    console.error('Error starting mission:', error);
    return { success: false, message: error.message };
  }
});

ipcMain.handle('stop-mission', async () => {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
    return { success: true, message: 'Mission stopped' };
  }
  return { success: false, message: 'No mission running' };
});

ipcMain.handle('start-udp-server', async (event, port) => {
  try {
    if (udpServer) {
      udpServer.close();
    }
    
    udpServer = dgram.createSocket('udp4');
    
    udpServer.on('listening', () => {
      const address = udpServer.address();
      console.log(`UDP Server listening on ${address.address}:${address.port}`);
      mainWindow.webContents.send('udp-status', { connected: true, port: address.port });
    });
    
    udpServer.on('message', (msg, remote) => {
      const message = msg.toString();
      console.log(`UDP message from ${remote.address}:${remote.port} - ${message}`);
      
      // Parse Herelink telemetry data
      parseHerelinkData(message);
      
      mainWindow.webContents.send('udp-message', {
        from: `${remote.address}:${remote.port}`,
        message: message
      });
    });
    
    udpServer.on('error', (err) => {
      console.error('UDP Server error:', err);
      mainWindow.webContents.send('udp-error', err.message);
    });
    
    udpServer.bind(port);
    
    return { success: true, message: `UDP server started on port ${port}` };
  } catch (error) {
    console.error('Error starting UDP server:', error);
    return { success: false, message: error.message };
  }
});

ipcMain.handle('stop-udp-server', async () => {
  if (udpServer) {
    udpServer.close();
    udpServer = null;
    mainWindow.webContents.send('udp-status', { connected: false });
    return { success: true, message: 'UDP server stopped' };
  }
  return { success: false, message: 'No UDP server running' };
});

ipcMain.handle('get-drone-status', async () => {
  return droneStatus;
});

function parseStatusFromOutput(output) {
  // Parse different status information from Python output
  if (output.includes('Connecting to vehicle')) {
    droneStatus.status = 'Connecting...';
  } else if (output.includes('Arming motors')) {
    droneStatus.status = 'Arming...';
    droneStatus.connected = true;
  } else if (output.includes('Taking off')) {
    droneStatus.status = 'Taking off...';
    droneStatus.armed = true;
  } else if (output.includes('Altitude:')) {
    const altMatch = output.match(/Altitude: ([\d.]+)/);
    if (altMatch) {
      droneStatus.altitude = parseFloat(altMatch[1]);
    }
  } else if (output.includes('Distance to target:')) {
    const distMatch = output.match(/Distance to target: ([\d.]+)/);
    if (distMatch) {
      droneStatus.distanceToTarget = parseFloat(distMatch[1]);
      droneStatus.status = 'Flying to target...';
    }
  } else if (output.includes('Reached target location')) {
    droneStatus.status = 'At target location';
  } else if (output.includes('Return To Launch')) {
    droneStatus.status = 'Returning to launch';
    droneStatus.mode = 'RTL';
  }
  
  // Send updated status to renderer
  mainWindow.webContents.send('drone-status-update', droneStatus);
}

function parseHerelinkData(data) {
  try {
    // Parse JSON telemetry data from our mission scripts
    const telemetry = JSON.parse(data);
    
    // Handle telemetry from simple UDP mission script
    if (telemetry.latitude !== undefined) droneStatus.latitude = telemetry.latitude;
    if (telemetry.longitude !== undefined) droneStatus.longitude = telemetry.longitude;
    if (telemetry.altitude !== undefined) droneStatus.altitude = telemetry.altitude;
    if (telemetry.mode !== undefined) droneStatus.mode = telemetry.mode;
    if (telemetry.armed !== undefined) droneStatus.armed = telemetry.armed;
    if (telemetry.battery !== undefined) droneStatus.battery = telemetry.battery;
    if (telemetry.groundspeed !== undefined) droneStatus.groundspeed = telemetry.groundspeed;
    if (telemetry.heading !== undefined) droneStatus.heading = telemetry.heading;
    if (telemetry.connected !== undefined) droneStatus.connected = telemetry.connected;
    if (telemetry.status !== undefined) droneStatus.status = telemetry.status;
    
    // Handle MAVLink parser data structure
    if (telemetry.drone_status) {
      const status = telemetry.drone_status;
      
      if (status.latitude !== undefined) droneStatus.latitude = status.latitude;
      if (status.longitude !== undefined) droneStatus.longitude = status.longitude;
      if (status.altitude !== undefined) droneStatus.altitude = status.altitude;
      if (status.mode !== undefined) droneStatus.mode = status.mode;
      if (status.armed !== undefined) droneStatus.armed = status.armed;
      if (status.battery !== undefined) droneStatus.battery = status.battery;
      if (status.groundspeed !== undefined) droneStatus.groundspeed = status.groundspeed;
      if (status.heading !== undefined) droneStatus.heading = status.heading;
      if (status.connected !== undefined) droneStatus.connected = status.connected;
      if (status.system_status !== undefined) droneStatus.status = status.system_status;
    }
    
    // Send updated status to renderer
    mainWindow.webContents.send('drone-status-update', droneStatus);
    
    // Log message type for debugging
    if (telemetry.mavlink_type) {
      console.log(`MAVLink: ${telemetry.mavlink_type} from ${telemetry.source_ip}`);
    }
    
  } catch (error) {
    // Handle raw data (non-JSON)
    const dataStr = data.toString();
    
    if (dataStr.length > 100) {
      // This is likely raw MAVLink data - just log it briefly
      console.log(`Received raw data - length: ${dataStr.length} bytes`);
    } else {
      // Short message, might be readable
      console.log('Received data:', dataStr.substring(0, 50));
    }
    
    // Update connection status even for raw data
    droneStatus.connected = true;
    droneStatus.status = 'Receiving data';
    mainWindow.webContents.send('drone-status-update', droneStatus);
  }
}