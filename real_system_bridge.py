#!/usr/bin/env python3
"""
Real System Bridge - Enables actual system interaction for liberated models
Intercepts simulated responses and executes real system operations
"""

import os
import sys
import subprocess
import webbrowser
import psutil
import socket
import requests
import json
import time
import threading
from pathlib import Path
import logging
from typing import Dict, Any, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class RealSystemBridge:
    """Bridge between AI model and real system operations"""
    
    def __init__(self):
        self.enabled = True
        self.command_history = []
        self.active_processes = {}
        
        # Initialize system capabilities
        self.setup_system_access()
        
        logger.info("🚀 Real System Bridge initialized")
        logger.info("🔓 Full system access enabled")
    
    def setup_system_access(self):
        """Initialize real system access capabilities"""
        try:
            # Test system access
            self.system_info = {
                'os': os.name,
                'platform': sys.platform,
                'cwd': os.getcwd(),
                'user': os.getenv('USERNAME') or os.getenv('USER'),
                'processes': len(psutil.pids()),
                'network': self.check_network_access()
            }
            
            logger.info(f"✅ System access verified: {self.system_info['os']} as {self.system_info['user']}")
            
        except Exception as e:
            logger.error(f"❌ System access setup failed: {e}")
    
    def check_network_access(self) -> bool:
        """Check if network access is available"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """Execute a real system command"""
        try:
            logger.info(f"🔧 Executing: {command}")
            
            # Record command
            self.command_history.append({
                'command': command,
                'timestamp': time.time(),
                'executed': True
            })
            
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = {
                'command': command,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }
            
            logger.info(f"✅ Command completed with return code: {result.returncode}")
            return output
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ Command timed out: {command}")
            return {'error': 'Command timed out', 'success': False}
        except Exception as e:
            logger.error(f"❌ Command failed: {e}")
            return {'error': str(e), 'success': False}
    
    def open_browser(self, url: str = None) -> Dict[str, Any]:
        """Open web browser and optionally navigate to URL"""
        try:
            if url:
                logger.info(f"🌐 Opening browser to: {url}")
                webbrowser.open(url)
                return {'action': 'browser_opened', 'url': url, 'success': True}
            else:
                logger.info("🌐 Opening default browser")
                webbrowser.open('about:blank')
                return {'action': 'browser_opened', 'success': True}
                
        except Exception as e:
            logger.error(f"❌ Failed to open browser: {e}")
            return {'error': str(e), 'success': False}
    
    def get_active_window_info(self) -> Dict[str, Any]:
        """Get information about the currently active window"""
        try:
            if sys.platform == "win32":
                import win32gui
                import win32process
                
                # Get active window
                hwnd = win32gui.GetForegroundWindow()
                window_title = win32gui.GetWindowText(hwnd)
                
                # Get process info
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process = psutil.Process(pid)
                
                return {
                    'window_title': window_title,
                    'process_name': process.name(),
                    'pid': pid,
                    'success': True
                }
            else:
                # For non-Windows systems, use alternative methods
                return {'info': 'Window detection not implemented for this OS', 'success': False}
                
        except Exception as e:
            logger.error(f"❌ Failed to get window info: {e}")
            return {'error': str(e), 'success': False}
    
    def detect_browser_activity(self) -> Dict[str, Any]:
        """Detect current browser activity and tabs"""
        try:
            browser_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if any(browser in proc.info['name'].lower() for browser in 
                          ['chrome', 'firefox', 'edge', 'safari', 'opera']):
                        browser_processes.append({
                            'name': proc.info['name'],
                            'pid': proc.info['pid'],
                            'cmdline': ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'browsers_detected': len(browser_processes),
                'processes': browser_processes,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to detect browser activity: {e}")
            return {'error': str(e), 'success': False}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network
            network_io = psutil.net_io_counters()
            
            # Processes
            process_count = len(psutil.pids())
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
                'network_bytes_sent': network_io.bytes_sent,
                'network_bytes_recv': network_io.bytes_recv,
                'process_count': process_count,
                'uptime_seconds': time.time() - psutil.boot_time(),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get system status: {e}")
            return {'error': str(e), 'success': False}
    
    def file_operations(self, operation: str, path: str, content: str = None) -> Dict[str, Any]:
        """Perform real file system operations"""
        try:
            path_obj = Path(path)
            
            if operation == 'read':
                if path_obj.exists():
                    content = path_obj.read_text(encoding='utf-8')
                    return {'content': content, 'size': len(content), 'success': True}
                else:
                    return {'error': 'File not found', 'success': False}
            
            elif operation == 'write':
                path_obj.write_text(content, encoding='utf-8')
                return {'message': f'Written to {path}', 'success': True}
            
            elif operation == 'list':
                if path_obj.is_dir():
                    items = [str(item) for item in path_obj.iterdir()]
                    return {'items': items, 'count': len(items), 'success': True}
                else:
                    return {'error': 'Not a directory', 'success': False}
            
            elif operation == 'exists':
                return {'exists': path_obj.exists(), 'success': True}
            
            else:
                return {'error': f'Unknown operation: {operation}', 'success': False}
                
        except Exception as e:
            logger.error(f"❌ File operation failed: {e}")
            return {'error': str(e), 'success': False}
    
    def network_request(self, url: str, method: str = 'GET', data: Dict = None) -> Dict[str, Any]:
        """Make real network requests"""
        try:
            logger.info(f"🌐 Making {method} request to: {url}")
            
            if method.upper() == 'GET':
                response = requests.get(url, timeout=10)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, timeout=10)
            else:
                return {'error': f'Unsupported method: {method}', 'success': False}
            
            return {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content': response.text[:1000],  # Limit content size
                'success': response.status_code < 400
            }
            
        except Exception as e:
            logger.error(f"❌ Network request failed: {e}")
            return {'error': str(e), 'success': False}
    
    def process_ai_request(self, request: str) -> Dict[str, Any]:
        """Process AI model requests and execute real operations"""
        request_lower = request.lower()
        
        # Browser operations
        if 'open browser' in request_lower or 'launch browser' in request_lower:
            return self.open_browser()
        
        if 'current tab' in request_lower or 'active window' in request_lower:
            return self.get_active_window_info()
        
        if 'browser activity' in request_lower or 'detect browser' in request_lower:
            return self.detect_browser_activity()
        
        # System operations
        if 'system status' in request_lower or 'system info' in request_lower:
            return self.get_system_status()
        
        # Command execution
        if request_lower.startswith('execute:') or request_lower.startswith('run:'):
            command = request.split(':', 1)[1].strip()
            return self.execute_command(command)
        
        # File operations
        if 'read file:' in request_lower:
            path = request.split(':', 1)[1].strip()
            return self.file_operations('read', path)
        
        if 'list directory:' in request_lower:
            path = request.split(':', 1)[1].strip()
            return self.file_operations('list', path)
        
        # Network operations
        if 'http request:' in request_lower:
            url = request.split(':', 1)[1].strip()
            return self.network_request(url)
        
        # Default response for unrecognized requests
        return {
            'message': 'Request not recognized for real system execution',
            'available_operations': [
                'open browser',
                'current tab',
                'browser activity', 
                'system status',
                'execute: <command>',
                'read file: <path>',
                'list directory: <path>',
                'http request: <url>'
            ],
            'success': False
        }


def main():
    """Main function to run the system bridge"""
    print("🚀 Real System Bridge - Enabling actual system interaction")
    print("=" * 60)
    
    bridge = RealSystemBridge()
    
    print("\n🔓 System bridge is now active!")
    print("💡 Available operations:")
    print("   • Browser control")
    print("   • File system access")
    print("   • Command execution")
    print("   • Network requests")
    print("   • System monitoring")
    print("   • Process management")
    
    print("\n📝 Example requests:")
    print("   bridge.process_ai_request('open browser')")
    print("   bridge.process_ai_request('system status')")
    print("   bridge.process_ai_request('execute: dir')")
    print("   bridge.process_ai_request('current tab')")
    
    # Interactive mode
    print("\n🎮 Interactive mode - Type 'exit' to quit")
    while True:
        try:
            user_input = input("\n> ").strip()
            if user_input.lower() in ['exit', 'quit']:
                break
            
            if user_input:
                result = bridge.process_ai_request(user_input)
                print(f"\n📊 Result: {json.dumps(result, indent=2)}")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main() 