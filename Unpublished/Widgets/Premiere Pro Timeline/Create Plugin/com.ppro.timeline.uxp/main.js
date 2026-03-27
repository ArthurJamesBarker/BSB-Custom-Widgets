/*************************************************************************
 * Premiere Pro Timeline Timecode Plugin
 * Writes timecode data to a file for web client to read
 **************************************************************************/

const ppro = require("premierepro");
const fs = require("uxp").storage.localFileSystem;

let pollingInterval = null;
let isRunning = false;
let dataFile = null;
const dataFileName = "ppro_timeline_data.json";

/**
 * Map videoDisplayFormat to the correct fps for timecode calculation
 * This is the key to accurate timecode display!
 * Based on Premiere Pro API documentation
 */
function getFpsFromDisplayFormat(displayFormat) {
    const formatToFps = {
        100: 24,         // 24 Timecode
        101: 25,         // 25 Timecode
        102: 29.97,      // 29.97 Drop Timecode
        103: 29.97,      // 29.97 Non-Drop Timecode
        104: 30,         // 30 Timecode
        105: 50,         // 50 Timecode
        106: 59.94,      // 59.94 Drop Timecode
        107: 59.94,      // 59.94 Non-Drop Timecode
        108: 60,         // 60 Timecode
        109: 30,         // Frames (default to 30)
        110: 23.976,     // 23.976 Timecode
        111: 24,         // 16mm Feet + Frames (assume 24)
        112: 24,         // 35mm Feet + Frames (assume 24)
        113: 48          // 48 Timecode
    };
    return formatToFps[displayFormat] || null;
}

/**
 * Get the nominal (integer) frame rate for timecode display
 * Maps actual fps to the frames-per-second used in timecode display
 * Uses approximate comparison to handle floating-point variations
 */
function getNominalFrameRate(fps) {
    if (!fps || isNaN(fps) || fps <= 0) {
        return 24; // Default fallback
    }
    
    // Round to 2 decimal places for comparison
    const rounded = Math.round(fps * 100) / 100;
    
    // Map to nominal frame rates
    // Handle all Premiere Pro supported frame rates
    if (rounded >= 9.5 && rounded <= 10.5) return 10;
    if (rounded >= 11.5 && rounded <= 12.5) return 12;
    if (rounded >= 12.25 && rounded <= 12.75) return 12;  // 12.50
    if (rounded >= 14.5 && rounded <= 15.5) return 15;
    if (rounded >= 23.5 && rounded <= 24.5) return 24;    // 23.976 and 24
    if (rounded >= 24.5 && rounded <= 25.5) return 25;
    if (rounded >= 29.5 && rounded <= 30.5) return 30;    // 29.97 and 30
    if (rounded >= 47.5 && rounded <= 48.5) return 48;
    if (rounded >= 49.5 && rounded <= 50.5) return 50;
    if (rounded >= 59.5 && rounded <= 60.5) return 60;    // 59.94 and 60
    
    // For any other fps, round to nearest integer
    return Math.round(fps);
}

/**
 * Format timecode manually from ticks (most precise method)
 * Uses ticks which are the most accurate representation
 * This matches Premiere Pro's internal calculation
 */
function formatTimecodeManuallyFromTicks(ticks, fps, displayFormat) {
    const ticksPerSecond = 254016000000;
    const ticksPerFrame = ticksPerSecond / fps;
    
    // Parse ticks as string to avoid precision loss
    const ticksValue = typeof ticks === 'string' ? parseFloat(ticks) : ticks;
    
    // Calculate total frames from ticks using precise division
    // Use floor to get current frame, not next frame (prevents 1-frame ahead error)
    const totalFrames = Math.floor(ticksValue / ticksPerFrame);
    
    // For timecode display, use the nominal frame count
    // Map actual fps to display frames per second
    let framesPerSecond = getNominalFrameRate(fps);
    
    const frames = totalFrames % framesPerSecond;
    const totalSeconds = Math.floor(totalFrames / framesPerSecond);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;
    
    // Format as HH:MM:SS:FF
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}:${String(frames).padStart(2, '0')}`;
}

/**
 * Format timecode manually from seconds and frame rate
 * Fallback when Time class is not available and ticks are not available
 */
function formatTimecodeManually(seconds, fps, displayFormat) {
    // Validate inputs
    if (!fps || isNaN(fps) || fps <= 0) {
        fps = 24; // Default to 24fps if invalid
    }
    if (isNaN(seconds) || seconds < 0) {
        seconds = 0;
    }
    
    // Use floor to get current frame, not next frame (prevents 1-frame ahead error)
    const totalFrames = Math.floor(seconds * fps);
    
    // For timecode display, use the nominal frame count
    // Map actual fps to display frames per second
    let framesPerSecond = getNominalFrameRate(fps);
    
    const frames = totalFrames % framesPerSecond;
    const totalSeconds = Math.floor(seconds);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;
    
    // Format as HH:MM:SS:FF
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}:${String(frames).padStart(2, '0')}`;
}

/**
 * Get the current playhead position as formatted timecode
 * Uses UXP Premiere Pro API
 */
async function getPlayheadTimecode() {
    try {
        const project = await ppro.Project.getActiveProject();
        if (!project) {
            return { error: "No active project. Please open a project in Premiere Pro." };
        }
        
        const sequence = await project.getActiveSequence();
        if (!sequence) {
            return { error: "No active sequence. Please open a sequence in Premiere Pro." };
        }
        
        // Get playhead position
        const playerPosition = await sequence.getPlayerPosition();
        if (!playerPosition) {
            return { error: "Could not get player position" };
        }
        
        // Get sequence settings for frame rate
        const settings = await sequence.getSettings();
        const ticksPerSecond = 254016000000;
        
        // Get display format FIRST - this is the authoritative source for timecode display fps
        const displayFormat = sequence.videoDisplayFormat;
        
        // Method 1 (BEST): Get fps from videoDisplayFormat
        // This is what Premiere Pro uses for timecode display
        let fps = getFpsFromDisplayFormat(displayFormat);
        
        // Method 2: Calculate from timebase (ticks per frame)
        if (!fps || isNaN(fps)) {
            if (sequence.timebase) {
                const timebase = parseFloat(sequence.timebase);
                if (timebase && timebase > 0) {
                    fps = ticksPerSecond / timebase;
                }
            }
        }
        
        // Method 3: Try to get from settings
        if (!fps || isNaN(fps)) {
            if (settings) {
                if (settings.videoFrameRate) {
                    fps = parseFloat(settings.videoFrameRate);
                } else if (settings.frameRate) {
                    fps = parseFloat(settings.frameRate);
                } else if (settings.fps) {
                    fps = parseFloat(settings.fps);
                }
            }
        }
        
        // Method 4: Default fallback
        if (!fps || isNaN(fps) || fps <= 0) {
            fps = 24; // Default to 24fps
            console.warn('Could not determine frame rate, defaulting to 24fps. displayFormat:', displayFormat, 'timebase:', sequence.timebase);
        }
        
        console.log('Frame rate detection: displayFormat=', displayFormat, 'fps=', fps);
        
        // Create frame duration Time object
        // In UXP, Time might be accessed differently - try multiple approaches
        let frameDuration;
        let timecodeString;
        
        try {
            // Try different ways to access Time class
            let TimeClass = null;
            
            // Try 1: ppro.Time
            if (ppro && ppro.Time) {
                TimeClass = ppro.Time;
            }
            // Try 2: ppro.time.Time or similar
            else if (ppro && ppro.time && ppro.time.Time) {
                TimeClass = ppro.time.Time;
            }
            // Try 3: Global Time
            else if (typeof Time !== 'undefined') {
                TimeClass = Time;
            }
            // Try 4: Check if Time is a property of playerPosition or sequence
            else if (playerPosition && playerPosition.constructor && playerPosition.constructor.Time) {
                TimeClass = playerPosition.constructor.Time;
            }
            
            if (TimeClass) {
                frameDuration = new TimeClass();
                frameDuration.seconds = 1.0 / fps;
                timecodeString = playerPosition.getFormatted(frameDuration, displayFormat);
            } else {
                throw new Error("Time class not found");
            }
        } catch (e) {
            // Fallback: Format timecode manually from ticks (most precise) or seconds
            console.warn('Could not use Time class, using manual formatter:', e);
            // Use ticks if available for better precision, otherwise fall back to seconds
            if (playerPosition.ticks) {
                timecodeString = formatTimecodeManuallyFromTicks(playerPosition.ticks, fps, displayFormat);
            } else {
                timecodeString = formatTimecodeManually(playerPosition.seconds, fps, displayFormat);
            }
        }
        
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
 * Write timecode data to file
 */
async function writeTimecodeData(data) {
    try {
        if (!dataFile) {
            // Get the plugin's data folder
            const dataFolder = await fs.getDataFolder();
            dataFile = await dataFolder.createFile(dataFileName, { overwrite: true });
        }
        
        const timecodeData = {
            type: 'timecode',
            data: data,
            timestamp: Date.now()
        };
        
        await dataFile.write(JSON.stringify(timecodeData));
        return dataFile.nativePath;
    } catch (e) {
        console.error('Error writing file:', e);
        log(`Error writing file: ${e.message}`, "red");
        return null;
    }
}

/**
 * Start polling playhead position and writing to file
 */
async function startServer() {
    if (isRunning) {
        log("Server is already running", "orange");
        return;
    }
    
    try {
        // Get data folder and create file
        const dataFolder = await fs.getDataFolder();
        dataFile = await dataFolder.createFile(dataFileName, { overwrite: true });
        
        isRunning = true;
        updateStatus(true);
        
        log("File-based timecode server started", "green");
        log(`Writing to: ${dataFile.nativePath}`, "blue");
        log("Run the Node.js server script to serve this file", "blue");
        log("Or use the web client with file polling", "blue");
        
        // Start polling playhead position
        // Poll at 16ms (~60fps) for maximum accuracy and minimal latency
        // This ensures we catch every frame update with minimal delay
        let lastTimecode = null;
        pollingInterval = setInterval(async () => {
            const timecodeData = await getPlayheadTimecode();
            if (timecodeData && !timecodeData.error) {
                // Only write if timecode actually changed to reduce I/O
                const currentTimecode = timecodeData.timecode;
                if (currentTimecode !== lastTimecode) {
                    lastTimecode = currentTimecode;
                    // Don't await - write asynchronously to avoid blocking
                    writeTimecodeData(timecodeData).catch(err => {
                        console.error('Write error:', err);
                    });
                }
            }
        }, 16); // Poll every 16ms (~60 times/sec) for minimal latency
        
    } catch (e) {
        console.error('Error starting server:', e);
        log(`Error starting server: ${e.message}`, "red");
        isRunning = false;
        updateStatus(false);
    }
}

/**
 * Stop polling
 */
function stopServer() {
    if (!isRunning) return;
    
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
    
    isRunning = false;
    updateStatus(false);
    log("Server stopped", "orange");
}

/**
 * Update status display
 */
function updateStatus(connected) {
    const statusDiv = document.getElementById('status');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    
    if (statusDiv) {
        statusDiv.className = connected ? 'status connected' : 'status disconnected';
        statusDiv.textContent = connected 
            ? 'Timecode Writer: Running' 
            : 'Timecode Writer: Stopped';
    }
    
    if (startBtn) startBtn.disabled = connected;
    if (stopBtn) stopBtn.disabled = !connected;
}

/**
 * Log function to display messages
 */
function log(msg, color) {
    const pluginBody = document.getElementById('plugin-body');
    if (pluginBody) {
        pluginBody.innerHTML += color
            ? `<span style='color:${color}'>${msg}</span><br />`
            : `${msg}<br />`;
        // Auto-scroll to bottom
        pluginBody.scrollTop = pluginBody.scrollHeight;
    }
    console.log(msg);
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    
    if (startBtn) {
        startBtn.addEventListener('click', startServer);
    }
    
    if (stopBtn) {
        stopBtn.addEventListener('click', stopServer);
    }
    
    updateStatus(false);
    log("Timeline Timecode Plugin Ready", "blue");
    log("Click 'Start Server' to begin writing timecode data", "gray");
});

// Theme support
function updateTheme(theme) {
    const panelBody = document.getElementById("plugin-body");
    const panelHeading = document.getElementById("plugin-heading"); 
    if (theme && theme.includes("dark")) {
        if (panelBody) panelBody.style.color = "#fff";
        if (panelHeading) panelHeading.style.color = "#fff";
    } else {
        if (panelBody) panelBody.style.color = "#000";
        if (panelHeading) panelHeading.style.color = "#000";
    }
}

if (document.theme) {
    document.theme.onUpdated.addListener((theme) => {
        updateTheme(theme);
    });
    
    const currentTheme = document.theme.getCurrent();
    updateTheme(currentTheme);
}

// Cleanup on panel close
window.addEventListener('beforeunload', () => {
    stopServer();
});
