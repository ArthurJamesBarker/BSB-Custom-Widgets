// Busy Bar HTTP API Client
// Communicates with Busy Bar device to display status images

class BusyBarClient {
    constructor(baseUrl, appId) {
        this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
        this.appId = appId;
        this.imagesUploaded = new Set();
        this.uploadFailures = new Set(); // Track failed uploads to prevent infinite retries
        this.isReachable = null; // null = unknown, true = reachable, false = unreachable
        this.maxUploadRetries = 2; // Maximum retry attempts per image
        this.uploadRetryCount = new Map(); // Track retry count per image
        this.connectionCheckPromise = null; // Track ongoing connection check
        this.uploadInProgress = false; // Lock to prevent concurrent uploads
        this.uploadQueue = []; // Queue for upload requests
    }

    /**
     * Upload an image file to the Busy Bar device
     * @param {File|Blob|ArrayBuffer} imageData - Image file data
     * @param {string} filename - Filename to use on the device
     * @returns {Promise<void>}
     */
    async uploadImage(imageData, filename) {
        // Wait for any in-progress upload to complete
        while (this.uploadInProgress) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        // Set upload lock
        this.uploadInProgress = true;

        try {
            // Validate filename matches API pattern: ^[a-zA-Z0-9._-]+$
            const filenamePattern = /^[a-zA-Z0-9._-]+$/;
            if (!filenamePattern.test(filename)) {
                throw new Error(`Invalid filename format: ${filename}. Must match pattern: ^[a-zA-Z0-9._-]+$`);
            }
            
            const url = `${this.baseUrl}/api/assets/upload?app_id=${encodeURIComponent(this.appId)}&file=${encodeURIComponent(filename)}`;
            console.log(`Uploading image to: ${url}`);
            
            // Convert imageData to Blob if needed
            let blob;
            if (imageData instanceof Blob || imageData instanceof File) {
                blob = imageData;
            } else if (imageData instanceof ArrayBuffer) {
                blob = new Blob([imageData]);
            } else {
                throw new Error('Invalid image data type');
            }

            // According to API spec, Content-Type must be application/octet-stream
            // Python examples use: requests.post(url, data=data, headers={"Content-Type": "application/octet-stream"})
            console.log(`Uploading ${filename}: ${blob.size} bytes`);

            // Use AbortController for better browser compatibility (instead of AbortSignal.timeout)
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout for upload

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/octet-stream',
                },
                body: blob, // Matches Python's data= parameter
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                let errorText = '';
                try {
                    errorText = await response.text();
                } catch (e) {
                    errorText = `No error details available (${response.status})`;
                }
                console.error(`Upload failed response: ${response.status}`, errorText);
                // Mark as unreachable if we get a network error
                if (response.status === 0 || response.status >= 500) {
                    this.isReachable = false;
                }
                throw new Error(`Failed to upload image: ${response.status} - ${errorText}`);
            }

            // According to API spec, response should be JSON with SuccessResponse schema: {"result": "OK"}
            const responseContentType = response.headers.get('content-type') || '';
            
            if (responseContentType.includes('application/json')) {
                try {
                    const result = await response.json();
                    console.log(`Upload response for ${filename}:`, result);
                    
                    // Verify response matches SuccessResponse schema: {"result": "OK"}
                    if (result && typeof result === 'object') {
                        if (result.result === 'OK') {
                            // Success - this is the expected response format
                            console.log(`✅ Upload confirmed: ${filename}`);
                        } else if (result.error) {
                            // API returned an error
                            throw new Error(`Upload API returned error: ${result.error}`);
                        } else if (result.result && result.result !== 'OK') {
                            // Unexpected result value
                            console.warn(`Upload response has unexpected result value: ${result.result}`);
                        }
                    }
                } catch (jsonError) {
                    // If we already threw an API error, re-throw it
                    if (jsonError.message && jsonError.message.includes('Upload API returned error')) {
                        throw jsonError;
                    }
                    // JSON parse error - response might not be JSON after all
                    console.warn(`Expected JSON response for ${filename}, but parsing failed. Status is OK.`);
                }
            } else {
                // Not JSON, read as text (but don't log if empty)
                const text = await response.text();
                if (text) {
                    console.warn(`Upload response for ${filename} is not JSON (expected application/json):`, text);
                }
            }

            // Mark as uploaded if we got a successful response (200-299)
            // response.ok already ensures this, but being explicit
            this.imagesUploaded.add(filename);
            // Mark as reachable on successful upload
            this.isReachable = true;
            console.log(`✅ Image uploaded successfully: ${filename} (${blob.size} bytes)`);
            return true;
        } catch (error) {
            console.error(`Error uploading image ${filename}:`, error);
            // Mark as unreachable on network errors
            if (error.name === 'TypeError' || error.name === 'TimeoutError' || error.name === 'AbortError') {
                this.isReachable = false;
            }
            throw error;
        } finally {
            // Release upload lock
            this.uploadInProgress = false;
        }
    }

    /**
     * Upload an image from a URL or file path
     * @param {string} imageUrl - URL or path to the image file
     * @param {string} filename - Filename to use on the device
     * @returns {Promise<void>}
     */
    async uploadImageFromUrl(imageUrl, filename) {
        try {
            // Convert relative path to absolute URL using current window location
            let absoluteUrl;
            if (imageUrl.startsWith('http://') || imageUrl.startsWith('https://')) {
                absoluteUrl = imageUrl;
            } else if (imageUrl.startsWith('./') || imageUrl.startsWith('../') || !imageUrl.startsWith('/')) {
                // Relative path - use current window location
                const baseUrl = window.location.origin + window.location.pathname.substring(0, window.location.pathname.lastIndexOf('/'));
                absoluteUrl = baseUrl + '/' + imageUrl.replace(/^\.\//, '');
            } else {
                // Absolute path from root
                absoluteUrl = window.location.origin + imageUrl;
            }
            
            // Handle spaces in URL
            const encodedUrl = absoluteUrl.replace(/ /g, '%20');
            console.log(`Fetching image from: ${encodedUrl}`);
            
            const response = await fetch(encodedUrl);
            if (!response.ok) {
                throw new Error(`Failed to fetch image from ${encodedUrl}: ${response.status} ${response.statusText}`);
            }
            
            const blob = await response.blob();
            console.log(`Image fetched: ${filename}, size: ${blob.size} bytes, type: ${blob.type || 'unknown'}`);
            
            if (blob.size === 0) {
                throw new Error(`Image file is empty: ${filename}`);
            }
            
            // Validate it's actually an image
            if (blob.type && !blob.type.startsWith('image/')) {
                console.warn(`Warning: Fetched file ${filename} has type ${blob.type}, expected image/*`);
            }
            
            return await this.uploadImage(blob, filename);
        } catch (error) {
            console.error(`Error uploading image from URL ${imageUrl}:`, error);
            throw error;
        }
    }

    /**
     * Display an image on the Busy Bar screen
     * @param {string} imagePath - Path/filename of the uploaded image
     * @param {number} x - X position (default: 0)
     * @param {number} y - Y position (default: 0)
     * @param {string} display - Display side: "front" or "back" (default: "front")
     * @returns {Promise<void>}
     */
    async displayImage(imagePath, x = 0, y = 0, display = 'front') {
        try {
            const url = `${this.baseUrl}/api/display/draw`;
            
            const payload = {
                app_id: this.appId,
                elements: [
                    {
                        id: 'status',
                        type: 'image',
                        path: imagePath,
                        x: x,
                        y: y,
                        display: display
                    }
                ]
            };

            console.log(`Displaying image on Busy Bar: ${imagePath}`);
            console.log('Display payload:', JSON.stringify(payload, null, 2));

            // Use AbortController for better browser compatibility
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout for display

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`Display failed response: ${response.status}`, errorText);
                // Mark as unreachable if we get a network error
                if (response.status === 0 || response.status >= 500) {
                    this.isReachable = false;
                }
                throw new Error(`Failed to display image: ${response.status} - ${errorText}`);
            }

            // According to API spec, response should be JSON with SuccessResponse schema: {"result": "OK"}
            const result = await response.json();
            console.log(`Display response:`, result);
            
            // Verify response matches SuccessResponse schema
            if (result && typeof result === 'object' && result.result === 'OK') {
                console.log(`✅ Image displayed successfully on Busy Bar: ${imagePath}`);
                // Mark as reachable on successful display
                this.isReachable = true;
                return true;
            } else if (result && result.error) {
                throw new Error(`Display API returned error: ${result.error}`);
            } else {
                console.warn(`Display response has unexpected format:`, result);
                // Still mark as reachable since we got a 200 response
                this.isReachable = true;
                return true;
            }
        } catch (error) {
            console.error(`Error displaying image ${imagePath}:`, error);
            // Mark as unreachable on network errors
            if (error.name === 'TypeError' || error.name === 'TimeoutError' || error.name === 'AbortError') {
                this.isReachable = false;
            }
            throw error;
        }
    }

    /**
     * Clear the display
     * @returns {Promise<void>}
     */
    async clearDisplay() {
        try {
            const url = `${this.baseUrl}/api/display?app_id=${encodeURIComponent(this.appId)}`;
            
            const response = await fetch(url, {
                method: 'DELETE',
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Failed to clear display: ${response.status} - ${errorText}`);
            }

            console.log('Busy Bar display cleared');
            return true;
        } catch (error) {
            console.error('Error clearing display:', error);
            throw error;
        }
    }

    /**
     * Check if Busy Bar is reachable
     * @returns {Promise<boolean>}
     */
    async checkConnection() {
        // If a connection check is already in progress, return that promise
        if (this.connectionCheckPromise) {
            return this.connectionCheckPromise;
        }

        // Create new connection check promise
        this.connectionCheckPromise = (async () => {
            try {
                const url = `${this.baseUrl}/api/version`;
                
                // Use AbortController for better browser compatibility
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 3000);
                
                const response = await fetch(url, {
                    method: 'GET',
                    signal: controller.signal,
                });
                
                clearTimeout(timeoutId);
                
                this.isReachable = response.ok;
                if (response.ok) {
                    // Reset upload failures if connection is restored
                    this.uploadFailures.clear();
                    this.uploadRetryCount.clear();
                }
                return response.ok;
            } catch (error) {
                console.error('Busy Bar connection check failed:', error);
                this.isReachable = false;
                return false;
            } finally {
                // Clear the promise so next check can run
                this.connectionCheckPromise = null;
            }
        })();

        return this.connectionCheckPromise;
    }

    /**
     * Wait for connection check to complete if in progress, or verify connection
     * @returns {Promise<boolean>}
     */
    async ensureConnectionChecked() {
        if (this.isReachable === null) {
            // Connection state is unknown, check it now
            return await this.checkConnection();
        }
        // If a check is in progress, wait for it
        if (this.connectionCheckPromise) {
            return await this.connectionCheckPromise;
        }
        // Already checked, return current state
        return this.isReachable === true;
    }

    /**
     * Reset connection state and upload tracking
     * Useful when reconnecting or retrying after a failure
     */
    resetConnectionState() {
        this.isReachable = null;
        this.uploadFailures.clear();
        this.uploadRetryCount.clear();
        this.connectionCheckPromise = null;
        // Optionally clear uploaded images to force re-upload
        // this.imagesUploaded.clear();
    }

    /**
     * Get list of successfully uploaded images
     * @returns {Array<string>}
     */
    getUploadedImages() {
        return Array.from(this.imagesUploaded);
    }

    /**
     * Check if a specific image has been uploaded
     * @param {string} filename - Filename to check
     * @returns {boolean}
     */
    isImageUploaded(filename) {
        return this.imagesUploaded.has(filename);
    }

    /**
     * Upload both status images (recording and standby)
     * @returns {Promise<void>}
     */
    async uploadStatusImages() {
        const images = [
            { url: './Images/Recording.png', filename: 'recording.png' },
            { url: './Images/standby.png', filename: 'standby.png' }
        ];

        console.log(`Starting upload of ${images.length} status images...`);
        const results = [];
        
        for (const img of images) {
            try {
                console.log(`Uploading ${img.filename}...`);
                const result = await this.uploadImageFromUrl(img.url, img.filename);
                results.push({ filename: img.filename, success: true });
                console.log(`✅ Successfully uploaded ${img.filename}`);
            } catch (error) {
                console.error(`❌ Failed to upload ${img.filename}:`, error);
                results.push({ 
                    filename: img.filename, 
                    success: false, 
                    error: error.message || error.toString() 
                });
                // Don't throw here - continue with other images
            }
        }

        const successCount = results.filter(r => r.success).length;
        const failedCount = results.filter(r => !r.success).length;
        
        console.log(`Status images upload completed: ${successCount}/${images.length} successful`);
        
        if (failedCount > 0) {
            const failedFiles = results.filter(r => !r.success).map(r => `${r.filename} (${r.error})`).join(', ');
            console.warn(`Failed uploads: ${failedFiles}`);
        }
        
        if (successCount === 0) {
            throw new Error(`Failed to upload any images. Errors: ${results.map(r => r.error || 'Unknown').join('; ')}`);
        }
        
        if (successCount < images.length) {
            console.warn(`Only ${successCount}/${images.length} images uploaded successfully. Some features may not work.`);
        }
        
        return results;
    }

    /**
     * Show recording status on Busy Bar
     * @param {boolean} isRecording - True if recording, false if not
     * @returns {Promise<void>}
     */
    async showRecordingStatus(isRecording) {
        try {
            const imagePath = isRecording ? 'recording.png' : 'standby.png';
            
            // Wait for connection check if state is unknown (null)
            // This prevents race conditions where uploads start before connectivity is verified
            if (this.isReachable === null) {
                const isConnected = await this.ensureConnectionChecked();
                if (!isConnected) {
                    console.debug(`Skipping Busy Bar update - device is unreachable (connection check failed)`);
                    return;
                }
            }
            
            // If Busy Bar is known to be unreachable, skip silently
            if (this.isReachable === false) {
                console.debug(`Skipping Busy Bar update - device is unreachable`);
                return;
            }
            
            // Verify image was uploaded
            if (!this.imagesUploaded.has(imagePath)) {
                // Check if we've already failed to upload this image too many times
                const retryCount = this.uploadRetryCount.get(imagePath) || 0;
                if (retryCount >= this.maxUploadRetries || this.uploadFailures.has(imagePath)) {
                    console.debug(`Skipping upload of ${imagePath} - previous uploads failed (${retryCount} attempts)`);
                    // Don't throw - just skip the update silently
                    return;
                }
                
                // Double-check reachability before attempting upload
                if (this.isReachable === false) {
                    console.debug(`Skipping upload of ${imagePath} - Busy Bar is unreachable`);
                    return;
                }
                
                console.log(`Attempting to show ${imagePath} on Busy Bar`);
                console.warn(`Image ${imagePath} not in uploaded set. Attempting to upload now...`);
                
                try {
                    const url = isRecording ? './Images/Recording.png' : './Images/standby.png';
                    await this.uploadImageFromUrl(url, imagePath);
                    // Success - reset retry count and remove from failures
                    this.uploadRetryCount.delete(imagePath);
                    this.uploadFailures.delete(imagePath);
                    console.log(`Successfully uploaded ${imagePath}`);
                } catch (uploadError) {
                    // Check if error indicates Busy Bar is unreachable - do this FIRST
                    if (uploadError.name === 'TimeoutError' || 
                        uploadError.name === 'AbortError' ||
                        (uploadError.name === 'TypeError' && uploadError.message.includes('fetch'))) {
                        this.isReachable = false;
                        console.debug(`Marking Busy Bar as unreachable due to ${uploadError.name}`);
                    }
                    
                    // Track the failure
                    const newRetryCount = retryCount + 1;
                    this.uploadRetryCount.set(imagePath, newRetryCount);
                    
                    if (newRetryCount >= this.maxUploadRetries) {
                        this.uploadFailures.add(imagePath);
                        console.warn(`Failed to upload ${imagePath} after ${newRetryCount} attempts. Giving up.`);
                    } else {
                        console.warn(`Failed to upload ${imagePath} on demand (attempt ${newRetryCount}/${this.maxUploadRetries}):`, uploadError.message || uploadError.name);
                    }
                    
                    // Don't throw - just skip the update
                    return;
                }
            } else {
                // Image is already uploaded, just try to display it
                console.log(`Attempting to show ${imagePath} on Busy Bar`);
            }
            
            // Try to display the image, but handle errors gracefully
            // Skip if Busy Bar is unreachable
            if (this.isReachable === false) {
                console.debug(`Skipping Busy Bar display - device is unreachable`);
                return;
            }
            
            try {
                await this.displayImage(imagePath);
            } catch (displayError) {
                // Check if error indicates Busy Bar is unreachable
                if (displayError.name === 'TimeoutError' || 
                    displayError.name === 'AbortError' ||
                    (displayError.name === 'TypeError' && displayError.message.includes('fetch'))) {
                    this.isReachable = false;
                    console.debug(`Marking Busy Bar as unreachable due to ${displayError.name}`);
                }
                console.debug('Error displaying image on Busy Bar:', displayError.message || displayError.name);
                // Don't throw - just log the error
            }
        } catch (error) {
            console.error('Error showing recording status on Busy Bar:', error);
            // Don't re-throw - handle gracefully to prevent infinite retry loops
        }
    }
}

