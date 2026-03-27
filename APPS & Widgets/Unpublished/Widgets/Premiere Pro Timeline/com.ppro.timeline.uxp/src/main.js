/**
 * UXP Plugin Main Entry Point
 * Handles WebSocket server and playhead polling using direct UXP API access
 * 
 * Note: UXP API access for Premiere Pro uses the global 'app' object
 * which is available in the UXP context. No require() needed for app.
 */

// In UXP, the 'app' object is globally available
// This is the Premiere Pro application object

const http = require('http');
const url = require('url');

let wsServer = null;
let pollingInterval = null;
let isRunning = false;
let latestTimecodeData = null;
const port = 8080;

/**
 * Get the current playhead position as formatted timecode
 * Uses direct UXP API access (no evalScript needed)
 */
function getPlayheadTimecode() {
    try {
        // In UXP, 'app' is globally available
        // Check if app and project are available
        if (typeof app === 'undefined') {
            return { error: "Premiere Pro API not available. Make sure plugin is running in Premiere Pro." };
        }
        
        if (!app.project || !app.project.activeSequence) {
            return { error: "No active sequence. Please open a sequence in Premiere Pro." };
        }
        
        const sequence = app.project.activeSequence;
        const playerPosition = sequence.getPlayerPosition();
        
        if (!playerPosition) {
            return { error: "Could not get player position" };
        }
        
        // Get frame rate
        const frameRate = sequence.timebase;
        const ticksPerSecond = 254016000000;
        const fps = ticksPerSecond / parseFloat(frameRate);
        
        // Create frame duration
        const frameDuration = new Time();
        frameDuration.seconds = 1.0 / fps;
        
        // Get display format
        const displayFormat = sequence.videoDisplayFormat;
        
        // Format timecode
        const timecodeString = playerPosition.getFormatted(frameDuration, displayFormat);
        
        return {
            timecode: timecodeString,
            seconds: playerPosition.seconds,
            ticks: playerPosition.ticks,
            sequenceName: sequence.name,
            frameRate: fps,
            displayFormat: displayFormat
        };
    } catch (e) {
        console.error('Error getting playhead timecode:', e);
        return { error: e.toString() };
    }
}

/**
 * Broadcast timecode to all connected WebSocket clients
 */
function broadcastTimecode(data) {
    latestTimecodeData = {
        type: 'timecode',
        data: data,
        timestamp: Date.now()
    };
    
    if (wsServer && wsServer.wsServer && wsServer.clients) {
        const message = JSON.stringify(latestTimecodeData);
        
        wsServer.clients.forEach((client) => {
            if (client.readyState === 1) { // WebSocket.OPEN
                client.send(message);
            }
        });
    }
}

/**
 * Start HTTP/WebSocket server and polling
 */
function startServer() {
    if (isRunning) return;
    
    try {
        // Try WebSocket first, fallback to HTTP polling
        let WebSocketServer = null;
        try {
            const ws = require('ws');
            WebSocketServer = ws.Server;
        } catch (wsError) {
            console.log('WebSocket module not available, using HTTP polling only');
        }
        
        // Create HTTP server for both WebSocket upgrade and polling
        const httpServer = http.createServer((req, res) => {
            const parsedUrl = url.parse(req.url, true);
            
            // CORS headers
            res.setHeader('Access-Control-Allow-Origin', '*');
            res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
            res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
            
            if (req.method === 'OPTIONS') {
                res.writeHead(200);
                res.end();
                return;
            }
            
            // Polling endpoint
            if (parsedUrl.pathname === '/timecode' || parsedUrl.pathname === '/') {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(latestTimecodeData || { error: 'No data yet' }));
                return;
            }
            
            res.writeHead(404);
            res.end('Not found');
        });
        
        httpServer.listen(port, 'localhost', () => {
            console.log(`HTTP server listening on port ${port}`);
        });
        
        // If WebSocket is available, upgrade connections
        let actualWsServer = null;
        if (WebSocketServer) {
            actualWsServer = new WebSocketServer({ server: httpServer });
            
            actualWsServer.on('connection', (ws) => {
                console.log('WebSocket client connected');
                
                // Send initial data
                if (latestTimecodeData) {
                    ws.send(JSON.stringify(latestTimecodeData));
                }
                
                ws.on('close', () => {
                    console.log('WebSocket client disconnected');
                });
                
                ws.on('error', (error) => {
                    console.error('WebSocket error:', error);
                });
            });
        }
        
        // Store server reference
        wsServer = { 
            server: httpServer, 
            wsServer: actualWsServer,
            clients: actualWsServer ? actualWsServer.clients : []
        };
        
        isRunning = true;
        
        // Start polling playhead position
        pollingInterval = setInterval(() => {
            const timecodeData = getPlayheadTimecode();
            if (timecodeData && !timecodeData.error) {
                broadcastTimecode(timecodeData);
            }
        }, 100); // Poll every 100ms for smooth updates
        
        console.log(`Server started on port ${port}`);
        return true;
        
    } catch (e) {
        console.error('Error starting server:', e);
        return false;
    }
}

/**
 * Stop WebSocket server and polling
 */
function stopServer() {
    if (!isRunning) return;
    
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
    
    if (wsServer) {
        if (wsServer.server) {
            wsServer.server.close();
        }
        wsServer = null;
    }
    
    isRunning = false;
    console.log('Server stopped');
}

// Export functions for panel UI
module.exports = {
    startServer,
    stopServer,
    getPlayheadTimecode,
    isRunning: () => isRunning
};

