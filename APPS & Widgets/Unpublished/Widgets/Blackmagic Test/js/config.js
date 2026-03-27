// Camera Configuration
// Single source of truth for camera and Busy Bar settings

const CAMERA_CONFIG = {
    // Bluetooth LE Configuration
    bluetooth: {
        // Blackmagic Camera Service UUID
        serviceUUID: '291d567a-6d75-11e6-8b77-86f30ca893d3',
        
        // Bluetooth Characteristics UUIDs
        outgoingControlUUID: '5dd3465f-1aee-4299-8493-d2eca2f8e1bb',
        incomingControlUUID: 'b864e140-76a0-416a-bf30-5876504537d9',
        timecodeUUID: '6d8f2110-86f1-41bf-9afb-451d87e976c8',
        statusUUID: '7fe8691d-95dc-4fc5-8abd-ca74339b51b9'
    },
    
    // Busy Bar Configuration
    busyBar: {
        enabled: true,  // Set to true to enable Busy Bar integration
        connections: {
            usb: 'http://10.0.4.20',
            wifi: 'http://10.46.30.146'
        },
        defaultConnection: 'usb',
        appId: 'blackmagic-camera-control'  // Application ID for Busy Bar API
    }
};

