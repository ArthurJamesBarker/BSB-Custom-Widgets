// UI Controller for Bluetooth-only operation

// Ensure CAMERA_CONFIG is defined (fallback if config.js fails to load)
if (typeof CAMERA_CONFIG === 'undefined') {
    console.error('CAMERA_CONFIG is not defined! Make sure js/config.js is loaded before app.js');
    // Provide a minimal default config to prevent crashes
    window.CAMERA_CONFIG = {
        bluetooth: {
            serviceUUID: '291d567a-6d75-11e6-8b77-86f30ca893d3',
            outgoingControlUUID: '5dd3465f-1aee-4299-8493-d2eca2f8e1bb',
            incomingControlUUID: 'b864e140-76a0-416a-bf30-5876504537d9',
            timecodeUUID: '6d8f2110-86f1-41bf-9afb-451d87e976c8',
            statusUUID: '7fe8691d-95dc-4fc5-8abd-ca74339b51b9'
        },
        busyBar: {
            enabled: false,
            connections: {
                usb: 'http://10.0.4.20',
                wifi: 'http://10.46.30.146'
            },
            defaultConnection: 'usb',
            appId: 'blackmagic-camera-control'
        }
    };
}

class UIController {
    constructor() {
        this.bluetoothClient = null;
        this.controller = null;
        this.busyBarClient = null;
        this.currentBusyBarConnection = null;
        this.initializeElements();
        this.attachEventListeners();
        this.initializeBusyBar();
    }

    initializeBusyBar(connectionType = null) {
        // Get connection type from parameter or config default
        if (!connectionType) {
            connectionType = CAMERA_CONFIG?.busyBar?.defaultConnection || 'usb';
        }
        
        // Get IP address from config
        const connections = CAMERA_CONFIG?.busyBar?.connections;
        if (!connections || !connections[connectionType]) {
            console.warn(`Busy Bar connection type "${connectionType}" not found in config`);
            this.busyBarClient = null;
            return;
        }
        
        const ip = connections[connectionType];
        const appId = CAMERA_CONFIG?.busyBar?.appId || 'blackmagic-camera-control';
        
        // Initialize Busy Bar client if enabled
        if (CAMERA_CONFIG?.busyBar?.enabled) {
            try {
                this.busyBarClient = new BusyBarClient(ip, appId);
                this.currentBusyBarConnection = connectionType;
                console.log(`Busy Bar client initialized with ${connectionType} connection (${ip})`);
            } catch (error) {
                console.error('Failed to initialize Busy Bar client:', error);
                this.busyBarClient = null;
                this.currentBusyBarConnection = null;
            }
        }
    }

    initializeElements() {
        this.elements = {
            connectionStatus: document.getElementById('connectionStatus'),
            statusIndicator: document.getElementById('statusIndicator'),
            statusText: document.getElementById('statusText'),
            scanBluetoothBtn: document.getElementById('scanBluetoothBtn'),
            disconnectBluetoothBtn: document.getElementById('disconnectBluetoothBtn'),
            deviceList: document.getElementById('deviceList'),
            recordingStatus: document.getElementById('recordingStatus'),
            statusValue: document.getElementById('statusValue'),
            recordingIndicator: document.getElementById('recordingIndicator'),
            timecodeValue: document.getElementById('timecodeValue'),
            startRecordBtn: document.getElementById('startRecordBtn'),
            stopRecordBtn: document.getElementById('stopRecordBtn'),
            deviceName: document.getElementById('deviceName'),
            productName: document.getElementById('productName'),
            softwareVersion: document.getElementById('softwareVersion'),
            errorMessage: document.getElementById('errorMessage'),
            busyBarStatusValue: document.getElementById('busyBarStatusValue'),
            uploadImagesBtn: document.getElementById('uploadImagesBtn'),
            busyBarConnectionType: document.getElementById('busyBarConnectionType'),
            busyBarConnectBtn: document.getElementById('busyBarConnectBtn'),
        };
        
        // Set default connection type in dropdown
        if (this.elements.busyBarConnectionType) {
            const defaultConnection = CAMERA_CONFIG?.busyBar?.defaultConnection || 'usb';
            this.elements.busyBarConnectionType.value = defaultConnection;
        }
    }

    attachEventListeners() {
        this.elements.scanBluetoothBtn.addEventListener('click', () => this.handleBluetoothScan());
        this.elements.disconnectBluetoothBtn.addEventListener('click', () => this.handleBluetoothDisconnect());
        this.elements.startRecordBtn.addEventListener('click', () => this.handleStartRecording());
        this.elements.stopRecordBtn.addEventListener('click', () => this.handleStopRecording());
        this.elements.uploadImagesBtn.addEventListener('click', () => this.handleUploadImages());
        this.elements.busyBarConnectBtn.addEventListener('click', () => this.handleBusyBarConnect());
    }

    async handleBluetoothScan() {
        if (!this.bluetoothClient) {
            this.bluetoothClient = new BluetoothCameraClient();
        }

        if (!this.bluetoothClient.isAvailable()) {
            this.showError('Web Bluetooth API is not available. Please use Chrome, Edge, or Opera browser. Also ensure you are accessing via HTTPS or localhost.');
            return;
        }

        this.hideError();
        this.elements.scanBluetoothBtn.disabled = true;
        this.elements.scanBluetoothBtn.textContent = 'Scanning...';

        try {
            // Disconnect any existing connection
            if (this.bluetoothClient && this.bluetoothClient.isConnected()) {
                await this.bluetoothClient.disconnect();
            }
            
            const device = await this.bluetoothClient.scanForCameras();
            
            // Add device to list
            this.addDeviceToList(device);
            
            // Auto-connect to the device
            await this.connectToBluetoothDevice(device);
        } catch (error) {
            this.showError(error.message || 'Failed to scan for cameras');
        } finally {
            this.elements.scanBluetoothBtn.disabled = false;
            this.elements.scanBluetoothBtn.textContent = 'Scan for Cameras';
        }
    }

    addDeviceToList(device) {
        const deviceList = this.elements.deviceList;
        deviceList.innerHTML = '';
        
        const deviceItem = document.createElement('div');
        deviceItem.className = 'device-item';
        deviceItem.innerHTML = `
            <div class="device-info">
                <span class="device-name">${device.name || 'Unknown Device'}</span>
                <span class="device-id">${device.id}</span>
            </div>
        `;
        deviceList.appendChild(deviceItem);
    }

    async connectToBluetoothDevice(device) {
        this.hideError();
        
        try {
            await this.bluetoothClient.connectToCamera(device);
            
            // Set up callbacks
            this.bluetoothClient.setTimecodeCallback((timecode) => {
                this.updateTimecode(timecode);
            });
            
            this.bluetoothClient.setStatusCallback((status) => {
                // Handle status updates if needed
                console.log('Camera status update:', status);
            });
            
            // Set up recording state callback to detect changes from camera
            this.bluetoothClient.setRecordingStateCallback((isRecording) => {
                console.log('Recording state changed from camera:', isRecording);
                this.updateRecordingStatus(isRecording);
            });
            
            // Create controller wrapper for unified interface
            this.controller = {
                startRecording: () => this.bluetoothClient.startRecording(),
                stopRecording: () => this.bluetoothClient.stopRecording(),
                getRecordingState: () => this.bluetoothClient.getRecordingState(),
                getTimecode: () => Promise.resolve({ display: '--:--:--:--', timeline: '--:--:--:--' }),
                getCameraInfo: () => this.bluetoothClient.getCameraInfo(),
                checkConnection: () => Promise.resolve(this.bluetoothClient.isConnected()),
                startTimecodeUpdates: (callback) => {
                    this.bluetoothClient.setTimecodeCallback(callback);
                },
                startStatusUpdates: (callback) => {
                    this.bluetoothClient.setRecordingStateCallback(callback);
                    // Poll recording state periodically for Bluetooth
                    this.statusUpdateInterval = setInterval(async () => {
                        const isRecording = await this.bluetoothClient.getRecordingState();
                        callback(isRecording);
                    }, 2000);
                },
                stopTimecodeUpdates: () => {
                    this.bluetoothClient.setTimecodeCallback(null);
                },
                stopStatusUpdates: () => {
                    if (this.statusUpdateInterval) {
                        clearInterval(this.statusUpdateInterval);
                        this.statusUpdateInterval = null;
                    }
                },
                disconnect: () => this.bluetoothClient.disconnect()
            };
            
            this.setConnectionStatus(true, `Connected (Bluetooth): ${device.name}`);
            await this.loadCameraInfo();
            
            // Initialize Busy Bar if enabled
            await this.initializeBusyBarConnection();
            
            this.startUpdates();
            this.elements.disconnectBluetoothBtn.style.display = 'block';
            this.showSuccess('Connected to camera via Bluetooth');
        } catch (error) {
            this.setConnectionStatus(false, 'Connection Failed');
            this.showError(error.message || 'Failed to connect to camera');
        }
    }

    async initializeBusyBarConnection() {
        if (!this.busyBarClient) {
            this.updateBusyBarStatus('Disabled');
            return;
        }

        try {
            this.updateBusyBarStatus('Connecting...');
            
            // Reset connection state before checking
            this.busyBarClient.resetConnectionState();
            
            // Check if Busy Bar is reachable
            const isReachable = await this.busyBarClient.checkConnection();
            if (!isReachable) {
                this.updateBusyBarStatus('Not Reachable');
                console.warn('Busy Bar is not reachable. Status display will not work.');
                this.elements.uploadImagesBtn.style.display = 'block';
                return;
            }

            // Upload status images
            this.updateBusyBarStatus('Uploading Images...');
            console.log('Uploading status images to Busy Bar...');
            await this.busyBarClient.uploadStatusImages();
            
            // Display initial standby status
            await this.busyBarClient.showRecordingStatus(false);
            this.updateBusyBarStatus('Ready - Images Uploaded');
            this.elements.uploadImagesBtn.style.display = 'none';
            console.log('Busy Bar initialized and showing standby status');
        } catch (error) {
            console.error('Failed to initialize Busy Bar connection:', error);
            this.updateBusyBarStatus(`Error: ${error.message}`);
            this.elements.uploadImagesBtn.style.display = 'block';
            // Don't throw - allow camera control to continue working
        }
    }

    async handleUploadImages() {
        if (!this.busyBarClient) {
            this.showError('Busy Bar client not initialized');
            return;
        }

        this.elements.uploadImagesBtn.disabled = true;
        this.elements.uploadImagesBtn.textContent = 'Uploading...';
        this.hideError();

        try {
            // Reset connection state before retrying
            this.busyBarClient.resetConnectionState();
            
            this.updateBusyBarStatus('Uploading Images...');
            await this.busyBarClient.uploadStatusImages();
            await this.busyBarClient.showRecordingStatus(false);
            this.updateBusyBarStatus('Ready - Images Uploaded');
            this.elements.uploadImagesBtn.style.display = 'none';
            this.showSuccess('Images uploaded to Busy Bar successfully');
        } catch (error) {
            this.updateBusyBarStatus(`Upload Failed: ${error.message}`);
            this.showError(`Failed to upload images: ${error.message}`);
        } finally {
            this.elements.uploadImagesBtn.disabled = false;
            this.elements.uploadImagesBtn.textContent = 'Upload Images to Busy Bar';
        }
    }

    async handleBusyBarConnect() {
        if (!CAMERA_CONFIG?.busyBar?.enabled) {
            this.showError('Busy Bar is disabled in configuration');
            return;
        }

        const connectionType = this.elements.busyBarConnectionType.value;
        const connections = CAMERA_CONFIG.busyBar.connections;
        
        if (!connections || !connections[connectionType]) {
            this.showError(`Invalid connection type: ${connectionType}`);
            return;
        }

        this.hideError();
        this.elements.busyBarConnectBtn.disabled = true;
        this.elements.busyBarConnectBtn.textContent = 'Connecting...';
        this.updateBusyBarStatus('Connecting...');

        try {
            // Clear existing Busy Bar display if connected
            if (this.busyBarClient) {
                try {
                    await this.busyBarClient.clearDisplay();
                } catch (error) {
                    console.debug('Failed to clear previous Busy Bar display:', error);
                }
            }

            // Initialize with new connection type
            this.initializeBusyBar(connectionType);

            if (!this.busyBarClient) {
                throw new Error('Failed to initialize Busy Bar client');
            }

            // Initialize connection
            await this.initializeBusyBarConnection();
            this.showSuccess(`Connected to Busy Bar via ${connectionType.toUpperCase()}`);
        } catch (error) {
            console.error('Failed to connect to Busy Bar:', error);
            this.updateBusyBarStatus(`Connection Failed: ${error.message}`);
            this.showError(`Failed to connect to Busy Bar: ${error.message}`);
        } finally {
            this.elements.busyBarConnectBtn.disabled = false;
            this.elements.busyBarConnectBtn.textContent = 'Connect';
        }
    }

    updateBusyBarStatus(status) {
        if (this.elements.busyBarStatusValue) {
            this.elements.busyBarStatusValue.textContent = status;
        }
    }

    async handleBluetoothDisconnect() {
        try {
            await this.bluetoothClient.disconnect();
            this.controller = null;
            
            // Clear Busy Bar display on disconnect
            if (this.busyBarClient) {
                try {
                    await this.busyBarClient.clearDisplay();
                } catch (error) {
                    console.error('Failed to clear Busy Bar display:', error);
                }
                this.updateBusyBarStatus('Disconnected');
                this.elements.uploadImagesBtn.style.display = 'none';
            }
            
            this.setConnectionStatus(false, 'Disconnected');
            this.elements.disconnectBluetoothBtn.style.display = 'none';
            this.elements.deviceList.innerHTML = '<p class="no-devices">No devices found. Click "Scan for Cameras" to search.</p>';
            this.showSuccess('Disconnected from camera');
        } catch (error) {
            this.showError(error.message || 'Failed to disconnect');
        }
    }

    async checkConnection() {
        if (!this.controller) return false;
        
        const isConnected = await this.controller.checkConnection();
        this.setConnectionStatus(isConnected, isConnected ? 'Connected' : 'Disconnected');
        return isConnected;
    }

    setConnectionStatus(connected, text) {
        this.elements.statusIndicator.className = `status-indicator ${connected ? 'connected' : 'disconnected'}`;
        this.elements.statusText.textContent = text;
    }

    async loadCameraInfo() {
        if (!this.controller) return;
        
        try {
            const info = await this.controller.getCameraInfo();
            this.elements.deviceName.textContent = info.deviceName || '--';
            this.elements.productName.textContent = info.productName || '--';
            this.elements.softwareVersion.textContent = info.softwareVersion || '--';
        } catch (error) {
            console.error('Failed to load camera info:', error);
        }
    }

    updateRecordingStatus(isRecording) {
        this.elements.statusValue.textContent = isRecording ? 'Recording' : 'Stopped';
        this.elements.recordingIndicator.className = `recording-indicator ${isRecording ? 'active' : ''}`;
        this.elements.startRecordBtn.disabled = isRecording;
        this.elements.stopRecordBtn.disabled = !isRecording;
        
        // Update Busy Bar display
        if (this.busyBarClient) {
            // showRecordingStatus now handles errors gracefully, so we don't need to catch
            this.busyBarClient.showRecordingStatus(isRecording).catch(error => {
                // Only log if there's an unexpected error
                console.debug('Busy Bar display update:', error.message || 'Skipped (device unreachable)');
            });
        }
    }

    updateTimecode(timecode) {
        if (timecode && timecode.display) {
            this.elements.timecodeValue.textContent = timecode.display;
        }
    }

    async handleStartRecording() {
        if (!this.controller) {
            this.showError('Not connected to camera');
            return;
        }

        this.hideError();
        this.elements.startRecordBtn.disabled = true;
        
        try {
            await this.controller.startRecording();
            this.updateRecordingStatus(true);
            this.showSuccess('Recording started');
        } catch (error) {
            this.showError(error.message || 'Failed to start recording');
            this.updateRecordingStatus(false);
        } finally {
            this.elements.startRecordBtn.disabled = false;
        }
    }

    async handleStopRecording() {
        if (!this.controller) {
            this.showError('Not connected to camera');
            return;
        }

        this.hideError();
        this.elements.stopRecordBtn.disabled = true;
        
        try {
            await this.controller.stopRecording();
            this.updateRecordingStatus(false);
            this.showSuccess('Recording stopped');
        } catch (error) {
            this.showError(error.message || 'Failed to stop recording');
        } finally {
            this.elements.stopRecordBtn.disabled = false;
        }
    }

    startUpdates() {
        if (!this.controller) return;
        
        // Start timecode updates
        this.controller.startTimecodeUpdates((timecode) => {
            this.updateTimecode(timecode);
        });

        // Start status updates
        this.controller.startStatusUpdates((isRecording) => {
            this.updateRecordingStatus(isRecording);
        });
    }

    showError(message) {
        this.elements.errorMessage.textContent = message;
        this.elements.errorMessage.className = 'error-message visible error';
        setTimeout(() => {
            this.elements.errorMessage.className = 'error-message';
        }, 5000);
    }

    showSuccess(message) {
        this.elements.errorMessage.textContent = message;
        this.elements.errorMessage.className = 'error-message visible success';
        setTimeout(() => {
            this.elements.errorMessage.className = 'error-message';
        }, 3000);
    }

    hideError() {
        this.elements.errorMessage.className = 'error-message';
    }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const ui = new UIController();
    // Don't auto-initialize - let user choose connection mode
});
