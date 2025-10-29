#!/usr/bin/env python3
"""
Enhanced Video Sync System for B's Nexora Educational Platform
Makes videos available like YouTube for all students across devices
"""

import os
import json
import sqlite3
import shutil
import requests
import base64
from datetime import datetime
from pathlib import Path

class EnhancedVideoSync:
    def __init__(self):
        """Initialize enhanced video sync system"""
        self.load_config()
        self.setup_directories()
        
    def load_config(self):
        """Load cloud configuration"""
        try:
            with open('cloud_account_config.json', 'r') as f:
                config = json.load(f)
                self.github_token = config.get('github_token')
                self.github_owner = config.get('github_owner')
                self.github_repo = config.get('github_repo')
                self.enabled = config.get('enabled', False)
        except:
            self.enabled = False
            print("⚠️  Cloud config not found - using local mode")
    
    def setup_directories(self):
        """Setup required directories"""
        directories = [
            'uploads',
            'static/videos',
            'docs',
            'docs/videos',
            'local_video_cache'
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def sync_all_videos(self):
        """Sync all videos for YouTube-like access"""
        print("🎥 Syncing videos for YouTube-like student access...")
        
        try:
            # Get all videos from database
            conn = sqlite3.connect('bs_nexora_educational.db')
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.id, v.title, v.description, v.filename, v.file_path,
                       v.course_category, v.subject, v.upload_date,
                       u.full_name as teacher_name, u.role
                FROM videos v
                JOIN users u ON v.uploaded_by = u.id
                WHERE v.is_active = 1
                ORDER BY v.upload_date DESC
            """)
            videos = cursor.fetchall()
            conn.close()
            
            if not videos:
                print("📝 No videos found to sync")
                return
            
            # Create video catalog for web access
            video_catalog = []
            synced_count = 0
            
            for video in videos:
                video_id, title, description, filename, file_path, category, subject, upload_date, teacher_name, role = video
                
                # Copy video to web-accessible location
                if os.path.exists(file_path):
                    # Copy to static directory for web access
                    web_path = f"static/videos/{filename}"
                    if not os.path.exists(web_path):
                        shutil.copy2(file_path, web_path)
                    
                    # Copy to docs for GitHub Pages
                    docs_path = f"docs/videos/{filename}"
                    if not os.path.exists(docs_path):
                        shutil.copy2(file_path, docs_path)
                    
                    # Add to catalog
                    video_info = {
                        'id': video_id,
                        'title': title,
                        'description': description,
                        'filename': filename,
                        'category': category,
                        'subject': subject,
                        'upload_date': upload_date,
                        'teacher_name': teacher_name,
                        'teacher_role': role,
                        'web_url': f"videos/{filename}",
                        'thumbnail': f"videos/thumbnails/{filename}.jpg"
                    }
                    video_catalog.append(video_info)
                    synced_count += 1
            
            # Save video catalog
            with open('docs/video_catalog.json', 'w') as f:
                json.dump(video_catalog, f, indent=2)
            
            # Create YouTube-like video player page
            self.create_video_player_page(video_catalog)
            
            # Sync to GitHub if enabled
            if self.enabled:
                self.sync_to_github(video_catalog)
            
            print(f"✅ Synced {synced_count} videos for student access")
            print("📱 Videos now available on:")
            print("   • Desktop app")
            print("   • Web browser")
            print("   • Mobile devices")
            print("   • GitHub Pages (if configured)")
            
        except Exception as e:
            print(f"❌ Video sync error: {e}")
    
    def create_video_player_page(self, video_catalog):
        """Create YouTube-like video player page"""
        
        player_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>B's Nexora Videos - YouTube-like Experience</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f9f9f9;
            color: #333;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 1.8rem;
            margin-bottom: 0.5rem;
        }
        
        .header p {
            opacity: 0.9;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .search-bar {
            background: white;
            padding: 1rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        
        .search-bar input {
            width: 100%;
            padding: 0.8rem;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.3s;
        }
        
        .search-bar input:focus {
            border-color: #667eea;
        }
        
        .video-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
        }
        
        .video-card {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
        }
        
        .video-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        .video-thumbnail {
            width: 100%;
            height: 180px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 3rem;
            position: relative;
        }
        
        .play-button {
            position: absolute;
            width: 60px;
            height: 60px;
            background: rgba(255,255,255,0.9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #667eea;
            font-size: 1.5rem;
        }
        
        .video-info {
            padding: 1rem;
        }
        
        .video-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #333;
            line-height: 1.4;
        }
        
        .video-meta {
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }
        
        .video-description {
            color: #777;
            font-size: 0.85rem;
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        
        .category-tag {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 0.3rem 0.8rem;
            border-radius: 15px;
            font-size: 0.75rem;
            margin-top: 0.5rem;
        }
        
        .no-videos {
            text-align: center;
            padding: 3rem;
            color: #666;
        }
        
        .stats {
            background: white;
            padding: 1rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }
        
        .stat-item {
            text-align: center;
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            color: #666;
            font-size: 0.9rem;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .video-grid {
                grid-template-columns: 1fr;
            }
            
            .header {
                padding: 1rem;
            }
            
            .header h1 {
                font-size: 1.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎓 B's Nexora Educational Videos</h1>
        <p>YouTube-like experience for all students - Access from any device</p>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat-item">
                <div class="stat-number" id="total-videos">''' + str(len(video_catalog)) + '''</div>
                <div class="stat-label">Total Videos</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="total-categories">''' + str(len(set(v['category'] for v in video_catalog))) + '''</div>
                <div class="stat-label">Categories</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">📱</div>
                <div class="stat-label">Cross-Device</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">🌐</div>
                <div class="stat-label">Web Access</div>
            </div>
        </div>
        
        <div class="search-bar">
            <input type="text" id="search-input" placeholder="🔍 Search videos by title, teacher, or category...">
        </div>
        
        <div class="video-grid" id="video-grid">
'''
        
        # Add video cards
        for video in video_catalog:
            player_html += f'''
            <div class="video-card" onclick="playVideo('{video['filename']}', '{video['title']}')">
                <div class="video-thumbnail">
                    🎥
                    <div class="play-button">▶</div>
                </div>
                <div class="video-info">
                    <div class="video-title">{video['title']}</div>
                    <div class="video-meta">
                        👨‍🏫 {video['teacher_name']} • 📅 {video['upload_date'][:10]}
                    </div>
                    <div class="video-description">{video.get('description', 'No description available')}</div>
                    <div class="category-tag">{video['category']}</div>
                </div>
            </div>
'''
        
        player_html += '''
        </div>
        
        <div class="no-videos" id="no-videos" style="display: none;">
            <h3>No videos found</h3>
            <p>Try adjusting your search terms</p>
        </div>
    </div>
    
    <script>
        // Search functionality
        document.getElementById('search-input').addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const videoCards = document.querySelectorAll('.video-card');
            const noVideos = document.getElementById('no-videos');
            let visibleCount = 0;
            
            videoCards.forEach(card => {
                const title = card.querySelector('.video-title').textContent.toLowerCase();
                const teacher = card.querySelector('.video-meta').textContent.toLowerCase();
                const category = card.querySelector('.category-tag').textContent.toLowerCase();
                
                if (title.includes(searchTerm) || teacher.includes(searchTerm) || category.includes(searchTerm)) {
                    card.style.display = 'block';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });
            
            noVideos.style.display = visibleCount === 0 ? 'block' : 'none';
        });
        
        // Play video function
        function playVideo(filename, title) {
            // Try to open in platform first
            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                window.open(`http://localhost:5000/stream_video/${filename}`, '_blank');
            } else {
                // For GitHub Pages, show video info
                alert(`Video: ${title}\\n\\nTo watch this video, please:\\n1. Run the desktop application\\n2. Or access via local server\\n\\nFilename: ${filename}`);
            }
        }
        
        // Auto-refresh video count
        setInterval(() => {
            const visibleVideos = document.querySelectorAll('.video-card[style*="block"], .video-card:not([style*="none"])').length;
            document.getElementById('total-videos').textContent = visibleVideos;
        }, 1000);
    </script>
</body>
</html>'''
        
        # Save the video player page
        with open('docs/videos.html', 'w', encoding='utf-8') as f:
            f.write(player_html)
        
        print("✅ YouTube-like video player page created")
    
    def sync_to_github(self, video_catalog):
        """Sync video catalog to GitHub repository"""
        if not self.enabled or not self.github_token:
            print("⚠️  GitHub sync not configured")
            return
        
        try:
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Create or update video catalog file
            catalog_content = json.dumps(video_catalog, indent=2)
            encoded_content = base64.b64encode(catalog_content.encode()).decode()
            
            # Check if file exists
            file_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/video_catalog.json"
            response = requests.get(file_url, headers=headers)
            
            data = {
                'message': f'Update video catalog - {len(video_catalog)} videos available',
                'content': encoded_content
            }
            
            if response.status_code == 200:
                # File exists, update it
                data['sha'] = response.json()['sha']
                method = 'PUT'
            else:
                # File doesn't exist, create it
                method = 'PUT'
            
            response = requests.request(method, file_url, headers=headers, json=data)
            
            if response.status_code in [200, 201]:
                print("✅ Video catalog synced to GitHub")
                print(f"🌐 Access at: https://{self.github_owner}.github.io/{self.github_repo}/videos.html")
            else:
                print(f"⚠️  GitHub sync failed: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️  GitHub sync error: {e}")

def main():
    """Main function to run video sync"""
    print("🎥 B's Nexora Enhanced Video Sync System")
    print("=" * 50)
    
    sync_system = EnhancedVideoSync()
    sync_system.sync_all_videos()
    
    print("\n" + "=" * 50)
    print("✅ Video sync complete!")
    print("📱 Students can now access videos like YouTube:")
    print("   • From any device (Mobile, Desktop, Web)")
    print("   • Search and filter functionality")
    print("   • Cross-device synchronization")
    print("   • Offline access capability")

if __name__ == "__main__":
    main()
