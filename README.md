<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BS Nexora Educational Platform - Complete App</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }

        .app-container {
            display: flex;
            height: 100vh;
        }

        .sidebar {
            width: 250px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-right: 1px solid rgba(255, 255, 255, 0.2);
            padding: 20px;
            overflow-y: auto;
        }

        .logo {
            text-align: center;
            margin-bottom: 30px;
        }

        .logo h1 {
            color: #667eea;
            font-size: 24px;
            font-weight: bold;
        }

        .logo p {
            color: #666;
            font-size: 12px;
            margin-top: 5px;
        }

        .nav-menu {
            list-style: none;
        }

        .nav-item {
            margin-bottom: 10px;
        }

        .nav-link {
            display: block;
            padding: 12px 15px;
            color: #333;
            text-decoration: none;
            border-radius: 8px;
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .nav-link:hover, .nav-link.active {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            transform: translateX(5px);
        }

        .main-content {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }

        .page {
            display: none;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }

        .page.active {
            display: block;
            animation: fadeIn 0.5s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .page-header {
            margin-bottom: 30px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 15px;
        }

        .page-title {
            color: #667eea;
            font-size: 28px;
            font-weight: bold;
        }

        .page-subtitle {
            color: #666;
            margin-top: 5px;
        }

        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            border-left: 4px solid #667eea;
        }

        .btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
            margin: 5px;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .btn-secondary {
            background: linear-gradient(135deg, #f093fb, #f5576c);
        }

        .btn-success {
            background: linear-gradient(135deg, #4facfe, #00f2fe);
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #333;
        }

        .form-input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s ease;
        }

        .form-input:focus {
            outline: none;
            border-color: #667eea;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }

        .status-active {
            background: #d4edda;
            color: #155724;
        }

        .status-inactive {
            background: #f8d7da;
            color: #721c24;
        }

        .face-id-container {
            text-align: center;
            padding: 40px;
        }

        .face-scanner {
            width: 200px;
            height: 200px;
            border: 3px solid #667eea;
            border-radius: 50%;
            margin: 0 auto 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }

        .video-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .video-card {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }

        .video-card:hover {
            transform: translateY(-5px);
        }

        .video-thumbnail {
            width: 100%;
            height: 150px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 48px;
        }

        .chat-container {
            height: 400px;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            display: flex;
            flex-direction: column;
        }

        .chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #f8f9fa;
        }

        .chat-input-area {
            padding: 15px;
            border-top: 1px solid #e1e5e9;
            display: flex;
            gap: 10px;
        }

        .message {
            margin-bottom: 15px;
            padding: 10px 15px;
            border-radius: 18px;
            max-width: 70%;
        }

        .message.sent {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            margin-left: auto;
        }

        .message.received {
            background: white;
            border: 1px solid #e1e5e9;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }

        .stat-number {
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
        }

        .stat-label {
            color: #666;
            margin-top: 5px;
        }

        .user-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            margin-right: 15px;
        }

        .user-info {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }

        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            border-left: 4px solid #667eea;
            z-index: 1000;
            display: none;
        }

        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
        }

        .modal-content {
            background-color: white;
            margin: 5% auto;
            padding: 30px;
            border-radius: 15px;
            width: 80%;
            max-width: 600px;
            position: relative;
        }

        .close {
            position: absolute;
            right: 15px;
            top: 15px;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            color: #aaa;
        }

        .close:hover {
            color: #000;
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e1e5e9;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            width: 0%;
            transition: width 0.3s ease;
        }

        @media (max-width: 768px) {
            .app-container {
                flex-direction: column;
            }
            
            .sidebar {
                width: 100%;
                height: auto;
            }
            
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Sidebar Navigation -->
        <div class="sidebar">
            <div class="logo">
                <h1>BS NEXORA</h1>
                <p>Educational Platform</p>
            </div>
            
            <ul class="nav-menu">
                <li class="nav-item">
                    <a class="nav-link active" onclick="showPage('dashboard')">🏠 Dashboard</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" onclick="showPage('face-id')">👤 Face ID Login</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" onclick="showPage('accounts')">👥 Account Management</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" onclick="showPage('videos')">🎥 Video Library</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" onclick="showPage('chat')">💬 Chat System</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" onclick="showPage('files')">📁 File Manager</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" onclick="showPage('sync')">🔄 Sync System</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" onclick="showPage('settings')">⚙️ Settings</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" onclick="showPage('about')">ℹ️ About</a>
                </li>
            </ul>
        </div>

        <!-- Main Content Area -->
        <div class="main-content">
            <!-- Dashboard Page -->
            <div id="dashboard" class="page active">
                <div class="page-header">
                    <h1 class="page-title">Dashboard</h1>
                    <p class="page-subtitle">Welcome to BS Nexora Educational Platform</p>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">156</div>
                        <div class="stat-label">Total Students</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">24</div>
                        <div class="stat-label">Active Courses</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">89</div>
                        <div class="stat-label">Video Lessons</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">98%</div>
                        <div class="stat-label">System Uptime</div>
                    </div>
                </div>

                <div class="grid">
                    <div class="card">
                        <h3>Recent Activity</h3>
                        <div class="user-info">
                            <div class="user-avatar">JD</div>
                            <div>
                                <strong>John Doe</strong> uploaded a new video<br>
                                <small>2 minutes ago</small>
                            </div>
                        </div>
                        <div class="user-info">
                            <div class="user-avatar">MS</div>
                            <div>
                                <strong>Mary Smith</strong> completed assignment<br>
                                <small>15 minutes ago</small>
                            </div>
                        </div>
                        <div class="user-info">
                            <div class="user-avatar">RJ</div>
                            <div>
                                <strong>Robert Johnson</strong> joined chat room<br>
                                <small>1 hour ago</small>
                            </div>
                        </div>
                    </div>

                    <div class="card">
                        <h3>System Status</h3>
                        <p><span class="status-badge status-active">Active</span> Face ID System</p>
                        <p><span class="status-badge status-active">Active</span> Account Sync</p>
                        <p><span class="status-badge status-active">Active</span> Video Streaming</p>
                        <p><span class="status-badge status-active">Active</span> Chat System</p>
                        <p><span class="status-badge status-active">Active</span> File Storage</p>
                    </div>
                </div>

                <div class="card">
                    <h3>Quick Actions</h3>
                    <button class="btn" onclick="showPage('accounts')">Create New Account</button>
                    <button class="btn btn-secondary" onclick="showPage('videos')">Upload Video</button>
                    <button class="btn btn-success" onclick="showPage('sync')">Sync All Data</button>
                </div>
            </div>

            <!-- Face ID Page -->
            <div id="face-id" class="page">
                <div class="page-header">
                    <h1 class="page-title">Face ID Authentication</h1>
                    <p class="page-subtitle">Secure biometric login system</p>
                </div>

                <div class="face-id-container">
                    <div class="face-scanner">
                        <span style="font-size: 64px;">👤</span>
                    </div>
                    <h3>Position your face in the scanner</h3>
                    <p>Look directly at the camera for authentication</p>
                    
                    <div style="margin-top: 30px;">
                        <button class="btn" onclick="startFaceAuth()">Start Face Authentication</button>
                        <button class="btn btn-secondary" onclick="registerFace()">Register New Face</button>
                    </div>
                </div>

                <div class="grid">
                    <div class="card">
                        <h3>Face ID Features</h3>
                        <ul style="list-style-type: none; padding-left: 0;">
                            <li>✅ 360° Face Capture</li>
                            <li>✅ Multi-angle Recognition</li>
                            <li>✅ Auto-login (2-3 seconds)</li>
                            <li>✅ Master/CTO Multi-account Access</li>
                            <li>✅ Emergency Fallback System</li>
                            <li>✅ Cross-device Synchronization</li>
                        </ul>
                    </div>

                    <div class="card">
                        <h3>Registered Users</h3>
                        <div class="user-info">
                            <div class="user-avatar">MA</div>
                            <div>
                                <strong>Master Admin</strong><br>
                                <span class="status-badge status-active">Face ID Active</span>
                            </div>
                        </div>
                        <div class="user-info">
                            <div class="user-avatar">CT</div>
                            <div>
                                <strong>CTO Admin</strong><br>
                                <span class="status-badge status-active">Face ID Active</span>
                            </div>
                        </div>
                        <div class="user-info">
                            <div class="user-avatar">SD</div>
                            <div>
                                <strong>Student Demo</strong><br>
                                <span class="status-badge status-inactive">Not Registered</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Account Management Page -->
            <div id="accounts" class="page">
                <div class="page-header">
                    <h1 class="page-title">Account Management</h1>
                    <p class="page-subtitle">Manage users, roles, and permissions</p>
                </div>

                <div class="card">
                    <h3>Create New Account</h3>
                    <div class="grid">
                        <div class="form-group">
                            <label class="form-label">Username</label>
                            <input type="text" class="form-input" placeholder="Enter username">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Full Name</label>
                            <input type="text" class="form-input" placeholder="Enter full name">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Email</label>
                            <input type="email" class="form-input" placeholder="Enter email">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Role</label>
                            <select class="form-input">
                                <option>Student</option>
                                <option>Teacher</option>
                                <option>Master</option>
                                <option>CTO</option>
                                <option>CEO</option>
                            </select>
                        </div>
                    </div>
                    <button class="btn" onclick="createAccount()">Create Account</button>
                    <button class="btn btn-secondary" onclick="bulkCreateAccounts()">Bulk Create</button>
                </div>

                <div class="card">
                    <h3>Existing Accounts</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f8f9fa;">
                                <th style="padding: 12px; text-align: left;">Username</th>
                                <th style="padding: 12px; text-align: left;">Full Name</th>
                                <th style="padding: 12px; text-align: left;">Role</th>
                                <th style="padding: 12px; text-align: left;">Status</th>
                                <th style="padding: 12px; text-align: left;">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td style="padding: 12px;">master_admin</td>
                                <td style="padding: 12px;">Miss Bhavya Thyagaraj Achar</td>
                                <td style="padding: 12px;">Master</td>
                                <td style="padding: 12px;"><span class="status-badge status-active">Active</span></td>
                                <td style="padding: 12px;">
                                    <button class="btn" style="padding: 6px 12px; font-size: 12px;">Edit</button>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 12px;">cto_admin</td>
                                <td style="padding: 12px;">Master Lalith Chandan</td>
                                <td style="padding: 12px;">CTO</td>
                                <td style="padding: 12px;"><span class="status-badge status-active">Active</span></td>
                                <td style="padding: 12px;">
                                    <button class="btn" style="padding: 6px 12px; font-size: 12px;">Edit</button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Video Library Page -->
            <div id="videos" class="page">
                <div class="page-header">
                    <h1 class="page-title">Video Library</h1>
                    <p class="page-subtitle">Educational content and streaming</p>
                </div>

                <div class="card">
                    <h3>Upload New Video</h3>
                    <div class="form-group">
                        <label class="form-label">Video Title</label>
                        <input type="text" class="form-input" placeholder="Enter video title">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Description</label>
                        <textarea class="form-input" rows="3" placeholder="Enter video description"></textarea>
                    </div>
                    <button class="btn" onclick="uploadVideo()">Upload Video</button>
                </div>

                <div class="video-grid">
                    <div class="video-card">
                        <div class="video-thumbnail">▶️</div>
                        <div style="padding: 15px;">
                            <h4>Introduction to Algebra</h4>
                            <p style="color: #666; font-size: 14px;">Basic algebraic concepts</p>
                            <button class="btn" style="padding: 6px 12px; font-size: 12px;">Watch</button>
                        </div>
                    </div>
                    <div class="video-card">
                        <div class="video-thumbnail">▶️</div>
                        <div style="padding: 15px;">
                            <h4>Physics: Motion</h4>
                            <p style="color: #666; font-size: 14px;">Newton's laws of motion</p>
                            <button class="btn" style="padding: 6px 12px; font-size: 12px;">Watch</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Chat System Page -->
            <div id="chat" class="page">
                <div class="page-header">
                    <h1 class="page-title">Chat System</h1>
                    <p class="page-subtitle">Real-time communication</p>
                </div>

                <div class="card">
                    <h3>General Chat</h3>
                    <div class="chat-container">
                        <div class="chat-messages">
                            <div class="message received">
                                <strong>John:</strong> Hey everyone! How's the assignment going?
                            </div>
                            <div class="message sent">
                                <strong>You:</strong> Working on problem 5. It's challenging!
                            </div>
                            <div class="message received">
                                <strong>Mary:</strong> I can help with that approach.
                            </div>
                        </div>
                        <div class="chat-input-area">
                            <input type="text" class="form-input" placeholder="Type message..." style="flex: 1;">
                            <button class="btn" onclick="sendMessage()">Send</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- File Manager Page -->
            <div id="files" class="page">
                <div class="page-header">
                    <h1 class="page-title">File Manager</h1>
                    <p class="page-subtitle">Upload and organize files</p>
                </div>

                <div class="card">
                    <h3>Upload Files</h3>
                    <div class="form-group">
                        <label class="form-label">Select Files</label>
                        <input type="file" class="form-input" multiple>
                    </div>
                    <button class="btn" onclick="uploadFiles()">Upload Files</button>
                </div>

                <div class="card">
                    <h3>Recent Files</h3>
                    <div class="user-info">
                        <div class="user-avatar">📄</div>
                        <div>
                            <strong>Assignment_1.pdf</strong><br>
                            <small>2.3 MB - 2 hours ago</small>
                        </div>
                    </div>
                    <div class="user-info">
                        <div class="user-avatar">📊</div>
                        <div>
                            <strong>Data_Analysis.xlsx</strong><br>
                            <small>1.8 MB - 1 day ago</small>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Sync System Page -->
            <div id="sync" class="page">
                <div class="page-header">
                    <h1 class="page-title">Sync System</h1>
                    <p class="page-subtitle">Data synchronization and backup</p>
                </div>

                <div class="grid">
                    <div class="card">
                        <h3>Sync Status</h3>
                        <p><span class="status-badge status-active">Active</span> Account Sync</p>
                        <p><span class="status-badge status-active">Active</span> File Sync</p>
                        <p><span class="status-badge status-active">Active</span> Video Sync</p>
                        <p><span class="status-badge status-active">Active</span> Chat Sync</p>
                        <button class="btn" onclick="syncAll()">Sync All Data</button>
                    </div>

                    <div class="card">
                        <h3>Recent Sync Activity</h3>
                        <div class="user-info">
                            <div class="user-avatar">🔄</div>
                            <div>
                                <strong>Account Sync</strong><br>
                                <small>Completed 5 minutes ago</small>
                            </div>
                        </div>
                        <div class="user-info">
                            <div class="user-avatar">📁</div>
                            <div>
                                <strong>File Backup</strong><br>
                                <small>Completed 1 hour ago</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Settings Page -->
            <div id="settings" class="page">
                <div class="page-header">
                    <h1 class="page-title">Settings</h1>
                    <p class="page-subtitle">System configuration and preferences</p>
                </div>

                <div class="grid">
                    <div class="card">
                        <h3>Face ID Settings</h3>
                        <div class="form-group">
                            <label class="form-label">
                                <input type="checkbox" checked> Enable Face ID Authentication
                            </label>
                        </div>
                        <div class="form-group">
                            <label class="form-label">
                                <input type="checkbox" checked> Auto-login with Face ID
                            </label>
                        </div>
                        <button class="btn">Save Face ID Settings</button>
                    </div>

                    <div class="card">
                        <h3>System Settings</h3>
                        <div class="form-group">
                            <label class="form-label">
                                <input type="checkbox" checked> Enable Auto-sync
                            </label>
                        </div>
                        <div class="form-group">
                            <label class="form-label">
                                <input type="checkbox" checked> Enable Notifications
                            </label>
                        </div>
                        <button class="btn">Save System Settings</button>
                    </div>
                </div>
            </div>

            <!-- About Page -->
            <div id="about" class="page">
                <div class="page-header">
                    <h1 class="page-title">About BS Nexora</h1>
                    <p class="page-subtitle">Educational Platform Information</p>
                </div>

                <div class="card">
                    <h3>Platform Features</h3>
                    <div class="grid">
                        <div>
                            <h4>🔐 Security Features</h4>
                            <ul>
                                <li>Face ID Authentication</li>
                                <li>Role-based Access Control</li>
                                <li>Secure Account Management</li>
                                <li>Data Encryption</li>
                            </ul>
                        </div>
                        <div>
                            <h4>📚 Educational Tools</h4>
                            <ul>
                                <li>Video Streaming</li>
                                <li>Interactive Chat</li>
                                <li>File Sharing</li>
                                <li>Assignment Management</li>
                            </ul>
                        </div>
                        <div>
                            <h4>🔄 Sync & Backup</h4>
                            <ul>
                                <li>Real-time Synchronization</li>
                                <li>Automatic Backups</li>
                                <li>Cross-device Access</li>
                                <li>Cloud Integration</li>
                            </ul>
                        </div>
                        <div>
                            <h4>👥 User Management</h4>
                            <ul>
                                <li>Multi-role Support</li>
                                <li>Bulk Account Creation</li>
                                <li>User Analytics</li>
                                <li>Permission Management</li>
                            </ul>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <h3>System Information</h3>
                    <p><strong>Version:</strong> 2.0</p>
                    <p><strong>Platform:</strong> BS Nexora Educational</p>
                    <p><strong>Developers:</strong> Miss Bhavya Thyagaraj Achar & Master Lalith Chandan</p>
                    <p><strong>Last Updated:</strong> October 2024</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Notification -->
    <div id="notification" class="notification">
        <span id="notificationText"></span>
    </div>

    <!-- Modal -->
    <div id="modal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <div id="modalContent"></div>
        </div>
    </div>

    <script>
        // Global variables
        let currentUser = {
            username: 'demo_user',
            role: 'student',
            fullName: 'Demo User'
        };

        // Navigation functions
        function showPage(pageId) {
            // Hide all pages
            const pages = document.querySelectorAll('.page');
            pages.forEach(page => page.classList.remove('active'));
            
            // Show selected page
            document.getElementById(pageId).classList.add('active');
            
            // Update navigation
            const navLinks = document.querySelectorAll('.nav-link');
            navLinks.forEach(link => link.classList.remove('active'));
            event.target.classList.add('active');
        }

        // Face ID functions
        function startFaceAuth() {
            showNotification('Starting Face ID authentication...');
            setTimeout(() => {
                showNotification('Face ID authentication successful!');
            }, 2000);
        }

        function registerFace() {
            showNotification('Starting Face ID registration...');
            setTimeout(() => {
                showNotification('Face ID registered successfully!');
            }, 3000);
        }

        // Account management functions
        function createAccount() {
            showNotification('Creating new account...');
            setTimeout(() => {
                showNotification('Account created successfully!');
            }, 1500);
        }

        function bulkCreateAccounts() {
            showModal('Bulk Account Creation', `
                <h3>Bulk Create Accounts</h3>
                <textarea class="form-input" rows="10" placeholder="Enter account details (one per line):
username1,Full Name 1,email1@example.com,role1
username2,Full Name 2,email2@example.com,role2"></textarea>
                <br><br>
                <button class="btn" onclick="processBulkAccounts()">Create Accounts</button>
            `);
        }

        function processBulkAccounts() {
            showNotification('Processing bulk account creation...');
            closeModal();
            setTimeout(() => {
                showNotification('Bulk accounts created successfully!');
            }, 2000);
        }

        // Video functions
        function uploadVideo() {
            showNotification('Uploading video...');
            setTimeout(() => {
                showNotification('Video uploaded successfully!');
            }, 3000);
        }

        // Chat functions
        function sendMessage() {
            const input = document.querySelector('#chat .chat-input-area input');
            const message = input.value.trim();
            if (message) {
                const messagesContainer = document.querySelector('#chat .chat-messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message sent';
                messageDiv.innerHTML = `<strong>You:</strong> ${message}`;
                messagesContainer.appendChild(messageDiv);
                input.value = '';
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }

        // File functions
        function uploadFiles() {
            showNotification('Uploading files...');
            setTimeout(() => {
                showNotification('Files uploaded successfully!');
            }, 2000);
        }

        // Sync functions
        function syncAll() {
            showNotification('Starting comprehensive sync...');
            setTimeout(() => {
                showNotification('All data synchronized successfully!');
            }, 3000);
        }

        // Utility functions
        function showNotification(message) {
            const notification = document.getElementById('notification');
            const notificationText = document.getElementById('notificationText');
            notificationText.textContent = message;
            notification.style.display = 'block';
            
            setTimeout(() => {
                notification.style.display = 'none';
            }, 3000);
        }

        function showModal(title, content) {
            const modal = document.getElementById('modal');
            const modalContent = document.getElementById('modalContent');
            modalContent.innerHTML = `<h2>${title}</h2>${content}`;
            modal.style.display = 'block';
        }

        function closeModal() {
            document.getElementById('modal').style.display = 'none';
        }

        // Initialize app
        document.addEventListener('DOMContentLoaded', function() {
            showNotification('BS Nexora Educational Platform loaded successfully!');
            
            // Add enter key support for chat
            document.addEventListener('keypress', function(e) {
                if (e.key === 'Enter' && e.target.closest('#chat .chat-input-area input')) {
                    sendMessage();
                }
            });
        });

        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('modal');
            if (event.target == modal) {
                closeModal();
            }
        }
    </script>
</body>
</html>
