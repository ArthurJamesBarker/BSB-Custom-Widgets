#!/usr/bin/env python3
"""
Simple HTTP Server for Premiere Pro Timeline Timecode
Serves the timecode data file written by the UXP plugin
"""

import http.server
import socketserver
import json
import os
from pathlib import Path

PORT = 8080

# Find the data file (UXP plugin writes to its data folder)
# The plugin shows the path in the log - it's typically:
# ~/Library/Application Support/Adobe/UXP/PluginsStorage/PPRO/26/Developer/com.ppro.timeline.uxp/PluginData/ppro_timeline_data.json

home = Path.home()
possible_paths = [
    home / "Library" / "Application Support" / "Adobe" / "UXP" / "PluginsStorage" / "PPRO" / "26" / "Developer" / "com.ppro.timeline.uxp" / "PluginData" / "ppro_timeline_data.json",
    home / "Library" / "Application Support" / "Adobe" / "UXP" / "PluginsStorage" / "PPRO" / "25" / "Developer" / "com.ppro.timeline.uxp" / "PluginData" / "ppro_timeline_data.json",
    Path(__file__).parent / "ppro_timeline_data.json",  # Fallback: same directory
]

data_file_path = None
for file_path in possible_paths:
    if file_path.exists():
        data_file_path = file_path
        print(f"✓ Found data file at: {file_path}")
        break

if not data_file_path:
    print("⚠ Data file not found. Plugin will create it when started.")
    print("Looking in:")
    for p in possible_paths:
        print(f"  - {p}")

class TimecodeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/timecode' or self.path == '/':
            # Try to read the data file
            if data_file_path and data_file_path.exists():
                try:
                    with open(data_file_path, 'r', encoding='utf-8') as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    self.wfile.write(data.encode('utf-8'))
                except Exception as e:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    error_data = json.dumps({'error': f'Error reading data file: {str(e)}'})
                    self.wfile.write(error_data.encode('utf-8'))
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_data = json.dumps({'error': 'No data yet. Make sure the plugin is running.'})
                self.wfile.write(error_data.encode('utf-8'))
            return
        
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b'Not found')
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

if __name__ == "__main__":
    # Allow reuse of address to handle TIME_WAIT connections
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), TimecodeHandler) as httpd:
        print(f"\n🚀 Timecode Server running on http://localhost:{PORT}")
        print(f"📡 Web client can connect to: http://localhost:{PORT}/timecode\n")
        
        if data_file_path:
            print(f"📁 Watching file: {data_file_path}\n")
        else:
            print("⚠️  Data file not found. Start the plugin in Premiere Pro first.\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nShutting down server...")
            httpd.shutdown()

