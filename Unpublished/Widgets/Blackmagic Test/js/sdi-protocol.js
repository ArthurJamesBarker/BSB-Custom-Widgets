// SDI Camera Control Protocol Encoder/Decoder
// Based on Blackmagic SDI Camera Control Protocol specification

class SDIProtocol {
    constructor() {
        // Protocol constants
        this.OPERATION_ASSIGN = 0;
        this.OPERATION_OFFSET = 1;
        
        // Data types
        this.DATA_TYPE_BOOLEAN = 0;
        this.DATA_TYPE_INT8 = 1;
        this.DATA_TYPE_INT16 = 2;
        this.DATA_TYPE_INT32 = 3;
        this.DATA_TYPE_FIXED16 = 128;
        
        // Groups
        this.GROUP_MEDIA = 10;
        
        // Transport modes
        this.TRANSPORT_MODE_PREVIEW = 0;
        this.TRANSPORT_MODE_PLAY = 1;
        this.TRANSPORT_MODE_RECORD = 2;
    }

    /**
     * Encode a transport mode command (Group 10, ID 10.1)
     * @param {number} mode - 0=Preview, 1=Play, 2=Record
     * @param {number} speed - 0=pause/stop, positive=forward, negative=backward
     * @param {number} flags - Bit flags (loop, play all, disk active, etc.)
     * @param {number} destination - Camera destination ID (0-255, 255=all)
     * @returns {ArrayBuffer} Encoded packet
     */
    encodeTransportCommand(mode, speed = 0, flags = 0, destination = 255) {
        // Packet structure per SDI Camera Control Protocol:
        // Header (4 bytes):
        //   Byte 0: destination (uint8)
        //   Byte 1: command length (uint8) - length of command data, NOT including header
        //   Byte 2: command id (uint8) - 0 = "change configuration"
        //   Byte 3: reserved (uint8) - should be 0
        // Command data (for command 0):
        //   Byte 4: category (uint8) - group number (10 for Media)
        //   Byte 5: parameter (uint8) - parameter ID (1 for Transport mode)
        //   Byte 6: data type (uint8) - 1 = signed byte (int8)
        //   Byte 7: operation type (uint8) - 0 = assign
        //   Byte 8-12: data (int8 array) - [mode, speed, flags, slot1, slot2]
        // Padding to 32-bit boundary (4 bytes)
        
        const commandDataLength = 5; // category, parameter, data type, operation, data (5 bytes)
        const dataLength = 5; // mode, speed, flags, slot1, slot2
        const totalCommandDataLength = commandDataLength + dataLength; // 10 bytes
        
        // Calculate padding: round up to nearest 4-byte boundary
        const paddingLength = (4 - (totalCommandDataLength % 4)) % 4;
        const totalLength = 4 + totalCommandDataLength + paddingLength; // header + command data + padding
        
        const buffer = new ArrayBuffer(totalLength);
        const view = new DataView(buffer);
        
        let offset = 0;
        
        // Header (4 bytes)
        view.setUint8(offset++, destination); // destination
        view.setUint8(offset++, totalCommandDataLength); // command length (command data only, not header)
        view.setUint8(offset++, 0); // command id = 0 (change configuration)
        view.setUint8(offset++, 0); // reserved = 0
        
        // Command data
        view.setUint8(offset++, this.GROUP_MEDIA); // category (Group 10 = Media)
        view.setUint8(offset++, 1); // parameter (ID 10.1 = Transport mode)
        view.setUint8(offset++, this.DATA_TYPE_INT8); // data type = 1 (signed byte)
        view.setUint8(offset++, this.OPERATION_ASSIGN); // operation = 0 (assign)
        
        // Data (5 signed bytes)
        view.setInt8(offset++, mode); // [0] = mode
        view.setInt8(offset++, speed); // [1] = speed
        view.setInt8(offset++, flags); // [2] = flags
        view.setInt8(offset++, 0); // [3] = slot 1 storage medium (default)
        view.setInt8(offset++, 0); // [4] = slot 2 storage medium (default)
        
        // Padding to 32-bit boundary
        for (let i = 0; i < paddingLength; i++) {
            view.setUint8(offset++, 0);
        }
        
        return buffer;
    }

    /**
     * Encode a record command
     * @param {number} destination - Camera destination ID (0-255, 255=all)
     * @returns {ArrayBuffer} Encoded packet
     */
    encodeRecordCommand(destination = 255) {
        return this.encodeTransportCommand(
            this.TRANSPORT_MODE_RECORD,
            0, // speed = 0 (pause/stop)
            0, // flags
            destination
        );
    }

    /**
     * Encode a stop/preview command
     * @param {number} destination - Camera destination ID (0-255, 255=all)
     * @returns {ArrayBuffer} Encoded packet
     */
    encodeStopCommand(destination = 255) {
        return this.encodeTransportCommand(
            this.TRANSPORT_MODE_PREVIEW,
            0, // speed = 0 (pause/stop)
            0, // flags
            destination
        );
    }

    /**
     * Decode timecode from 32-bit BCD format
     * @param {DataView} dataView - DataView containing the timecode
     * @param {number} offset - Byte offset in the data
     * @returns {string} Timecode in HH:MM:SS:mm format
     */
    decodeTimecode(dataView, offset = 0) {
        const bcd = dataView.getUint32(offset, false); // big-endian
        
        // Extract BCD digits
        const hours = ((bcd >> 24) & 0xF0) >> 4;
        const hours2 = (bcd >> 24) & 0x0F;
        const minutes = ((bcd >> 16) & 0xF0) >> 4;
        const minutes2 = (bcd >> 16) & 0x0F;
        const seconds = ((bcd >> 8) & 0xF0) >> 4;
        const seconds2 = (bcd >> 8) & 0x0F;
        const frames = ((bcd) & 0xF0) >> 4;
        const frames2 = (bcd) & 0x0F;
        
        const hh = (hours * 10) + hours2;
        const mm = (minutes * 10) + minutes2;
        const ss = (seconds * 10) + seconds2;
        const ff = (frames * 10) + frames2;
        
        return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}:${String(ff).padStart(2, '0')}`;
    }

    /**
     * Decode timecode from Uint8Array
     * @param {Uint8Array} data - Array containing the timecode bytes
     * @returns {string} Timecode in HH:MM:SS:mm format
     */
    decodeTimecodeFromArray(data) {
        if (data.length < 4) {
            return '--:--:--:--';
        }
        
        const bcd = (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3];
        
        const hours = ((bcd >> 24) & 0xF0) >> 4;
        const hours2 = (bcd >> 24) & 0x0F;
        const minutes = ((bcd >> 16) & 0xF0) >> 4;
        const minutes2 = (bcd >> 16) & 0x0F;
        const seconds = ((bcd >> 8) & 0xF0) >> 4;
        const seconds2 = (bcd >> 8) & 0x0F;
        const frames = ((bcd) & 0xF0) >> 4;
        const frames2 = (bcd) & 0x0F;
        
        const hh = (hours * 10) + hours2;
        const mm = (minutes * 10) + minutes2;
        const ss = (seconds * 10) + seconds2;
        const ff = (frames * 10) + frames2;
        
        return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}:${String(ff).padStart(2, '0')}`;
    }

    /**
     * Decode camera status flags
     * @param {number} flags - 8-bit status flags
     * @returns {object} Parsed status object
     */
    decodeCameraStatus(flags) {
        return {
            none: (flags & 0x00) === 0x00,
            powerOn: (flags & 0x01) === 0x01,
            connected: (flags & 0x02) === 0x02,
            paired: (flags & 0x04) === 0x04,
            versionsVerified: (flags & 0x08) === 0x08,
            initialPayloadReceived: (flags & 0x10) === 0x10,
            cameraReady: (flags & 0x20) === 0x20
        };
    }

    /**
     * Parse transport mode from incoming control message
     * @param {DataView} dataView - DataView containing the message
     * @param {number} offset - Byte offset in the data
     * @returns {object} Parsed transport state
     */
    parseTransportState(dataView, offset = 0) {
        // Assuming the response follows similar structure
        // This may need adjustment based on actual camera responses
        if (dataView.byteLength < offset + 1) {
            return { mode: 0, speed: 0, flags: 0 };
        }
        
        const mode = dataView.getInt8(offset);
        const speed = dataView.byteLength > offset + 1 ? dataView.getInt8(offset + 1) : 0;
        const flags = dataView.byteLength > offset + 2 ? dataView.getInt8(offset + 2) : 0;
        
        return { mode, speed, flags };
    }
}

