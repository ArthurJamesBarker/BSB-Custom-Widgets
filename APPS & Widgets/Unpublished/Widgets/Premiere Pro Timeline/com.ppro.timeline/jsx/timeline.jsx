/**
 * Premiere Pro Timeline Timecode ExtendScript
 * Reads playhead position and formats it as timecode
 */

(function() {
    'use strict';
    
    /**
     * Get the current playhead position as formatted timecode
     * @returns {Object} Object with timecode string and sequence info, or null if no active sequence
     */
    function getPlayheadTimecode() {
        try {
            if (!app.project || !app.project.activeSequence) {
                return null;
            }
            
            var sequence = app.project.activeSequence;
            var playerPosition = sequence.getPlayerPosition();
            
            if (!playerPosition) {
                return null;
            }
            
            // Get frame rate from sequence settings
            var settings = sequence.getSettings();
            var frameRate = sequence.timebase; // This is in ticks per frame
            var displayFormat = sequence.videoDisplayFormat;
            
            // Calculate frame rate in frames per second
            // timebase is ticks per frame, and there are 254016000000 ticks per second
            var ticksPerSecond = 254016000000;
            var fps = ticksPerSecond / parseFloat(frameRate);
            
            // Create a Time object for one frame duration
            var frameDuration = new Time();
            frameDuration.seconds = 1.0 / fps;
            
            // Format the timecode
            var timecodeString = playerPosition.getFormatted(frameDuration, displayFormat);
            
            return {
                timecode: timecodeString,
                seconds: playerPosition.seconds,
                ticks: playerPosition.ticks,
                sequenceName: sequence.name,
                frameRate: fps,
                displayFormat: displayFormat
            };
        } catch (e) {
            return {
                error: e.toString()
            };
        }
    }
    
    /**
     * Get sequence information
     * @returns {Object} Sequence info or null
     */
    function getSequenceInfo() {
        try {
            if (!app.project || !app.project.activeSequence) {
                return null;
            }
            
            var sequence = app.project.activeSequence;
            var settings = sequence.getSettings();
            
            return {
                name: sequence.name,
                start: sequence.zeroPoint,
                end: sequence.end,
                timebase: sequence.timebase,
                videoDisplayFormat: sequence.videoDisplayFormat,
                frameWidth: sequence.frameSizeHorizontal,
                frameHeight: sequence.frameSizeVertical
            };
        } catch (e) {
            return {
                error: e.toString()
            };
        }
    }
    
    // Export functions to be called from CEP panel
    // In ExtendScript, we use evalScript to communicate with CEP
    // These functions will be called via evalScript from the CEP panel
    
})();

