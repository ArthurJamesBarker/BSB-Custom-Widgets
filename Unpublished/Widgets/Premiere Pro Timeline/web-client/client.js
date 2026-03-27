/**
 * WebSocket Client for Premiere Pro Timeline Timecode
 */

(function() {
    'use strict';
    
    var ws = null;
    var pollingInterval = null;
    var updateCount = 0;
    var wsUrl = 'ws://localhost:8080';
    var httpUrl = 'http://localhost:8080/timecode';
    var useWebSocket = true;
    var reconnectAttempts = 0;
    var maxReconnectAttempts = 10;
    var reconnectDelay = 3000;
    
    // DOM elements
    var timecodeDisplay = document.getElementById('timecodeDisplay');
    var statusDiv = document.getElementById('status');
    var sequenceName = document.getElementById('sequenceName');
    var frameRate = document.getElementById('frameRate');
    var seconds = document.getElementById('seconds');
    var updateCountEl = document.getElementById('updateCount');
    var connectBtn = document.getElementById('connectBtn');
    var disconnectBtn = document.getElementById('disconnectBtn');
    
    /**
     * Update status display
     */
    function updateStatus(status, message) {
        statusDiv.className = 'status ' + status;
        statusDiv.textContent = message || status;
    }
    
    /**
     * Update timecode display
     */
    function updateTimecode(data) {
        if (!data || data.error) {
            timecodeDisplay.textContent = data && data.error ? data.error : 'No data';
            timecodeDisplay.className = 'timecode-display connecting';
            return;
        }
        
        timecodeDisplay.textContent = data.data.timecode || '00:00:00:00';
        timecodeDisplay.className = 'timecode-display';
        
        if (data.data.sequenceName) {
            sequenceName.textContent = data.data.sequenceName;
        }
        
        if (data.data.frameRate) {
            frameRate.textContent = data.data.frameRate.toFixed(2) + ' fps';
        }
        
        if (data.data.seconds !== undefined) {
            seconds.textContent = data.data.seconds.toFixed(3) + 's';
        }
        
        updateCount++;
        updateCountEl.textContent = updateCount;
    }
    
    /**
     * Connect via WebSocket
     */
    function connectWebSocket() {
        try {
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                console.log('WebSocket connected');
                updateStatus('connected', 'Connected via WebSocket');
                reconnectAttempts = 0;
                connectBtn.disabled = true;
                disconnectBtn.disabled = false;
            };
            
            ws.onmessage = function(event) {
                try {
                    var data = JSON.parse(event.data);
                    updateTimecode(data);
                } catch (e) {
                    console.error('Error parsing message:', e);
                }
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                updateStatus('disconnected', 'WebSocket error - trying HTTP polling');
                // Fallback to HTTP polling
                useWebSocket = false;
                connectHttp();
            };
            
            ws.onclose = function() {
                console.log('WebSocket closed');
                updateStatus('disconnected', 'Disconnected');
                connectBtn.disabled = false;
                disconnectBtn.disabled = true;
                
                // Attempt to reconnect
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++;
                    setTimeout(function() {
                        console.log('Attempting to reconnect... (' + reconnectAttempts + '/' + maxReconnectAttempts + ')');
                        updateStatus('connecting', 'Reconnecting... (' + reconnectAttempts + '/' + maxReconnectAttempts + ')');
                        connectWebSocket();
                    }, reconnectDelay);
                } else {
                    updateStatus('disconnected', 'Connection failed. Please check if the server is running.');
                }
            };
            
        } catch (e) {
            console.error('Error creating WebSocket:', e);
            updateStatus('disconnected', 'WebSocket not available - using HTTP polling');
            useWebSocket = false;
            connectHttp();
        }
    }
    
    /**
     * Connect via HTTP polling (fallback)
     */
    function connectHttp() {
        updateStatus('connected', 'Connected via HTTP polling');
        connectBtn.disabled = true;
        disconnectBtn.disabled = false;
        
        // Poll every 100ms
        pollingInterval = setInterval(function() {
            fetch(httpUrl)
                .then(function(response) {
                    return response.json();
                })
                .then(function(data) {
                    updateTimecode(data);
                })
                .catch(function(error) {
                    console.error('Polling error:', error);
                    if (!pollingInterval) {
                        // Connection lost, try to reconnect
                        updateStatus('disconnected', 'Connection lost');
                        connectBtn.disabled = false;
                        disconnectBtn.disabled = true;
                    }
                });
        }, 100);
    }
    
    /**
     * Connect to server
     */
    window.connect = function() {
        if (ws && ws.readyState === WebSocket.OPEN) {
            return; // Already connected
        }
        
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
        
        updateStatus('connecting', 'Connecting...');
        reconnectAttempts = 0;
        
        // Try WebSocket first
        if (useWebSocket) {
            connectWebSocket();
        } else {
            connectHttp();
        }
    };
    
    /**
     * Disconnect from server
     */
    window.disconnect = function() {
        reconnectAttempts = maxReconnectAttempts; // Prevent auto-reconnect
        
        if (ws) {
            ws.close();
            ws = null;
        }
        
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
        
        updateStatus('disconnected', 'Disconnected');
        connectBtn.disabled = false;
        disconnectBtn.disabled = true;
        timecodeDisplay.textContent = 'Disconnected';
        timecodeDisplay.className = 'timecode-display connecting';
    };
    
    // Auto-connect on page load
    window.addEventListener('load', function() {
        setTimeout(function() {
            window.connect();
        }, 500);
    });
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
        window.disconnect();
    });
    
})();

