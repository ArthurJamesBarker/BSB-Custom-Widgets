#!/usr/bin/env python3

"""
Simple server control script for Blackmagic Camera Control
Usage: python3 server.py [start|stop|restart|status]
"""

import sys
import subprocess
import signal
import time
import http.client
import os
from pathlib import Path

PORT = 8000
BASE_DIR = Path(__file__).parent.parent  # Go up one level to project root

def check_server_running():
    """Check if server is running on the port"""
    try:
        conn = http.client.HTTPConnection('localhost', PORT, timeout=1)
        conn.request('HEAD', '/')
        conn.getresponse()
        conn.close()
        return True
    except:
        return False

def start_server():
    """Start the web server"""
    if check_server_running():
        print(f"Server is already running on port {PORT}")
        print(f"Open http://localhost:{PORT} in your browser")
        return
    
    print(f"Starting web server on port {PORT}...")
    print(f"Access the application at: http://localhost:{PORT}")
    print("\nPress Ctrl+C to stop the server\n")
    
    os.chdir(BASE_DIR)
    try:
        subprocess.run(['python3', '-m', 'http.server', str(PORT)])
    except KeyboardInterrupt:
        print("\nStopping server...")
    except Exception as e:
        print(f"Failed to start server: {e}")
        sys.exit(1)

def stop_server():
    """Stop the web server"""
    print(f"Stopping web server on port {PORT}...")
    
    try:
        # First try to find process using lsof (more reliable)
        result = subprocess.run(
            ['lsof', '-ti', f':{PORT}'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            # Found process(es) using the port
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    try:
                        subprocess.run(['kill', pid], check=True)
                        print(f"Killed process {pid}")
                    except subprocess.CalledProcessError:
                        print(f"Failed to kill process {pid}")
            print("Server stopped successfully")
        else:
            # Fallback to pkill method
            result = subprocess.run(
                ['pkill', '-f', f'python3 -m http.server {PORT}'],
                capture_output=True
            )
            if result.returncode == 0:
                print("Server stopped successfully")
            else:
                print(f"No server found running on port {PORT}")
    except Exception as e:
        print(f"Error stopping server: {e}")

def restart_server():
    """Restart the web server"""
    stop_server()
    time.sleep(1)
    print("Restarting server...")
    start_server()

def show_status():
    """Show server status"""
    if check_server_running():
        print(f"✓ Server is running on port {PORT}")
        print(f"Open http://localhost:{PORT} in your browser")
    else:
        print(f"✗ Server is not running on port {PORT}")

def main():
    command = sys.argv[1] if len(sys.argv) > 1 else 'start'
    
    if command == 'start':
        start_server()
    elif command == 'stop':
        stop_server()
    elif command == 'restart':
        restart_server()
    elif command == 'status':
        show_status()
    else:
        print("Usage: python3 server.py [start|stop|restart|status]")
        print("\nCommands:")
        print("  start   - Start the web server")
        print("  stop    - Stop the web server")
        print("  restart - Restart the web server")
        print("  status  - Check if server is running")
        sys.exit(1)

if __name__ == '__main__':
    main()

