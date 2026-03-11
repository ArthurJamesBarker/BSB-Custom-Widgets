/**
 * UXP Panel JavaScript
 * Handles UI interactions and communicates with main.js
 */

const plugin = require('./main.js');

// UI elements
const statusDiv = document.getElementById('status');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');

/**
 * Update status display
 */
function updateStatus(connected, message) {
    statusDiv.className = connected ? 'status connected' : 'status disconnected';
    statusDiv.textContent = message || (connected ? 'WebSocket Server: Running on port 8080' : 'WebSocket Server: Stopped');
}

/**
 * Start server
 */
startBtn.addEventListener('click', () => {
    const success = plugin.startServer();
    if (success) {
        updateStatus(true, 'WebSocket Server: Running on port 8080');
        startBtn.disabled = true;
        stopBtn.disabled = false;
    } else {
        updateStatus(false, 'WebSocket Server: Failed to start');
        alert('Failed to start server. Check console for errors.');
    }
});

/**
 * Stop server
 */
stopBtn.addEventListener('click', () => {
    plugin.stopServer();
    updateStatus(false, 'WebSocket Server: Stopped');
    startBtn.disabled = false;
    stopBtn.disabled = true;
});

// Initialize
updateStatus(false);

// Check server status periodically
setInterval(() => {
    if (plugin.isRunning()) {
        if (startBtn.disabled === false) {
            startBtn.disabled = true;
            stopBtn.disabled = false;
        }
    } else {
        if (startBtn.disabled === true && stopBtn.disabled === true) {
            startBtn.disabled = false;
        }
    }
}, 1000);

