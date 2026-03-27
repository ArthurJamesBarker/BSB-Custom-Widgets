/**
 * Simple Node.js HTTP Server
 * Serves the timecode data file written by the UXP plugin
 * 
 * Run this with: node server.js
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

const port = 8080;

// Find the data file (UXP plugin writes to its data folder)
// The plugin shows the path in the log - it's typically:
// /Users/.../Library/Application Support/Adobe/UXP/PluginsStorage/PPRO/25/Developer/com.ppro.timeline.uxp/PluginData/ppro_timeline_data.json
// or /Users/.../Library/Application Support/Adobe/UXP/PluginsStorage/PPRO/26/Developer/com.ppro.timeline.uxp/PluginData/ppro_timeline_data.json

const possiblePaths = [
    // Try PPRO 26 first (newer versions)
    path.join(process.env.HOME, 'Library', 'Application Support', 'Adobe', 'UXP', 'PluginsStorage', 'PPRO', '26', 'Developer', 'com.ppro.timeline.uxp', 'PluginData', 'ppro_timeline_data.json'),
    // Try PPRO 25
    path.join(process.env.HOME, 'Library', 'Application Support', 'Adobe', 'UXP', 'PluginsStorage', 'PPRO', '25', 'Developer', 'com.ppro.timeline.uxp', 'PluginData', 'ppro_timeline_data.json'),
    // Try PHSP (Photoshop) paths just in case
    path.join(process.env.HOME, 'Library', 'Application Support', 'Adobe', 'UXP', 'PluginsStorage', 'PHSP', '25', 'com.ppro.timeline.uxp', 'ppro_timeline_data.json'),
    path.join(process.env.APPDATA || '', 'Adobe', 'UXP', 'PluginsStorage', 'PPRO', '26', 'Developer', 'com.ppro.timeline.uxp', 'PluginData', 'ppro_timeline_data.json'),
    path.join(process.env.APPDATA || '', 'Adobe', 'UXP', 'PluginsStorage', 'PPRO', '25', 'Developer', 'com.ppro.timeline.uxp', 'PluginData', 'ppro_timeline_data.json'),
    path.join(__dirname, 'ppro_timeline_data.json') // Fallback: same directory
];

let dataFilePath = null;

// Find the data file
for (const filePath of possiblePaths) {
    if (fs.existsSync(filePath)) {
        dataFilePath = filePath;
        console.log(`Found data file at: ${filePath}`);
        break;
    }
}

if (!dataFilePath) {
    console.warn('Data file not found. Plugin will create it when started.');
    console.log('Looking in:', possiblePaths);
}

const server = http.createServer((req, res) => {
    // CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }
    
    // Serve timecode endpoint
    if (req.url === '/timecode' || req.url === '/') {
        // Try to read the data file
        if (dataFilePath && fs.existsSync(dataFilePath)) {
            try {
                const data = fs.readFileSync(dataFilePath, 'utf8');
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(data);
            } catch (e) {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Error reading data file' }));
            }
        } else {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'No data yet. Make sure the plugin is running.' }));
        }
        return;
    }
    
    res.writeHead(404);
    res.end('Not found');
});

server.listen(port, 'localhost', () => {
    console.log(`\n🚀 Timecode Server running on http://localhost:${port}`);
    console.log(`📡 Web client can connect to: http://localhost:${port}/timecode\n`);
    
    if (dataFilePath) {
        console.log(`📁 Watching file: ${dataFilePath}\n`);
        
        // Watch for file changes
        fs.watchFile(dataFilePath, { interval: 100 }, (curr, prev) => {
            console.log('Timecode data updated');
        });
    } else {
        console.log('⚠️  Data file not found. Start the plugin in Premiere Pro first.\n');
    }
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\n\nShutting down server...');
    server.close();
    process.exit(0);
});

