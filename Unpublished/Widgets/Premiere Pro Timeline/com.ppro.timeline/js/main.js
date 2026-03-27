/**
 * CEP Panel Main JavaScript
 * Handles WebSocket server and playhead polling
 */

(function() {
    'use strict';
    
    var csInterface = new CSInterface();
    var wsServer = null;
    var pollingInterval = null;
    var isRunning = false;
    var port = 8080;
    
    // Update UI elements
    var statusDiv = document.getElementById('status');
    var startBtn = document.getElementById('startBtn');
    var stopBtn = document.getElementById('stopBtn');
    
    /**
     * Update status display
     */
    function updateStatus(connected, message) {
        statusDiv.className = connected ? 'status connected' : 'status disconnected';
        statusDiv.textContent = message || (connected ? 'WebSocket Server: Running on port ' + port : 'WebSocket Server: Stopped');
    }
    
    /**
     * Call ExtendScript to get playhead timecode
     */
    function getPlayheadTimecode() {
        var script = 'getPlayheadTimecode()';
        
        try {
            csInterface.evalScript(script, function(result) {
                if (result && result !== 'undefined' && result !== 'null') {
                    var data;
                    try {
                        data = JSON.parse(result);
                    } catch (e) {
                        // If result is not JSON, try to evaluate it
                        data = eval('(' + result + ')');
                    }
                    
                    if (data && !data.error) {
                        broadcastTimecode(data);
                    }
                }
            });
        } catch (e) {
            console.error('Error getting timecode:', e);
        }
    }
    
    // Store latest timecode data
    var latestTimecodeData = null;
    
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
            var message = JSON.stringify(latestTimecodeData);
            
            wsServer.clients.forEach(function(client) {
                if (client.readyState === 1) { // WebSocket.OPEN
                    client.send(message);
                }
            });
        }
    }
    
    /**
     * Start WebSocket server and polling
     */
    window.startServer = function() {
        if (isRunning) return;
        
        // First, we need to inject the ExtendScript functions
        var extendScript = `
            function getPlayheadTimecode() {
                try {
                    if (!app.project || !app.project.activeSequence) {
                        return JSON.stringify({error: "No active sequence"});
                    }
                    
                    var sequence = app.project.activeSequence;
                    var playerPosition = sequence.getPlayerPosition();
                    
                    if (!playerPosition) {
                        return JSON.stringify({error: "Could not get player position"});
                    }
                    
                    // Get frame rate
                    var frameRate = sequence.timebase;
                    var ticksPerSecond = 254016000000;
                    var fps = ticksPerSecond / parseFloat(frameRate);
                    
                    // Create frame duration
                    var frameDuration = new Time();
                    frameDuration.seconds = 1.0 / fps;
                    
                    // Get display format
                    var displayFormat = sequence.videoDisplayFormat;
                    
                    // Format timecode
                    var timecodeString = playerPosition.getFormatted(frameDuration, displayFormat);
                    
                    var result = {
                        timecode: timecodeString,
                        seconds: playerPosition.seconds,
                        ticks: playerPosition.ticks,
                        sequenceName: sequence.name,
                        frameRate: fps,
                        displayFormat: displayFormat
                    };
                    
                    return JSON.stringify(result);
                } catch (e) {
                    return JSON.stringify({error: e.toString()});
                }
            }
        `;
        
        csInterface.evalScript(extendScript, function(result) {
            console.log('ExtendScript injected');
        });
        
        // Start HTTP server for WebSocket or polling
        // CEP panels can use Node.js http module
        try {
            var http = require('http');
            var url = require('url');
            
            // Try WebSocket first, fallback to HTTP polling
            var WebSocketServer = null;
            try {
                // Try to load ws module (may not be available)
                var ws = require('ws');
                WebSocketServer = ws.Server;
            } catch (wsError) {
                console.log('WebSocket module not available, using HTTP polling');
            }
            
            // Create HTTP server for both WebSocket upgrade and polling
            var httpServer = http.createServer(function(req, res) {
                var parsedUrl = url.parse(req.url, true);
                
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
            
            httpServer.listen(port, 'localhost', function() {
                console.log('HTTP server listening on port ' + port);
            });
            
            // If WebSocket is available, upgrade connections
            var actualWsServer = null;
            if (WebSocketServer) {
                actualWsServer = new WebSocketServer({ server: httpServer });
                
                actualWsServer.on('connection', function(ws) {
                    console.log('WebSocket client connected');
                    updateStatus(true, 'WebSocket Server: Client connected on port ' + port);
                    
                    // Send initial data
                    if (latestTimecodeData) {
                        ws.send(JSON.stringify(latestTimecodeData));
                    }
                    
                    ws.on('close', function() {
                        console.log('WebSocket client disconnected');
                        if (actualWsServer.clients.size === 0) {
                            updateStatus(true, 'WebSocket Server: Running (no clients) on port ' + port);
                        }
                    });
                    
                    ws.on('error', function(error) {
                        console.error('WebSocket error:', error);
                    });
                });
                
                updateStatus(true, 'WebSocket Server: Running on port ' + port);
            } else {
                updateStatus(true, 'HTTP Server: Running on port ' + port + ' (polling mode)');
            }
            
            // Store server reference
            wsServer = { 
                server: httpServer, 
                wsServer: actualWsServer,
                clients: actualWsServer ? actualWsServer.clients : []
            };
            
            isRunning = true;
            startBtn.disabled = true;
            stopBtn.disabled = false;
            
            // Start polling playhead position
            pollingInterval = setInterval(function() {
                getPlayheadTimecode();
            }, 100); // Poll every 100ms for smooth updates
            
        } catch (e) {
            console.error('Error starting server:', e);
            alert('Error starting server: ' + e.message + '\n\nUsing file polling fallback.');
            startFilePolling();
        }
    };
    
    /**
     * Fallback: File-based polling (simpler, no dependencies)
     */
    function startFilePolling() {
        var fs = require('fs');
        var path = require('path');
        var dataFile = path.join(csInterface.getSystemPath(SystemPath.USER_DATA), 'ppro_timeline_data.json');
        
        isRunning = true;
        startBtn.disabled = true;
        stopBtn.disabled = false;
        updateStatus(true, 'File Polling: Active (check web client for file path)');
        
        pollingInterval = setInterval(function() {
            getPlayheadTimecode();
        }, 100);
        
        // Also write to file for file-based clients
        var originalBroadcast = broadcastTimecode;
        broadcastTimecode = function(data) {
            originalBroadcast(data);
            try {
                fs.writeFileSync(dataFile, JSON.stringify({
                    type: 'timecode',
                    data: data,
                    timestamp: Date.now()
                }));
            } catch (e) {
                console.error('Error writing file:', e);
            }
        };
    }
    
    /**
     * Stop WebSocket server and polling
     */
    window.stopServer = function() {
        if (!isRunning) return;
        
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
        
        if (wsServer) {
            if (wsServer.server) {
                wsServer.server.close();
            } else if (wsServer.close) {
                wsServer.close();
            }
            wsServer = null;
        }
        
        isRunning = false;
        startBtn.disabled = false;
        stopBtn.disabled = true;
        updateStatus(false, 'WebSocket Server: Stopped');
    };
    
    // Initialize
    updateStatus(false);
    
    // Cleanup on panel close
    window.addEventListener('beforeunload', function() {
        window.stopServer();
    });
    
})();

