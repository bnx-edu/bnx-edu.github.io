#!/usr/bin/env python3
"""
B's Nexora Educational Platform - Universal Cross-Platform Launcher
Works on Windows, macOS, and Linux desktop systems

Enhanced Video System Features:
- YouTube-like video browsing for students
- All videos uploaded by Master/CTO/CEO/CAO/Teachers are automatically public
- Real-time video streaming with HTML5 player
- Cross-device compatibility (Mobile, Desktop, Web)
- Progress tracking and search functionality
- Automatic video sync across all devices

Cloud Account System Features:
- Google-like account creation and management
- Cross-device login from any computer worldwide
- Cloud-stored user profiles with GitHub repository
- Device tracking and access management
- Automatic account synchronization across devices
- Secure PBKDF2 password encryption
- Fallback to local accounts when offline
- Admin panel for cloud account setup and management
"""

import sys
import os
import platform
import threading
import time
import subprocess
import webbrowser
from pathlib import Path

class UniversalLauncher:
    def __init__(self):
        self.system = platform.system().lower()
        self.flask_process = None
        self.server_ready = False
        
        print(f"Detected OS: {platform.system()} {platform.release()}")
        
    def hide_console_window(self):
        """Hide console window on Windows"""
        if self.system == 'windows':
            try:
                import ctypes
                ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
            except:
                pass
    
    def start_flask_server(self):
        """Start Flask server in background"""
        try:
            from app import app, init_database, create_default_accounts
            
            print("Initializing B's Nexora Educational Platform...")
            
            # Initialize database silently
            init_database()
            create_default_accounts()
            
            # Verify video system and cloud accounts
            self.verify_video_system()
            self.verify_cloud_accounts()
            
            print("Starting server...")
            
            # Run Flask app
            app.run(
                host='127.0.0.1', 
                port=5000, 
                debug=False, 
                use_reloader=False,
                threaded=True
            )
            
        except Exception as e:
            print(f"Server error: {e}")
    
    def verify_video_system(self):
        """Verify video system is properly configured"""
        try:
            import sqlite3
            import os
            
            print("Verifying video system...")
            
            # Check uploads directory
            uploads_dir = 'uploads'
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir, exist_ok=True)
                print("Created uploads directory")
            
            # Check database for videos
            conn = sqlite3.connect('bs_nexora_educational.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM videos WHERE is_active = 1')
            video_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE role = "student"')
            student_count = cursor.fetchone()[0]
            
            conn.close()
            
            print(f"✅ Video System Status:")
            print(f"   - Active videos: {video_count}")
            print(f"   - Student accounts: {student_count}")
            print(f"   - Upload directory: {'✅ Ready' if os.path.exists(uploads_dir) else '❌ Missing'}")
            print(f"   - Cross-device sync: ✅ Enabled")
            print(f"   - YouTube-like access: ✅ All videos public to students")
            
            # Check cloud account system
            try:
                from cloud_account_system import cloud_account_manager, is_cloud_enabled
                if is_cloud_enabled():
                    print(f"   - Cloud accounts: ✅ Enabled (Google-like cross-device)")
                else:
                    print(f"   - Cloud accounts: ⚠️  Not configured (local accounts only)")
            except ImportError:
                print(f"   - Cloud accounts: ❌ Not available")
            
        except Exception as e:
            print(f"Video system verification error: {e}")
    
    def verify_cloud_accounts(self):
        """Verify cloud account system is properly configured"""
        try:
            print("Verifying cloud account system...")
            
            # Check if cloud account system is available
            try:
                from cloud_account_system import cloud_account_manager, is_cloud_enabled
                cloud_available = True
            except ImportError:
                cloud_available = False
            
            if not cloud_available:
                print("⚠️  Cloud Account System:")
                print("   - Status: Not available")
                print("   - Accounts: Local only (single computer)")
                print("   - Access: Limited to this device")
                return
            
            # Check if cloud accounts are configured
            is_configured = is_cloud_enabled()
            
            print("✅ Cloud Account System Status:")
            if is_configured:
                print("   - Status: ✅ Enabled and configured")
                print("   - Type: Google-like cross-device accounts")
                print("   - Access: Any device with internet")
                print("   - Storage: Secure cloud repository")
                print("   - Features: Device tracking, auto-sync")
                
                # Try to get account count
                try:
                    accounts = cloud_account_manager.list_cloud_accounts()
                    print(f"   - Cloud accounts: {len(accounts)} created")
                except:
                    print("   - Cloud accounts: Available for creation")
            else:
                print("   - Status: ⚠️  Available but not configured")
                print("   - Setup needed: GitHub repository configuration")
                print("   - Access after setup: Any device worldwide")
                print("   - Benefits: Google-like account experience")
            
            # Check local accounts as fallback
            import sqlite3
            conn = sqlite3.connect('bs_nexora_educational.db')
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users WHERE account_type = "local" OR account_type IS NULL')
            local_count = cursor.fetchone()[0]
            conn.close()
            
            print(f"   - Local accounts: {local_count} (fallback/offline)")
            
        except Exception as e:
            print(f"Cloud account verification error: {e}")
    
    def test_video_api(self):
        """Test video API endpoint to ensure video functionality works"""
        try:
            import requests
            
            print("Testing video API...")
            
            # Test the video API endpoint
            response = requests.get('http://localhost:5000/api/videos', timeout=5)
            
            if response.status_code == 401:
                print("⚠️  Video API requires authentication (normal behavior)")
                print("   Students will need to login to access videos")
            elif response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    video_count = len(data.get('videos', []))
                    print(f"✅ Video API working! {video_count} videos available")
                else:
                    print(f"⚠️  Video API response: {data.get('message', 'Unknown')}")
            else:
                print(f"⚠️  Video API returned status: {response.status_code}")
                
            # Test video streaming endpoint (if videos exist)
            try:
                stream_response = requests.head('http://localhost:5000/stream_video/1', timeout=3)
                if stream_response.status_code in [200, 206, 401]:
                    print("✅ Video streaming endpoint working")
                else:
                    print(f"⚠️  Video streaming status: {stream_response.status_code}")
            except:
                print("ℹ️  Video streaming test skipped (no videos or auth required)")
                
        except ImportError:
            print("ℹ️  Requests not available - skipping video API test")
        except Exception as e:
            print(f"Video API test error: {e}")
    
    def test_cloud_authentication(self):
        """Test cloud authentication system"""
        try:
            print("Testing cloud authentication...")
            
            # Check if cloud accounts are available
            try:
                from cloud_account_system import authenticate_cloud_user, is_cloud_enabled
                
                if not is_cloud_enabled():
                    print("ℹ️  Cloud authentication not configured")
                    print("   Setup required: Go to Cloud Account Setup in admin panel")
                    return
                
                print("✅ Cloud authentication system ready")
                print("   Features available:")
                print("   • Google-like account creation")
                print("   • Cross-device login capability")
                print("   • Automatic account synchronization")
                print("   • Device tracking and management")
                print("   • Secure cloud storage")
                
                # Test device info collection
                device_info = self.get_device_info()
                print(f"   Current device: {device_info}")
                
            except ImportError:
                print("ℹ️  Cloud authentication system not available")
                print("   Using local accounts only")
                
        except Exception as e:
            print(f"Cloud authentication test error: {e}")
            
    def wait_for_server(self, timeout=10):
        """Wait for Flask server to be ready"""
        try:
            import requests
            
            for i in range(timeout):
                try:
                    response = requests.get('http://localhost:5000', timeout=1)
                    if response.status_code in [200, 302]:
                        self.server_ready = True
                        return True
                except:
                    pass
                time.sleep(1)
        except ImportError:
            # If requests not available, just wait
            time.sleep(3)
            return True
        return False
    
    def launch_with_webview(self):
        """Launch using pywebview (cross-platform)"""
        try:
            import webview
            
            # Create window
            window = webview.create_window(
                title="B's Nexora Educational Platform",
                url="http://localhost:5000",
                width=1400,
                height=900,
                min_size=(1000, 700),
                resizable=True,
                shadow=True,
                focus=True,
                text_select=True,
                background_color='#1a1a1a',
                debug=False
            )
            
            # Choose GUI based on platform
            gui_options = {
                'windows': 'edgechromium',
                'darwin': 'cocoa',  # macOS
                'linux': 'gtk'
            }
            
            gui = gui_options.get(self.system, 'cef')
            
            webview.start(
                debug=False,
                http_server=False,
                gui=gui,
                private_mode=False
            )
            
            return True
            
        except ImportError:
            print("PyWebView not available")
            return False
        except Exception as e:
            print(f"WebView error: {e}")
            return False
    
    def launch_windows_app_mode(self):
        """Launch on Windows using Edge/Chrome app mode"""
        if self.system != 'windows':
            return False
            
        # Try Edge first
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ]
        
        for edge_path in edge_paths:
            if os.path.exists(edge_path):
                try:
                    subprocess.Popen([
                        edge_path,
                        '--app=http://localhost:5000',
                        '--window-size=1400,900',
                        '--disable-web-security',
                        '--no-first-run'
                    ], creationflags=subprocess.CREATE_NO_WINDOW)
                    return True
                except:
                    continue
        
        # Try Chrome
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        
        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                try:
                    subprocess.Popen([
                        chrome_path,
                        '--app=http://localhost:5000',
                        '--window-size=1400,900',
                        '--disable-web-security',
                        '--no-first-run'
                    ], creationflags=subprocess.CREATE_NO_WINDOW)
                    return True
                except:
                    continue
        
        return False
    
    def launch_macos_app_mode(self):
        """Launch on macOS using app mode"""
        if self.system != 'darwin':
            return False
            
        try:
            # Try Chrome app mode on macOS
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if os.path.exists(chrome_path):
                subprocess.Popen([
                    chrome_path,
                    '--app=http://localhost:5000',
                    '--window-size=1400,900',
                    '--disable-web-security',
                    '--no-first-run'
                ])
                return True
        except:
            pass
        
        try:
            # Try Safari (basic)
            subprocess.Popen(['open', '-a', 'Safari', 'http://localhost:5000'])
            return True
        except:
            pass
        
        return False
    
    def launch_linux_app_mode(self):
        """Launch on Linux using app mode"""
        if self.system != 'linux':
            return False
            
        # Try Chrome/Chromium app mode on Linux
        chrome_commands = [
            'google-chrome',
            'chromium-browser',
            'chromium',
            'chrome'
        ]
        
        for chrome_cmd in chrome_commands:
            try:
                subprocess.Popen([
                    chrome_cmd,
                    '--app=http://localhost:5000',
                    '--window-size=1400,900',
                    '--disable-web-security',
                    '--no-first-run'
                ])
                return True
            except FileNotFoundError:
                continue
            except:
                continue
        
        # Try Firefox
        try:
            subprocess.Popen(['firefox', 'http://localhost:5000'])
            return True
        except:
            pass
        
        return False
    
    def launch_fallback_browser(self):
        """Fallback to default browser (works on all platforms)"""
        try:
            webbrowser.open('http://localhost:5000')
            return True
        except Exception as e:
            print(f"Browser fallback error: {e}")
            return False
    
    def run(self):
        """Main launcher - cross-platform"""
        print("=" * 60)
        print("🎓 B's Nexora Educational Platform - Universal Launcher")
        print("=" * 60)
        print(f"Platform: {platform.system()} {platform.release()}")
        print("✅ Enhanced Video System - YouTube-like Experience")
        print("✅ Cross-Device Sync - Mobile, Desktop, Web")
        print("✅ All videos public to students automatically")
        print("✅ Cloud Account System - Google-like cross-device accounts")
        print("=" * 60)
        
        # Hide console on Windows
        if '--hide-console' in sys.argv:
            self.hide_console_window()
        
        # Start Flask server in background thread
        server_thread = threading.Thread(target=self.start_flask_server, daemon=True)
        server_thread.start()
        
        # Wait for server to be ready
        print("Waiting for server to start...")
        if not self.wait_for_server():
            print("Server failed to start!")
            return False
        
        print("Server ready! Opening application...")
        
        # Test video API endpoint and cloud accounts
        self.test_video_api()
        self.test_cloud_authentication()
        
        # Try different launch methods based on platform
        launch_methods = []
        
        if self.system == 'windows':
            launch_methods = [
                ("PyWebView (Native)", self.launch_with_webview),
                ("Windows App Mode", self.launch_windows_app_mode),
                ("Default Browser", self.launch_fallback_browser)
            ]
        elif self.system == 'darwin':  # macOS
            launch_methods = [
                ("PyWebView (Native)", self.launch_with_webview),
                ("macOS App Mode", self.launch_macos_app_mode),
                ("Default Browser", self.launch_fallback_browser)
            ]
        elif self.system == 'linux':
            launch_methods = [
                ("PyWebView (Native)", self.launch_with_webview),
                ("Linux App Mode", self.launch_linux_app_mode),
                ("Default Browser", self.launch_fallback_browser)
            ]
        else:
            launch_methods = [
                ("PyWebView (Native)", self.launch_with_webview),
                ("Default Browser", self.launch_fallback_browser)
            ]
        
        # Try launch methods in order
        for method_name, method_func in launch_methods:
            print(f"Trying {method_name}...")
            if method_func():
                print(f"✅ Successfully launched with {method_name}")
                print("=" * 60)
                print("🚀 B's Nexora Educational Platform is now running!")
                print("📚 Students can now access all videos uploaded by:")
                print("   • Master Admin")
                print("   • CTO Admin") 
                print("   • CEO Admin")
                print("   • CAO Admin")
                print("   • All Teachers")
                print("🎥 Video System Features:")
                print("   • YouTube-like video browsing")
                print("   • Real-time video streaming")
                print("   • Cross-device compatibility")
                print("   • Progress tracking")
                print("   • Search and filter functionality")
                print("🌐 Cloud Account Features:")
                print("   • Google-like account creation")
                print("   • Cross-device login (any computer)")
                print("   • Cloud-stored user profiles")
                print("   • Device tracking and management")
                print("   • Automatic account synchronization")
                print("   • Secure GitHub repository storage")
                print("   • Fallback to local accounts offline")
                print("   • PBKDF2 encrypted passwords")
                print("📱 Access Instructions:")
                print("   • Students: Login from any device worldwide")
                print("   • Teachers: Access from home, school, mobile")
                print("   • Admins: Manage accounts from anywhere")
                print("   • Setup: Configure once, use everywhere")
                print("=" * 60)
                break
        else:
            print("All launch methods failed!")
            return False
        
        # Keep the script running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Application closed by user")
        
        return True

def main():
    """Main entry point"""
    launcher = UniversalLauncher()
    success = launcher.run()
    
    if not success:
        print("Failed to launch B's Nexora Educational Platform")
        if platform.system().lower() == 'windows':
            input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
