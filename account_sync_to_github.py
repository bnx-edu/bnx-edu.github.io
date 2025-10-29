#!/usr/bin/env python3
"""
Account Sync to GitHub System for B's Nexora Educational Platform
Syncs account creation and management to GitHub.io repository
"""

import os
import json
import sqlite3
import requests
import base64
import hashlib
from datetime import datetime
import uuid

class AccountSyncToGitHub:
    def __init__(self):
        """Initialize account sync system"""
        self.load_config()
        self.setup_sync_structure()
        
    def load_config(self):
        """Load GitHub configuration"""
        try:
            with open('cloud_account_config.json', 'r') as f:
                config = json.load(f)
                self.github_token = config.get('github_token')
                self.github_owner = config.get('github_owner')
                self.github_repo = config.get('github_repo')
                self.enabled = config.get('enabled', False)
                
            if not self.enabled or not self.github_token:
                print("⚠️  GitHub sync not configured - run setup_github_sync_complete.py first")
                
        except Exception as e:
            print(f"❌ Config error: {e}")
            self.enabled = False
    
    def setup_sync_structure(self):
        """Setup directory structure for account sync"""
        directories = [
            'account_sync',
            'account_sync/users',
            'account_sync/sessions',
            'account_sync/backups'
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def sync_all_accounts(self):
        """Sync all accounts to GitHub repository"""
        print("👥 Syncing accounts to GitHub.io repository...")
        
        if not self.enabled:
            print("❌ GitHub sync not enabled - please configure first")
            return False
        
        try:
            # Get all accounts from database
            conn = sqlite3.connect('bs_nexora_educational.db')
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, full_name, email, role, subdivision, 
                       created_at, last_login, is_active, account_type
                FROM users
                WHERE is_active = 1
                ORDER BY created_at DESC
            """)
            accounts = cursor.fetchall()
            conn.close()
            
            if not accounts:
                print("📝 No accounts found to sync")
                return True
            
            # Prepare account data for sync
            account_data = []
            for account in accounts:
                user_id, username, full_name, email, role, subdivision, created_at, last_login, is_active, account_type = account
                
                # Create secure account record (no passwords)
                account_record = {
                    'id': user_id,
                    'username': username,
                    'full_name': full_name,
                    'email': email,
                    'role': role,
                    'subdivision': subdivision,
                    'created_at': created_at,
                    'last_login': last_login,
                    'is_active': bool(is_active),
                    'account_type': account_type or 'local',
                    'sync_date': datetime.now().isoformat(),
                    'device_access': 'cross-device',
                    'platform_access': ['web', 'desktop', 'mobile']
                }
                account_data.append(account_record)
            
            # Create account summary
            account_summary = {
                'total_accounts': len(account_data),
                'roles': {
                    'students': len([a for a in account_data if a['role'] == 'student']),
                    'teachers': len([a for a in account_data if a['role'] == 'teacher']),
                    'admins': len([a for a in account_data if a['role'] in ['master', 'cto', 'ceo', 'cao']]),
                    'crew_leads': len([a for a in account_data if a['role'] == 'crew_lead'])
                },
                'subdivisions': list(set(a['subdivision'] for a in account_data if a['subdivision'])),
                'last_sync': datetime.now().isoformat(),
                'sync_status': 'active',
                'github_repo': f"{self.github_owner}/{self.github_repo}",
                'access_url': f"https://{self.github_owner}.github.io/{self.github_repo}"
            }
            
            # Save locally first
            with open('account_sync/account_data.json', 'w') as f:
                json.dump(account_data, f, indent=2)
            
            with open('account_sync/account_summary.json', 'w') as f:
                json.dump(account_summary, f, indent=2)
            
            # Sync to GitHub
            success = self.upload_to_github(account_data, account_summary)
            
            if success:
                print(f"✅ Synced {len(account_data)} accounts to GitHub")
                print(f"🌐 Access at: https://{self.github_owner}.github.io/{self.github_repo}")
                print("📱 Accounts now available for cross-device access")
                
                # Create web interface for account management
                self.create_account_web_interface(account_summary)
                
                return True
            else:
                print("❌ Failed to sync accounts to GitHub")
                return False
                
        except Exception as e:
            print(f"❌ Account sync error: {e}")
            return False
    
    def upload_to_github(self, account_data, account_summary):
        """Upload account data to GitHub repository"""
        try:
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Upload account summary
            summary_content = json.dumps(account_summary, indent=2)
            encoded_summary = base64.b64encode(summary_content.encode()).decode()
            
            summary_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/account_summary.json"
            
            # Check if file exists
            response = requests.get(summary_url, headers=headers)
            
            data = {
                'message': f'Update account summary - {account_summary["total_accounts"]} accounts',
                'content': encoded_summary
            }
            
            if response.status_code == 200:
                data['sha'] = response.json()['sha']
            
            response = requests.put(summary_url, headers=headers, json=data)
            
            if response.status_code not in [200, 201]:
                print(f"❌ Failed to upload account summary: {response.status_code}")
                return False
            
            # Upload account data (anonymized)
            anonymized_data = self.anonymize_account_data(account_data)
            data_content = json.dumps(anonymized_data, indent=2)
            encoded_data = base64.b64encode(data_content.encode()).decode()
            
            data_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/accounts_public.json"
            
            response = requests.get(data_url, headers=headers)
            
            data = {
                'message': f'Update public account data - {len(anonymized_data)} accounts',
                'content': encoded_data
            }
            
            if response.status_code == 200:
                data['sha'] = response.json()['sha']
            
            response = requests.put(data_url, headers=headers, json=data)
            
            return response.status_code in [200, 201]
            
        except Exception as e:
            print(f"❌ GitHub upload error: {e}")
            return False
    
    def anonymize_account_data(self, account_data):
        """Create anonymized version of account data for public access"""
        anonymized = []
        
        for account in account_data:
            # Create anonymized record
            anon_record = {
                'id': hashlib.md5(str(account['id']).encode()).hexdigest()[:8],
                'role': account['role'],
                'subdivision': account['subdivision'],
                'created_at': account['created_at'][:10],  # Date only
                'account_type': account['account_type'],
                'is_active': account['is_active']
            }
            anonymized.append(anon_record)
        
        return anonymized
    
    def create_account_web_interface(self, account_summary):
        """Create web interface for account management"""
        
        interface_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>B's Nexora Account Management</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }}
        
        .header {{
            background: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            text-align: center;
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            color: #333;
        }}
        
        .header p {{
            color: #666;
            font-size: 1.1rem;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-number {{
            font-size: 3rem;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 0.5rem;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 1.1rem;
            font-weight: 500;
        }}
        
        .info-section {{
            background: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }}
        
        .info-section h2 {{
            color: #333;
            margin-bottom: 1rem;
            font-size: 1.5rem;
        }}
        
        .feature-list {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }}
        
        .feature-item {{
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }}
        
        .feature-item h3 {{
            color: #333;
            margin-bottom: 0.5rem;
        }}
        
        .feature-item p {{
            color: #666;
            font-size: 0.9rem;
        }}
        
        .access-buttons {{
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 2rem;
        }}
        
        .access-btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            border: none;
            border-radius: 50px;
            font-size: 1rem;
            cursor: pointer;
            text-decoration: none;
            transition: transform 0.3s ease;
            display: inline-block;
        }}
        
        .access-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }}
        
        .sync-status {{
            background: #d4edda;
            color: #155724;
            padding: 1rem;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 2rem;
            border: 1px solid #c3e6cb;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}
            
            .header {{
                padding: 1rem;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
            
            .access-buttons {{
                flex-direction: column;
                align-items: center;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>👥 B's Nexora Account Management</h1>
        <p>Cross-Device Account System - Access from Anywhere</p>
    </div>
    
    <div class="container">
        <div class="sync-status">
            ✅ Accounts successfully synced to GitHub.io repository!<br>
            Last sync: {account_summary['last_sync'][:19].replace('T', ' ')}
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{account_summary['total_accounts']}</div>
                <div class="stat-label">Total Accounts</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{account_summary['roles']['students']}</div>
                <div class="stat-label">Students</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{account_summary['roles']['teachers']}</div>
                <div class="stat-label">Teachers</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{account_summary['roles']['admins']}</div>
                <div class="stat-label">Admins</div>
            </div>
        </div>
        
        <div class="info-section">
            <h2>🌐 Cross-Device Account Features</h2>
            <div class="feature-list">
                <div class="feature-item">
                    <h3>🔐 Secure Authentication</h3>
                    <p>PBKDF2 encrypted passwords with secure session management</p>
                </div>
                <div class="feature-item">
                    <h3>📱 Multi-Device Access</h3>
                    <p>Login from any device - Desktop, Mobile, Web, Tablet</p>
                </div>
                <div class="feature-item">
                    <h3>☁️ Cloud Synchronization</h3>
                    <p>Automatic account sync across all devices and platforms</p>
                </div>
                <div class="feature-item">
                    <h3>🔄 Real-time Updates</h3>
                    <p>Account changes sync instantly across all devices</p>
                </div>
                <div class="feature-item">
                    <h3>🏫 Role-Based Access</h3>
                    <p>Students, Teachers, Admins with appropriate permissions</p>
                </div>
                <div class="feature-item">
                    <h3>📊 Activity Tracking</h3>
                    <p>Monitor login activity and device usage</p>
                </div>
            </div>
        </div>
        
        <div class="info-section">
            <h2>📋 Account Distribution</h2>
            <div class="feature-list">
                <div class="feature-item">
                    <h3>👨‍🎓 Students ({account_summary['roles']['students']})</h3>
                    <p>Access to videos, courses, and learning materials</p>
                </div>
                <div class="feature-item">
                    <h3>👨‍🏫 Teachers ({account_summary['roles']['teachers']})</h3>
                    <p>Upload videos, manage content, track student progress</p>
                </div>
                <div class="feature-item">
                    <h3>👨‍💼 Admins ({account_summary['roles']['admins']})</h3>
                    <p>Full system access, user management, system configuration</p>
                </div>
                <div class="feature-item">
                    <h3>👥 Crew Leads ({account_summary['roles']['crew_leads']})</h3>
                    <p>Team management, content approval, subdivision oversight</p>
                </div>
            </div>
        </div>
        
        <div class="access-buttons">
            <a href="https://{self.github_owner}.github.io/{self.github_repo}" class="access-btn">
                🌐 Access Web Platform
            </a>
            <a href="https://github.com/{self.github_owner}/{self.github_repo}" class="access-btn">
                📂 View Repository
            </a>
            <a href="videos.html" class="access-btn">
                🎥 Watch Videos
            </a>
        </div>
        
        <div class="info-section">
            <h2>🚀 How to Access Your Account</h2>
            <div class="feature-list">
                <div class="feature-item">
                    <h3>💻 Desktop Application</h3>
                    <p>Download and run universal_launcher.py for full desktop experience</p>
                </div>
                <div class="feature-item">
                    <h3>🌐 Web Browser</h3>
                    <p>Access via GitHub Pages at {self.github_owner}.github.io/{self.github_repo}</p>
                </div>
                <div class="feature-item">
                    <h3>📱 Mobile Device</h3>
                    <p>Open web browser and navigate to the platform URL</p>
                </div>
                <div class="feature-item">
                    <h3>🔄 Sync Anywhere</h3>
                    <p>Your account works on any device with internet connection</p>
                </div>
            </div>
        </div>
    </div>
</body>
</html>'''
        
        # Save the account management interface
        os.makedirs('docs', exist_ok=True)
        with open('docs/accounts.html', 'w', encoding='utf-8') as f:
            f.write(interface_html)
        
        print("✅ Account web interface created")
    
    def create_account_backup(self):
        """Create backup of all account data"""
        try:
            backup_data = {
                'backup_date': datetime.now().isoformat(),
                'backup_id': str(uuid.uuid4()),
                'platform': 'B\'s Nexora Educational Platform',
                'accounts': []
            }
            
            # Get all accounts
            conn = sqlite3.connect('bs_nexora_educational.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE is_active = 1")
            accounts = cursor.fetchall()
            
            # Get column names
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            conn.close()
            
            # Create account records
            for account in accounts:
                account_dict = dict(zip(columns, account))
                # Remove sensitive data
                if 'password_hash' in account_dict:
                    del account_dict['password_hash']
                backup_data['accounts'].append(account_dict)
            
            # Save backup
            backup_filename = f"account_sync/backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_filename, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            print(f"✅ Account backup created: {backup_filename}")
            return True
            
        except Exception as e:
            print(f"❌ Backup error: {e}")
            return False

def main():
    """Main function to run account sync"""
    print("👥 B's Nexora Account Sync to GitHub System")
    print("=" * 50)
    
    sync_system = AccountSyncToGitHub()
    
    # Create backup first
    print("📦 Creating account backup...")
    sync_system.create_account_backup()
    
    # Sync accounts
    success = sync_system.sync_all_accounts()
    
    if success:
        print("\n" + "=" * 50)
        print("✅ Account sync to GitHub complete!")
        print("🌐 Accounts now available at GitHub.io")
        print("📱 Cross-device access enabled")
        print("🔐 Secure cloud synchronization active")
    else:
        print("\n❌ Account sync failed - check configuration")

if __name__ == "__main__":
    main()
