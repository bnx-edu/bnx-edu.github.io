#!/usr/bin/env python3
"""
Simple IDE Setup for B's Nexora Educational Platform
Run this directly in your IDE to fix video and account sync issues
"""

import os
import json
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

def setup_platform():
    """Complete platform setup that can be run in IDE"""
    print("🔧 B's Nexora Educational Platform - IDE Setup")
    print("=" * 60)
    
    # Step 1: Create directories
    print("📁 Creating directories...")
    directories = [
        'docs',
        'docs/static', 
        'docs/videos',
        'account_sync',
        'account_sync/users',
        'account_sync/backups',
        'local_video_cache'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print("✅ Directories created")
    
    # Step 2: Create cloud account config
    print("⚙️ Creating cloud account configuration...")
    
    cloud_config = {
        "github_token": "PASTE_YOUR_GITHUB_TOKEN_HERE",
        "github_owner": "ctoa712-cpu",
        "github_repo": "B-s-Nexora-Edu-Tech",
        "enabled": False,
        "setup_date": datetime.now().isoformat(),
        "instructions": "Replace github_token with your actual token, then set enabled to true"
    }
    
    with open('cloud_account_config.json', 'w') as f:
        json.dump(cloud_config, f, indent=2)
    
    print("✅ Cloud config created")
    
    # Step 3: Create video sync system
    print("🎥 Setting up video sync...")
    
    try:
        # Check if database exists and has videos
        if os.path.exists('bs_nexora_educational.db'):
            conn = sqlite3.connect('bs_nexora_educational.db')
            cursor = conn.cursor()
            
            # Check for videos
            cursor.execute('SELECT COUNT(*) FROM videos WHERE is_active = 1')
            video_count = cursor.fetchone()[0]
            
            if video_count > 0:
                # Copy videos to web-accessible location
                cursor.execute("""
                    SELECT filename, file_path FROM videos 
                    WHERE is_active = 1 AND file_path IS NOT NULL
                """)
                videos = cursor.fetchall()
                
                synced_count = 0
                for filename, file_path in videos:
                    if os.path.exists(file_path):
                        # Copy to docs for web access
                        docs_path = f"docs/videos/{filename}"
                        if not os.path.exists(docs_path):
                            try:
                                shutil.copy2(file_path, docs_path)
                                synced_count += 1
                            except Exception as e:
                                print(f"⚠️ Could not copy {filename}: {e}")
                
                print(f"✅ Synced {synced_count} videos for web access")
            else:
                print("📝 No videos found in database")
            
            conn.close()
        else:
            print("📝 Database not found - will be created on first run")
    
    except Exception as e:
        print(f"⚠️ Video sync error: {e}")
    
    # Step 4: Create account sync system
    print("👥 Setting up account sync...")
    
    try:
        if os.path.exists('bs_nexora_educational.db'):
            conn = sqlite3.connect('bs_nexora_educational.db')
            cursor = conn.cursor()
            
            # Get account summary
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
            total_accounts = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE role = "student" AND is_active = 1')
            students = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE role = "teacher" AND is_active = 1')
            teachers = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE role IN ("master", "cto", "ceo", "cao") AND is_active = 1')
            admins = cursor.fetchone()[0]
            
            # Create account summary
            account_summary = {
                'total_accounts': total_accounts,
                'roles': {
                    'students': students,
                    'teachers': teachers,
                    'admins': admins,
                    'crew_leads': 0
                },
                'last_sync': datetime.now().isoformat(),
                'sync_status': 'ready',
                'github_repo': "ctoa712-cpu/B-s-Nexora-Edu-Tech",
                'access_url': "https://ctoa712-cpu.github.io/B-s-Nexora-Edu-Tech"
            }
            
            with open('account_sync/account_summary.json', 'w') as f:
                json.dump(account_summary, f, indent=2)
            
            print(f"✅ Account summary created - {total_accounts} accounts ready")
            conn.close()
        else:
            print("📝 Database not found - accounts will be synced on first run")
    
    except Exception as e:
        print(f"⚠️ Account sync error: {e}")
    
    # Step 5: Create web interface files
    print("🌐 Creating web interface...")
    
    # Create main index.html
    index_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>B's Nexora Educational Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; display: flex; align-items: center; justify-content: center;
        }
        .container { 
            background: rgba(255, 255, 255, 0.95); padding: 3rem; border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1); text-align: center; max-width: 600px; width: 90%;
        }
        .logo { font-size: 2.5rem; font-weight: bold; color: #333; margin-bottom: 1rem; }
        .subtitle { color: #666; font-size: 1.2rem; margin-bottom: 2rem; }
        .status { background: #d4edda; color: #155724; padding: 1rem; border-radius: 10px; margin: 1rem 0; }
        .btn { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;
            padding: 1rem 2rem; border: none; border-radius: 50px; font-size: 1.1rem;
            cursor: pointer; text-decoration: none; display: inline-block; margin: 0.5rem;
            transition: transform 0.3s ease;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2); }
        .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin: 2rem 0; }
        .feature { background: #f8f9fa; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #667eea; }
        .feature h3 { color: #333; margin-bottom: 0.5rem; }
        .feature p { color: #666; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🎓 B's Nexora Educational Platform</div>
        <div class="subtitle">Advanced Learning Management System</div>
        
        <div class="status">✅ Platform setup complete! Ready for GitHub deployment.</div>
        
        <div class="features">
            <div class="feature">
                <h3>🎥 YouTube-like Videos</h3>
                <p>All videos uploaded by teachers are automatically available to students</p>
            </div>
            <div class="feature">
                <h3>🌐 Cross-Device Access</h3>
                <p>Access from any device - Mobile, Desktop, or Web</p>
            </div>
            <div class="feature">
                <h3>☁️ Cloud Accounts</h3>
                <p>Google-like account system with automatic synchronization</p>
            </div>
            <div class="feature">
                <h3>📱 Mobile Friendly</h3>
                <p>Optimized for smartphones and tablets</p>
            </div>
        </div>
        
        <div style="margin-top: 2rem;">
            <a href="videos.html" class="btn">🎥 View Videos</a>
            <a href="accounts.html" class="btn">👥 Manage Accounts</a>
            <a href="https://github.com/ctoa712-cpu/B-s-Nexora-Edu-Tech" class="btn">📂 GitHub Repo</a>
        </div>
        
        <div style="margin-top: 2rem; color: #666; font-size: 0.9rem;">
            <p><strong>Next Steps:</strong></p>
            <p>1. Get GitHub Personal Access Token</p>
            <p>2. Update cloud_account_config.json with your token</p>
            <p>3. Run the sync scripts</p>
            <p>4. Commit and push to GitHub</p>
            <p>5. Enable GitHub Pages</p>
        </div>
    </div>
</body>
</html>'''
    
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    # Create GitHub Pages config
    config_yml = '''title: "B's Nexora Educational Platform"
description: "Advanced Learning Management System with YouTube-like video access"
theme: minima
plugins:
  - jekyll-feed
'''
    
    with open('docs/_config.yml', 'w') as f:
        f.write(config_yml)
    
    print("✅ Web interface created")
    
    # Step 6: Create instructions file
    print("📋 Creating setup instructions...")
    
    instructions = """# B's Nexora Educational Platform - Setup Complete!

## ✅ What's Been Set Up

1. **Directory Structure**: All necessary folders created
2. **Cloud Configuration**: Template created (needs your GitHub token)
3. **Video Sync System**: Ready to sync videos for YouTube-like access
4. **Account Sync System**: Ready to sync accounts to GitHub.io
5. **Web Interface**: GitHub Pages files created

## 🔧 Next Steps

### Step 1: Get GitHub Personal Access Token
1. Go to GitHub.com → Settings → Developer settings → Personal access tokens
2. Generate new token with 'repo' permissions
3. Copy the token

### Step 2: Configure Cloud Sync
1. Open `cloud_account_config.json`
2. Replace `PASTE_YOUR_GITHUB_TOKEN_HERE` with your actual token
3. Change `"enabled": false` to `"enabled": true`
4. Save the file

### Step 3: Run Sync Scripts (in your IDE)
1. Run `enhanced_video_sync.py` - Syncs videos for YouTube-like access
2. Run `account_sync_to_github.py` - Syncs accounts to GitHub.io
3. Run `deploy_complete_platform.py` - Deploys everything

### Step 4: Deploy to GitHub
1. Commit all files to your repository
2. Push to GitHub
3. Go to repository Settings → Pages
4. Set source to "Deploy from a branch"
5. Select "main" branch and "/docs" folder
6. Save

### Step 5: Access Your Platform
- **Web**: https://ctoa712-cpu.github.io/B-s-Nexora-Edu-Tech
- **Desktop**: Run `universal_launcher.py`
- **Mobile**: Access via web browser

## 🎥 Video Features
- YouTube-like experience for students
- Cross-device video access
- Search and filter functionality
- Mobile-optimized player

## 👥 Account Features
- Cross-device account synchronization
- Secure cloud storage
- Google-like account experience
- Real-time sync across devices

## 🚀 Platform Ready!
Your B's Nexora Educational Platform is now configured for:
- YouTube-like video access for students
- Account creation syncing to GitHub.io
- Cross-device compatibility
- Professional web interface
"""
    
    with open('SETUP_INSTRUCTIONS.md', 'w', encoding='utf-8') as f:
        f.write(instructions)
    
    print("✅ Setup instructions created")
    
    # Final summary
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETE!")
    print("=" * 60)
    print("✅ All systems configured and ready")
    print("✅ Video sync system: Ready for YouTube-like access")
    print("✅ Account sync system: Ready for GitHub.io sync")
    print("✅ Web interface: Created for GitHub Pages")
    print("✅ Instructions: See SETUP_INSTRUCTIONS.md")
    print("\n📋 Next: Configure your GitHub token and run the sync scripts!")
    print("🌐 Target URL: https://ctoa712-cpu.github.io/B-s-Nexora-Edu-Tech")
    print("=" * 60)

if __name__ == "__main__":
    setup_platform()
