// Bluetooth LE Client for Blackmagic Camera Control
// Uses Web Bluetooth API to communicate with cameras via Bluetooth LE

class BluetoothCameraClient {
    constructor() {
        this.device = null;
        this.server = null;
        this.cameraService = null;
        this.outgoingControl = null;
        this.incomingControl = null;
        this.timecodeCharacteristic = null;
        this.statusCharacteristic = null;
        this.sdiProtocol = new SDIProtocol();
        
        // UUIDs from CAMERA_CONFIG (single source of truth)
        this.SERVICE_UUID = CAMERA_CONFIG.bluetooth.serviceUUID;
        this.OUTGOING_CONTROL_UUID = CAMERA_CONFIG.bluetooth.outgoingControlUUID;
        this.INCOMING_CONTROL_UUID = CAMERA_CONFIG.bluetooth.incomingControlUUID;
        this.TIMECODE_UUID = CAMERA_CONFIG.bluetooth.timecodeUUID;
        this.STATUS_UUID = CAMERA_CONFIG.bluetooth.statusUUID;
        
        // Callbacks
        this.timecodeCallback = null;
        this.statusCallback = null;
        this.controlCallback = null;
        this.recordingStateCallback = null;
        
        this.isRecording = false;
    }

    /**
     * Check if Web Bluetooth API is available
     * @returns {boolean}
     */
    isAvailable() {
        return 'bluetooth' in navigator;
    }

    /**
     * Scan for Blackmagic cameras
     * @returns {Promise<BluetoothDevice>}
     */
    async scanForCameras() {
        if (!this.isAvailable()) {
            throw new Error('Web Bluetooth API is not available in this browser. Please use Chrome, Edge, or Opera.');
        }

        try {
            const device = await navigator.bluetooth.requestDevice({
                filters: [{
                    services: [this.SERVICE_UUID]
                }],
                optionalServices: ['0000180a-0000-1000-8000-00805f9b34fb'] // Device Information Service (full UUID)
            });

            return device;
        } catch (error) {
            if (error.name === 'NotFoundError') {
                throw new Error('No Blackmagic camera found. Make sure Bluetooth is enabled on the camera and it is discoverable.');
            } else if (error.name === 'SecurityError') {
                throw new Error('Bluetooth access denied. Please allow Bluetooth access in your browser settings.');
            } else if (error.name === 'InvalidStateError') {
                throw new Error('Bluetooth is already in use. Please disconnect first.');
            }
            throw error;
        }
    }

    /**
     * Connect to a Bluetooth device
     * @param {BluetoothDevice} device - The device to connect to
     * @returns {Promise<void>}
     */
    async connectToCamera(device) {
        this.device = device;
        
        // Handle disconnection
        this.device.addEventListener('gattserverdisconnected', () => {
            this.handleDisconnection();
        });

        try {
            this.server = await this.device.gatt.connect();
            this.cameraService = await this.server.getPrimaryService(this.SERVICE_UUID);
            
            // Get characteristics
            this.outgoingControl = await this.cameraService.getCharacteristic(this.OUTGOING_CONTROL_UUID);
            this.incomingControl = await this.cameraService.getCharacteristic(this.INCOMING_CONTROL_UUID);
            this.timecodeCharacteristic = await this.cameraService.getCharacteristic(this.TIMECODE_UUID);
            this.statusCharacteristic = await this.cameraService.getCharacteristic(this.STATUS_UUID);
            
            // Subscribe to notifications
            await this.subscribeToNotifications();
            
            return true;
        } catch (error) {
            console.error('Error connecting to camera:', error);
            throw new Error(`Failed to connect to camera: ${error.message}`);
        }
    }

    /**
     * Subscribe to characteristic notifications
     * @returns {Promise<void>}
     */
    async subscribeToNotifications() {
        try {
            // Subscribe to timecode updates
            if (this.timecodeCharacteristic) {
                await this.timecodeCharacteristic.startNotifications();
                this.timecodeCharacteristic.addEventListener('characteristicvaluechanged', (event) => {
                    this.handleTimecodeUpdate(event.target.value);
                });
            }

            // Subscribe to status updates
            if (this.statusCharacteristic) {
                await this.statusCharacteristic.startNotifications();
                this.statusCharacteristic.addEventListener('characteristicvaluechanged', (event) => {
                    this.handleStatusUpdate(event.target.value);
                });
            }

            // Subscribe to incoming control messages
            if (this.incomingControl) {
                await this.incomingControl.startNotifications();
                this.incomingControl.addEventListener('characteristicvaluechanged', (event) => {
                    this.handleControlMessage(event.target.value);
                });
            }
        } catch (error) {
            console.error('Error subscribing to notifications:', error);
            throw new Error(`Failed to subscribe to notifications: ${error.message}`);
        }
    }

    /**
     * Handle timecode updates
     * @param {DataView} value - Timecode data
     */
    handleTimecodeUpdate(value) {
        if (this.timecodeCallback) {
            const timecode = this.sdiProtocol.decodeTimecodeFromArray(new Uint8Array(value.buffer));
            this.timecodeCallback({ display: timecode, timeline: timecode });
        }
    }

    /**
     * Handle status updates
     * @param {DataView} value - Status data
     */
    handleStatusUpdate(value) {
        if (value.byteLength > 0) {
            const flags = value.getUint8(0);
            const status = this.sdiProtocol.decodeCameraStatus(flags);
            
            if (this.statusCallback) {
                this.statusCallback(status);
            }
        }
    }

    /**
     * Handle incoming control messages
     * @param {DataView} value - Control message data
     */
    handleControlMessage(value) {
        // Parse transport state from incoming messages
        // Incoming messages follow SDI protocol format
        try {
            console.log('Incoming control message, length:', value.byteLength);
            if (value.byteLength >= 4) {
                // Log raw bytes for debugging
                const bytes = [];
                for (let i = 0; i < Math.min(value.byteLength, 20); i++) {
                    bytes.push('0x' + value.getUint8(i).toString(16).padStart(2, '0'));
                }
                console.log('Control message bytes:', bytes.join(' '));
                
                // Check if this is a transport mode message (Group 10, Parameter 1)
                // Skip header (4 bytes) and check category/parameter
                if (value.byteLength >= 10) {
                    const category = value.getUint8(4); // Group 10 = Media
                    const parameter = value.getUint8(5); // Parameter 1 = Transport mode
                    
                    console.log('Parsing message - category:', category, 'parameter:', parameter);
                    
                    if (category === 10 && parameter === 1) {
                        // This is a transport mode update
                        const dataType = value.getUint8(6);
                        const operation = value.getUint8(7);
                        
                        console.log('Transport mode message - dataType:', dataType, 'operation:', operation);
                        
                        // Operation 0 = assign (command), Operation 2 = notification/response
                        // Both can contain transport mode information
                        if (dataType === 1 && (operation === 0 || operation === 2)) {
                            // Extract transport mode from data section (byte 8)
                            const mode = value.getInt8(8);
                            const wasRecording = this.isRecording;
                            this.isRecording = (mode === 2); // Mode 2 = Record
                            
                            console.log('Transport mode:', mode, 'isRecording:', this.isRecording);
                            
                            // Always notify callback when we receive a transport state update
                            // This ensures UI updates even if state didn't change
                            if (this.recordingStateCallback) {
                                console.log(`Recording state update from camera: ${this.isRecording ? 'Recording' : 'Stopped'}`);
                                this.recordingStateCallback(this.isRecording);
                            }
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Error parsing control message:', error);
        }
        
        if (this.controlCallback) {
            this.controlCallback(value);
        }
    }

    /**
     * Send a control message to the camera
     * @param {ArrayBuffer} packet - SDI protocol packet
     * @returns {Promise<void>}
     */
    async sendControlMessage(packet) {
        if (!this.outgoingControl) {
            throw new Error('Not connected to camera');
        }

        try {
            // Convert ArrayBuffer to Uint8Array for writeValue
            const dataView = new Uint8Array(packet);
            console.log('Writing to characteristic:', this.OUTGOING_CONTROL_UUID);
            console.log('Data to write:', Array.from(dataView).map(b => '0x' + b.toString(16).padStart(2, '0')).join(' '));
            
            await this.outgoingControl.writeValue(dataView);
            console.log('Control message written successfully');
        } catch (error) {
            console.error('Error sending control message:', error);
            console.error('Error details:', {
                name: error.name,
                message: error.message,
                stack: error.stack
            });
            throw new Error(`Failed to send control message: ${error.message}`);
        }
    }

    /**
     * Start recording
     * @returns {Promise<void>}
     */
    async startRecording() {
        try {
            const packet = this.sdiProtocol.encodeRecordCommand();
            console.log('Sending record command, packet length:', packet.byteLength);
            console.log('Packet bytes:', new Uint8Array(packet));
            await this.sendControlMessage(packet);
            // Don't set isRecording here - wait for camera confirmation via control message
            // But set it optimistically for immediate UI feedback
            this.isRecording = true;
            if (this.recordingStateCallback) {
                this.recordingStateCallback(true);
            }
            console.log('Record command sent successfully');
        } catch (error) {
            console.error('Error in startRecording:', error);
            throw error;
        }
    }

    /**
     * Stop recording
     * @returns {Promise<void>}
     */
    async stopRecording() {
        const packet = this.sdiProtocol.encodeStopCommand();
        await this.sendControlMessage(packet);
        // Don't set isRecording here - wait for camera confirmation via control message
        // But set it optimistically for immediate UI feedback
        this.isRecording = false;
        if (this.recordingStateCallback) {
            this.recordingStateCallback(false);
        }
    }

    /**
     * Get current recording state
     * Note: We track state from incoming control messages and commands sent
     * @returns {Promise<boolean>}
     */
    async getRecordingState() {
        // State is updated from:
        // 1. Commands we send (startRecording/stopRecording)
        // 2. Incoming control messages when camera state changes
        return this.isRecording;
    }

    /**
     * Get camera information from Device Information Service
     * @returns {Promise<object>}
     */
    async getCameraInfo() {
        if (!this.server) {
            throw new Error('Not connected');
        }

        try {
            const deviceInfoService = await this.server.getPrimaryService('0000180a-0000-1000-8000-00805f9b34fb');
            const manufacturerChar = await deviceInfoService.getCharacteristic('00002a29-0000-1000-8000-00805f9b34fb');
            const modelChar = await deviceInfoService.getCharacteristic('00002a24-0000-1000-8000-00805f9b34fb');
            
            const manufacturerData = await manufacturerChar.readValue();
            const modelData = await modelChar.readValue();
            
            const decoder = new TextDecoder('utf-8');
            const manufacturer = decoder.decode(manufacturerData);
            const model = decoder.decode(modelData);
            
            return {
                deviceName: this.device.name || 'Unknown',
                productName: model || 'Unknown',
                manufacturer: manufacturer || 'Blackmagic Design',
                softwareVersion: 'N/A' // Not available via Bluetooth
            };
        } catch (error) {
            console.error('Error getting camera info:', error);
            return {
                deviceName: this.device?.name || 'Unknown',
                productName: 'Unknown',
                manufacturer: 'Blackmagic Design',
                softwareVersion: 'N/A'
            };
        }
    }

    /**
     * Set timecode update callback
     * @param {Function} callback
     */
    setTimecodeCallback(callback) {
        this.timecodeCallback = callback;
    }

    /**
     * Set status update callback
     * @param {Function} callback
     */
    setStatusCallback(callback) {
        this.statusCallback = callback;
    }

    /**
     * Set control message callback
     * @param {Function} callback
     */
    setControlCallback(callback) {
        this.controlCallback = callback;
    }

    /**
     * Set recording state callback
     * @param {Function} callback
     */
    setRecordingStateCallback(callback) {
        this.recordingStateCallback = callback;
    }

    /**
     * Handle disconnection
     */
    handleDisconnection() {
        this.device = null;
        this.server = null;
        this.cameraService = null;
        this.outgoingControl = null;
        this.incomingControl = null;
        this.timecodeCharacteristic = null;
        this.statusCharacteristic = null;
        this.isRecording = false;
    }

    /**
     * Disconnect from camera
     * @returns {Promise<void>}
     */
    async disconnect() {
        if (this.device && this.device.gatt.connected) {
            try {
                this.device.gatt.disconnect();
            } catch (error) {
                console.error('Error disconnecting:', error);
            }
        }
        this.handleDisconnection();
    }

    /**
     * Check if connected
     * @returns {boolean}
     */
    isConnected() {
        return this.device !== null && 
               this.device.gatt !== null && 
               this.device.gatt.connected;
    }

    /**
     * Get device name
     * @returns {string}
     */
    getDeviceName() {
        return this.device?.name || 'Unknown Device';
    }
}

