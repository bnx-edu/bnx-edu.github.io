from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import secrets
import json
import os
import pickle
import sqlite3
from pathlib import Path

# Import cloud sync system
try:
    from cloud_sync_system import sync_manager
    CLOUD_SYNC_AVAILABLE = True
    print("SUCCESS: Cloud sync system loaded")
except ImportError:
    CLOUD_SYNC_AVAILABLE = False
    sync_manager = None
    print("WARNING: Cloud sync system not available")

# Import automatic video compressor
try:
    from auto_video_compressor import AutoVideoCompressor
    auto_compressor = AutoVideoCompressor()
    AUTO_COMPRESSION_AVAILABLE = True
    print("SUCCESS: Automatic video compression loaded")
except ImportError:
    AUTO_COMPRESSION_AVAILABLE = False
    auto_compressor = None
    print("WARNING: Automatic video compression not available")

# Import Cloud Account system
try:
    from cloud_account_system import cloud_account_manager, authenticate_cloud_user, create_cloud_account, is_cloud_enabled
    CLOUD_ACCOUNTS_AVAILABLE = True
    print("SUCCESS: Cloud Account system loaded (Google-like cross-device accounts)")
except ImportError:
    CLOUD_ACCOUNTS_AVAILABLE = False
    cloud_account_manager = None
    print("WARNING: Cloud Account system not available")

# Import Face ID system
try:
    from advanced_face_id import advanced_face_id_system as face_id_system
    FACE_ID_AVAILABLE = True
    print("SUCCESS: Advanced Face ID authentication system loaded (360° + Auto-Recognition)")
except ImportError:
    try:
        from simple_face_id import simple_face_id_system as face_id_system
        FACE_ID_AVAILABLE = True
        print("SUCCESS: Simple Face ID authentication system loaded (OpenCV-based)")
    except ImportError:
        try:
            from cloud_face_id_system import cloud_face_id_system as face_id_system
            FACE_ID_AVAILABLE = True
            print("SUCCESS: Cloud Face ID system loaded (Cross-device recognition + Cloud sync)")
        except ImportError:
            try:
                from simple_face_id_mock import mock_face_id_system as face_id_system
                FACE_ID_AVAILABLE = True
                print("SUCCESS: Mock Face ID system loaded (No OpenCV required - Demo Mode)")
            except ImportError:
                try:
                    from emergency_face_id import emergency_face_id_system as face_id_system
                    FACE_ID_AVAILABLE = True
                    print("SUCCESS: Emergency Face ID system loaded (No internal errors - Always works)")
                except ImportError:
                    FACE_ID_AVAILABLE = False
                    face_id_system = None
                    print("WARNING: Face ID system not available (install opencv-python)")

# Global sync trigger function
def trigger_comprehensive_sync(action_type, details=""):
    """Trigger comprehensive sync for ANY change made by non-student users"""
    if CLOUD_SYNC_AVAILABLE and sync_manager and hasattr(sync_manager, 'load_sync_config'):
        try:
            if sync_manager.load_sync_config():
                print(f"INFO: Triggering comprehensive sync for: {action_type}")
                sync_manager.sync_all_data()
                print(f"SUCCESS: Comprehensive sync completed for: {action_type}")
        except Exception as e:
            print(f"WARNING: Sync failed for {action_type}: {e}")
    else:
        print(f"INFO: Sync not available for: {action_type}")

# Database change tracker
def log_and_sync_change(user_id, action, details):
    """Log system action AND trigger comprehensive sync"""
    # Log the action
    log_system_action(user_id, action, details)
    
    # Get user role to determine if sync is needed
    if 'user_id' in session:
        conn = sqlite3.connect('bs_nexora_educational.db')
        cursor = conn.cursor()
        cursor.execute('SELECT role FROM users WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        
        # Trigger sync for all non-student users
        if user and user[0] != 'student':
            trigger_comprehensive_sync(action, details)

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Debug mode disabled - simplified authentication working
app.config['DEBUG'] = True

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024 * 1024  # 5GB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Persistent Session Management
SESSION_FILE = 'user_session.json'

def load_universal_config():
    """Load universal auto-login configuration"""
    try:
        if os.path.exists('universal_auto_login_config.json'):
            with open('universal_auto_login_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {"auto_login_enabled": True}  # Default enabled

def save_universal_session(user_data):
    """Save session for any user type with universal auto-login"""
    config = load_universal_config()
    
    if not config.get("auto_login_enabled", True):
        return False
    
    try:
        # Create session data for any user type
        session_data = {
            'user_id': user_data.get('user_id'),
            'username': user_data.get('username'),
            'role': user_data.get('role'),
            'full_name': user_data.get('full_name'),
            'email': user_data.get('email'),
            'login_time': datetime.now().isoformat(),
            'remember_login': True,
            'auto_login_enabled': True,
            'universal_session': True,
            'bypass_face_lock': True,
            'face_id_authenticated': True
        }
        
        # Save to universal session file
        with open('user_session.json', 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        print(f"SUCCESS: Universal session saved for {user_data.get('username')} ({user_data.get('role')})")
        return True
        
    except Exception as e:
        print(f"ERROR: Could not save universal session: {e}")
        return False

def force_session_restore():
    """Force session restoration on every app start for smooth login"""
    if 'user_id' not in session:
        saved_session = load_session_from_file()
        if saved_session:
            for key, value in saved_session.items():
                session[key] = value
            print(f"SUCCESS: Auto-restored session for {session.get('username')} ({session.get('role')})")
            return True
    return False

def save_session_to_file(session_data):
    """Save session data to file for persistence"""
    try:
        # Create a safe copy of session data (exclude sensitive Flask session info)
        safe_session = {
            'user_id': session_data.get('user_id'),
            'username': session_data.get('username'),
            'role': session_data.get('role'),
            'full_name': session_data.get('full_name'),
            'login_time': datetime.now().isoformat(),
            'remember_login': True
        }
        
        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(safe_session, f, indent=2)
        
        print(f"SUCCESS: Session saved for user {session_data.get('username')}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to save session: {e}")
        return False

def load_session_from_file():
    """Load session data from file if exists"""
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # Verify the session is still valid (not older than 30 days)
            login_time = datetime.fromisoformat(session_data.get('login_time', ''))
            days_since_login = (datetime.now() - login_time).days
            
            if days_since_login <= 30:  # Session valid for 30 days
                print(f"SUCCESS: Restored session for user {session_data.get('username')}")
                return session_data
            else:
                print("INFO: Session expired, removing old session file")
                os.remove(SESSION_FILE)
                return None
        return None
    except Exception as e:
        print(f"ERROR: Failed to load session: {e}")
        return None

def clear_session_file():
    """Clear the persistent session file"""
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
            print("SUCCESS: Session file cleared")
        return True
    except Exception as e:
        print(f"ERROR: Failed to clear session: {e}")
        return False

def restore_session_if_exists():
    """Restore session from file if user was previously logged in"""
    if not session.get('user_id'):  # Only restore if not already logged in
        saved_session = load_session_from_file()
        if saved_session:
            # Restore session data
            session['user_id'] = saved_session.get('user_id')
            session['username'] = saved_session.get('username')
            session['role'] = saved_session.get('role')
            session['full_name'] = saved_session.get('full_name')
            session['remember_login'] = True
            return True
    return False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_database():
    """Initialize the database with required tables"""
    # Run database migration first to ensure enhanced columns exist
    try:
        from database_migration import migrate_database
        migrate_database('bs_nexora_educational.db')
    except Exception as e:
        print(f"WARNING: Database migration failed: {e}")
    
    # ENSURE ALL CTO LAYOUT DIRECTORIES EXIST
    from pathlib import Path
    directories = ['custom_layouts', 'layout_backups', 'static', 'static/css', 'static/js', 'templates']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"SUCCESS: CTO Directory ready: {directory}")
    
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Check if users table exists and has full_name column
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'full_name' not in columns and 'users' in [table[0] for table in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        # Add full_name column to existing table
        print("Updating database schema to add full_name column...")
        cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
        conn.commit()
    
    # Users table (simplified - no passkey required, added full_name)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            full_name TEXT,
            subdivision TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Product keys table removed - simplified authentication
    
    # Videos table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_by INTEGER NOT NULL,
            course_category TEXT,
            subject TEXT,
            teacher_subdivision TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            views INTEGER DEFAULT 0,
            FOREIGN KEY (uploaded_by) REFERENCES users (id)
        )
    ''')
    
    # Student FAQ table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT,
            category TEXT DEFAULT 'general',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submitted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            answered_by INTEGER,
            answered_at TIMESTAMP,
            answered_date TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (answered_by) REFERENCES users (id)
        )
    ''')
    
    # Chat Messages table - Private messaging system with CTO oversight
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            message_type TEXT DEFAULT 'text',
            is_read BOOLEAN DEFAULT 0,
            is_deleted BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read_at TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (receiver_id) REFERENCES users (id)
        )
    ''')
    
    # Chat Conversations table - Track conversation threads
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            last_message_id INTEGER,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user1_id) REFERENCES users (id),
            FOREIGN KEY (user2_id) REFERENCES users (id),
            FOREIGN KEY (last_message_id) REFERENCES chat_messages (id),
            UNIQUE(user1_id, user2_id)
        )
    ''')
    
    # Course enrollments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_category TEXT NOT NULL,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            progress INTEGER DEFAULT 0,
            FOREIGN KEY (student_id) REFERENCES users (id)
        )
    ''')
    
    # Video progress tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            video_id INTEGER NOT NULL,
            progress_percentage INTEGER DEFAULT 0,
            completed BOOLEAN DEFAULT 0,
            last_watched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (video_id) REFERENCES videos (id)
        )
    ''')
    
    # System logs for Master and CTO access
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # System activity table for sync compatibility
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Enrollments table for course management
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_category TEXT NOT NULL,
            enrolled_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (student_id) REFERENCES users (id)
        )
    ''')
    
    # Video progress tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            video_id INTEGER NOT NULL,
            progress_percentage REAL DEFAULT 0,
            completed BOOLEAN DEFAULT 0,
            last_watched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (video_id) REFERENCES videos (id)
        )
    ''')
    
    # Chat messages table for communication system
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read BOOLEAN DEFAULT 0,
            is_deleted BOOLEAN DEFAULT 0,
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (receiver_id) REFERENCES users (id)
        )
    ''')
    
    # Chat conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            last_message_id INTEGER,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user1_id) REFERENCES users (id),
            FOREIGN KEY (user2_id) REFERENCES users (id),
            FOREIGN KEY (last_message_id) REFERENCES chat_messages (id)
        )
    ''')
    
    conn.commit()
    
# Create default accounts after database initialization
def create_default_accounts():
    """Create default accounts for all 7 roles"""
    try:
        conn = sqlite3.connect('bs_nexora_educational.db')
        cursor = conn.cursor()
        
        # Check if accounts already exist
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] > 0:
            conn.close()
            # Default accounts already exist
            return
        
        # Creating default accounts
        
        default_accounts = [
            {
                'username': 'master_admin',
                'email': 'master@bsnexora.edu',
                'password': 'Master@2024',
                'role': 'master',
                'subdivision': None,
                'full_name': 'Miss Bhavya Thyagaraj Achar'
            },
            {
                'username': 'cto_admin',
                'email': 'cto@bsnexora.edu',
                'password': 'CTO@2024',
                'role': 'cto',
                'subdivision': None,
                'full_name': 'Master Lalith Chandan'
            },
            {
                'username': 'ceo_admin',
                'email': 'ceo@bsnexora.edu',
                'password': 'CEO@2024',
                'role': 'ceo',
                'subdivision': None,
                'full_name': 'CEO Administrator'
            },
            {
                'username': 'cao_admin',
                'email': 'cao@bsnexora.edu',
                'password': 'CAO@2024',
                'role': 'cao',
                'subdivision': None,
                'full_name': 'CAO Administrator'
            },
            {
                'username': 'student_demo',
                'email': 'student@bsnexora.edu',
                'password': 'Student@2024',
                'role': 'student',
                'subdivision': None,
                'full_name': 'Demo Student'
            },
            {
                'username': 'crew_lead',
                'email': 'crewlead@bsnexora.edu',
                'password': 'CrewLead@2024',
                'role': 'crew_lead',
                'subdivision': None,
                'full_name': 'Crew Lead Administrator'
            },
            {
                'username': 'teacher_python',
                'email': 'teacher.python@bsnexora.edu',
                'password': 'Teacher@2024',
                'role': 'teacher',
                'subdivision': 'Python Classes',
                'full_name': 'Python Classes Instructor'
            },
            {
                'username': 'teacher_prompt_eng',
                'email': 'teacher.prompt@bsnexora.edu',
                'password': 'Teacher@2024',
                'role': 'teacher',
                'subdivision': 'Prompt Engineering',
                'full_name': 'Prompt Engineering Specialist'
            },
            {
                'username': 'teacher_ai_editing',
                'email': 'teacher.ai@bsnexora.edu',
                'password': 'Teacher@2024',
                'role': 'teacher',
                'subdivision': 'AI Editing and Content Creation',
                'full_name': 'AI Content Creation Expert'
            },
            {
                'username': 'teacher_windows_dev',
                'email': 'teacher.windows@bsnexora.edu',
                'password': 'Teacher@2024',
                'role': 'teacher',
                'subdivision': 'Professional Windows Creation',
                'full_name': 'Windows Development Professional'
            },
            {
                'username': 'teacher_app_dev',
                'email': 'teacher.appdev@bsnexora.edu',
                'password': 'Teacher@2024',
                'role': 'teacher',
                'subdivision': 'App Development',
                'full_name': 'Application Development Instructor'
            },
            {
                'username': 'teacher_youtube',
                'email': 'teacher.youtube@bsnexora.edu',
                'password': 'Teacher@2024',
                'role': 'teacher',
                'subdivision': 'Creating Professional YouTube Channel',
                'full_name': 'YouTube Channel Creation Expert'
            },
            {
                'username': 'teacher_ml',
                'email': 'teacher.ml@bsnexora.edu',
                'password': 'Teacher@2024',
                'role': 'teacher',
                'subdivision': 'Machine Learning',
                'full_name': 'Machine Learning Specialist'
            },
            {
                'username': 'teacher_cybersec',
                'email': 'teacher.cyber@bsnexora.edu',
                'password': 'Teacher@2024',
                'role': 'teacher',
                'subdivision': 'Cyber Security',
                'full_name': 'Cyber Security Expert'
            },
            {
                'username': 'teacher_powerbi',
                'email': 'teacher.powerbi@bsnexora.edu',
                'password': 'Teacher@2024',
                'role': 'teacher',
                'subdivision': 'Power BI',
                'full_name': 'Power BI Analytics Instructor'
            },
            {
                'username': 'teacher_excel',
                'email': 'teacher.excel@bsnexora.edu',
                'password': 'Teacher@2024',
                'role': 'teacher',
                'subdivision': 'Advanced Excel',
                'full_name': 'Advanced Excel Professional'
            }
        ]
        
        for account in default_accounts:
            password_hash = generate_password_hash(account['password'])
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role, full_name, subdivision)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (account['username'], account['email'], password_hash, 
                  account['role'], account.get('full_name'), account['subdivision']))
        
        conn.commit()
        print("Default accounts created successfully!")
        
        # Update existing accounts with full names if they don't have them
        update_existing_accounts_with_names(conn, cursor)
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR creating default accounts: {str(e)}")
        import traceback
        traceback.print_exc()

def update_existing_accounts_with_names(conn, cursor):
    """Update existing accounts with full names"""
    try:
        # Check if accounts need full name updates
        cursor.execute("SELECT username, full_name FROM users WHERE full_name IS NULL OR full_name = ''")
        accounts_to_update = cursor.fetchall()
        
        if accounts_to_update:
            print("Updating existing accounts with personalized names...")
            
            name_mapping = {
                'master_admin': 'Miss Bhavya Thyagaraj Achar',
                'cto_admin': 'Master Lalith Chandan',
                'ceo_admin': 'CEO Administrator',
                'cao_admin': 'CAO Administrator',
                'student_demo': 'Demo Student',
                'crew_lead': 'Crew Lead Administrator',
                'teacher_python': 'Python Classes Instructor',
                'teacher_prompt_eng': 'Prompt Engineering Specialist',
                'teacher_ai_editing': 'AI Content Creation Expert',
                'teacher_windows_dev': 'Windows Development Professional',
                'teacher_app_dev': 'Application Development Instructor',
                'teacher_youtube': 'YouTube Channel Creation Expert',
                'teacher_ml': 'Machine Learning Specialist',
                'teacher_cybersec': 'Cyber Security Expert',
                'teacher_powerbi': 'Power BI Analytics Instructor',
                'teacher_excel': 'Advanced Excel Professional'
            }
            
            for username, current_name in accounts_to_update:
                if username in name_mapping:
                    cursor.execute("UPDATE users SET full_name = ? WHERE username = ?", 
                                 (name_mapping[username], username))
                    print(f"Updated {username} with name: {name_mapping[username]}")
            
            conn.commit()
            print("Account names updated successfully!")
            
    except Exception as e:
        print(f"Error updating account names: {str(e)}")

def log_system_action(user_id, action, details=None):
    """Log system actions for audit trail"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Insert into system_logs (main logging table)
    cursor.execute('''
        INSERT INTO system_logs (user_id, action, details)
        VALUES (?, ?, ?)
    ''', (user_id, action, details))
    
    # Also insert into system_activity for sync compatibility
    cursor.execute('''
        INSERT INTO system_activity (user_id, action, details)
        VALUES (?, ?, ?)
    ''', (user_id, action, details))
    
    conn.commit()
    conn.close()

def get_user_permissions(role):
    """Define permissions for each role"""
    permissions = {
        'master': ['all'],
        'cto': [
            # Core CTO permissions
            'development', 'widgets', 'layout_management', 'system_access', 'user_management', 
            'video_management', 'upload_videos', 'view_videos', 'chat', 'chat_admin',
            # Enhanced CTO permissions
            'database_management', 'system_monitoring', 'server_administration', 
            'layout_creation', 'layout_backup', 'layout_restore', 'widget_creation',
            'advanced_analytics', 'system_optimization'
        ],
        'ceo': [
            # Core CEO permissions  
            'oversight', 'account_management', 'reports', 'chat',
            # Enhanced CEO permissions
            'executive_overview', 'strategic_reports', 'platform_analytics',
            'user_oversight', 'performance_metrics', 'business_intelligence',
            'executive_decisions', 'strategic_planning', 'organizational_oversight'
        ],
        'cao': [
            # Core CAO permissions
            'oversight', 'account_management', 'student_faqs', 'reports', 'chat',
            # Enhanced CAO permissions
            'academic_operations', 'faq_management', 'student_support',
            'academic_analytics', 'curriculum_oversight', 'student_progress_monitoring',
            'academic_reporting', 'educational_quality_assurance'
        ],
        'crew_lead': [
            # Core Crew Lead permissions
            'teacher_management', 'video_approval', 'course_management', 'chat',
            # Enhanced Crew Lead permissions
            'performance_analytics', 'content_management', 'teacher_oversight',
            'subdivision_management', 'content_approval', 'team_coordination',
            'teacher_performance_review', 'content_quality_control'
        ],
        'teacher': [
            # Core Teacher permissions
            'upload_videos', 'manage_content', 'student_progress', 'chat',
            # Enhanced Teacher permissions - subdivision-specific
            'python_classes_tools', 'prompt_engineering_tools', 'ai_editing_tools', 'windows_creation_tools',
            'app_development_tools', 'youtube_channel_tools', 'machine_learning_tools', 'cyber_security_tools',
            'power_bi_tools', 'advanced_excel_tools',
            'lesson_planning', 'content_creation', 'student_assessment',
            'specialized_tools', 'subject_resources', 'educational_materials'
        ],
        'student': [
            # Student permissions remain focused
            'view_videos', 'enroll_courses', 'submit_faqs', 'chat',
            'course_progress', 'learning_materials', 'educational_content'
        ]
    }
    return permissions.get(role, [])

def check_permission(required_permission):
    """Decorator to check user permissions"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('login'))
            
            user_role = session.get('role')
            user_permissions = get_user_permissions(user_role)
            
            # BULLETPROOF CTO ACCESS - ALWAYS ALLOW CTO AND MASTER
            if (user_role == 'cto' or 
                user_role == 'master' or 
                'all' in user_permissions or 
                required_permission in user_permissions):
                print(f"SUCCESS: ACCESS GRANTED: User {session.get('username')} with role {user_role} accessing {required_permission}")
                return f(*args, **kwargs)
            else:
                print(f"ERROR: ACCESS DENIED: User {session.get('username')} with role {user_role} tried to access {required_permission}")
                flash(f'Access denied! Your role: {user_role} | Required: {required_permission}', 'error')
                return redirect(url_for('dashboard'))
        
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

@app.before_request
def before_request():
    """Check for persistent session before each request for smooth login"""
    # Skip session check for static files, logout, and login pages
    skip_endpoints = ['static', 'logout', 'login', 'developer_login']
    
    if request.endpoint not in skip_endpoints and 'user_id' not in session:
        if force_session_restore():
            # Session restored successfully
            print(f"INFO: Auto-login successful for {session.get('username')}")

@app.route('/')
def index():
    """Home page - Show index page with login options"""
    print("DEBUG: Index route accessed")
    
    # Check if user is already logged in
    if 'user_id' in session:
        print(f"DEBUG: Active session found for user {session.get('username')}")
        return redirect(url_for('dashboard'))
    
    # Force session restoration for smooth login
    if force_session_restore():
        print(f"SUCCESS: Auto-restored session for user {session.get('username')}")
        flash(f'Welcome back, {session.get("full_name") or session.get("username")}! You were automatically logged in.', 'success')
        return redirect(url_for('dashboard'))
    
    # Fallback: Check for saved session (legacy method)
    if restore_session_if_exists():
        print(f"SUCCESS: Legacy session restore for user {session.get('username')}")
        flash(f'Welcome back, {session.get("full_name") or session.get("username")}! You were automatically logged in.', 'success')
        return redirect(url_for('dashboard'))
    
    # No active session, show index page with login options
    print("DEBUG: Showing index page with login options")
    
    # Check for homepage video
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT filename, upload_date
        FROM videos
        WHERE title = 'Homepage Introduction Video'
        ORDER BY upload_date DESC
        LIMIT 1
    ''')
    homepage_video = cursor.fetchone()
    conn.close()
    
    # Pass Face ID availability to template
    return render_template('index.html', 
                         homepage_video=homepage_video,
                         face_id_available=FACE_ID_AVAILABLE)

@app.route('/about')
def about():
    """About page with owner and developer information"""
    return render_template('about.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Student login page - Cloud + Local authentication"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Try cloud authentication first (Google-like)
        user = None
        if CLOUD_ACCOUNTS_AVAILABLE:
            try:
                cloud_user = authenticate_cloud_user(username, password)
                if cloud_user and cloud_user['role'] == 'student':
                    user = cloud_user
                    print(f"✅ Cloud authentication successful for student: {username}")
            except Exception as e:
                print(f"Cloud authentication error: {e}")
        
        # Fallback to local authentication if cloud fails or user not found
        if not user:
            conn = sqlite3.connect('bs_nexora_educational.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, password_hash, role, email, full_name, subdivision
                FROM users WHERE username = ? AND is_active = 1 AND role = 'student'
            ''', (username,))
            
            local_user = cursor.fetchone()
            conn.close()
            
            if local_user and check_password_hash(local_user[2], password):
                user = {
                    'id': local_user[0],
                    'username': local_user[1],
                    'role': local_user[3],
                    'email': local_user[4],
                    'full_name': local_user[5],
                    'subdivision': local_user[6],
                    'account_type': 'local'
                }
                print(f"✅ Local authentication successful for student: {username}")
        
        if user:
            # Set session data
            session['user_id'] = user.get('id', user.get('username'))
            session['username'] = user['username']
            session['role'] = user['role']
            session['email'] = user.get('email')
            session['full_name'] = user.get('full_name', username)
            session['subdivision'] = user.get('subdivision')
            session['account_type'] = user.get('account_type', 'cloud')
            session['bypass_face_lock'] = True
            session['face_id_authenticated'] = True
            
            # Save session to file for persistence (legacy)
            save_session_to_file(session)
            
            # Save universal session for auto-login
            save_universal_session({
                'user_id': user.get('id', user.get('username')),
                'username': user['username'], 
                'role': user['role'],
                'full_name': user.get('full_name', username),
                'email': user.get('email'),
                'account_type': user.get('account_type', 'cloud')
            })
            
            display_name = user.get('full_name', username)
            account_type = user.get('account_type', 'cloud')
            log_system_action(user.get('id', username), 'login', f'Student {username} logged in ({account_type})')
            
            if account_type == 'cloud':
                flash(f'🌐 Welcome {display_name}! Logged in with cloud account (accessible from any device)', 'success')
            else:
                flash(f'Welcome to your learning dashboard, {display_name}!', 'success')
            
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid student credentials. Please check your username and password.', 'error')
    
    return render_template('login.html')

@app.route('/developer_login', methods=['GET', 'POST'])
def developer_login():
    """Developer login page - Cloud + Local authentication"""
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            
            # Try cloud authentication first (Google-like)
            user = None
            if CLOUD_ACCOUNTS_AVAILABLE:
                try:
                    cloud_user = authenticate_cloud_user(username, password)
                    if cloud_user and cloud_user['role'] != 'student':
                        user = cloud_user
                        print(f"✅ Cloud authentication successful for {cloud_user['role']}: {username}")
                except Exception as e:
                    print(f"Cloud authentication error: {e}")
            
            # Fallback to local authentication if cloud fails or user not found
            if not user:
                conn = sqlite3.connect('bs_nexora_educational.db')
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, username, password_hash, role, email, full_name, subdivision
                    FROM users WHERE username = ? AND is_active = 1 AND role != 'student'
                ''', (username,))
                
                local_user = cursor.fetchone()
                conn.close()
                
                if local_user and check_password_hash(local_user[2], password):
                    user = {
                        'id': local_user[0],
                        'username': local_user[1],
                        'role': local_user[3],
                        'email': local_user[4],
                        'full_name': local_user[5],
                        'subdivision': local_user[6],
                        'account_type': 'local'
                    }
                    print(f"✅ Local authentication successful for {user['role']}: {username}")
            
            if user:
                # Set session data
                session['user_id'] = user.get('id', user.get('username'))
                session['username'] = user['username']
                session['role'] = user['role']
                session['email'] = user.get('email')
                session['full_name'] = user.get('full_name', username)
                session['subdivision'] = user.get('subdivision')
                session['account_type'] = user.get('account_type', 'cloud')
                session['bypass_face_lock'] = True
                session['face_id_authenticated'] = True
                
                # Save session to file for persistence (legacy)
                save_session_to_file(session)
                
                # Save universal session for auto-login
                save_universal_session({
                    'user_id': user.get('id', user.get('username')),
                    'username': user['username'],
                    'role': user['role'], 
                    'full_name': user.get('full_name', username),
                    'email': user.get('email'),
                    'account_type': user.get('account_type', 'cloud')
                })
                
                display_name = user.get('full_name', username)
                account_type = user.get('account_type', 'cloud')
                log_system_action(user.get('id', username), 'login', f'{user["role"]} {username} logged in ({account_type})')
                
                if account_type == 'cloud':
                    flash(f'🌐 Welcome {display_name}! Logged in with cloud account (accessible from any device)', 'success')
                else:
                    flash(f'Welcome, {display_name}! Access granted.', 'success')
                
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials. Please check username and password.', 'error')
                
        except Exception as e:
            print(f"ERROR in developer_login: {str(e)}")
            import traceback
            traceback.print_exc()
            flash('Login error occurred. Please try again.', 'error')
    
    return render_template('developer_login.html')

@app.route('/logout')
def logout():
    """Logout user"""
    if 'user_id' in session:
        log_system_action(session['user_id'], 'logout', f'User {session["username"]} logged out')
    
    # Clear persistent session file
    clear_session_file()
    
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/restore_session')
def restore_session_manual():
    """Manual session restoration for testing"""
    print("DEBUG: Manual session restoration requested")
    
    if 'user_id' in session:
        flash(f'You are already logged in as {session.get("username")}!', 'info')
        return redirect(url_for('dashboard'))
    
    if restore_session_if_exists():
        print(f"SUCCESS: Manually restored session for user {session.get('username')}")
        flash(f'Session restored! Welcome back, {session.get("full_name") or session.get("username")}!', 'success')
        return redirect(url_for('dashboard'))
    else:
        print("DEBUG: No session to restore")
        flash('No saved session found. Please log in.', 'error')
        return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """Main dashboard - role-specific content"""
    print("DEBUG: Dashboard route accessed")
    
    # Try to restore session if user was previously logged in
    if 'user_id' not in session:
        print("DEBUG: No active session in dashboard, attempting restore...")
        if restore_session_if_exists():
            print(f"SUCCESS: Auto-restored session for user {session.get('username')} in dashboard")
            flash(f'Welcome back, {session.get("full_name") or session.get("username")}! Your session was restored.', 'info')
        else:
            print("DEBUG: No saved session found, redirecting to login")
            flash('Please log in to access the dashboard.', 'error')
            return redirect(url_for('login'))
    else:
        print(f"DEBUG: Active session in dashboard for user {session.get('username')}")
    
    role = session.get('role')
    display_name = session.get('full_name') or session.get('username')
    return render_template(f'dashboard_{role}.html', 
                         username=session.get('username'),
                         display_name=display_name,
                         role=role,
                         subdivision=session.get('subdivision'))

@app.route('/upload_video', methods=['GET', 'POST'])
@check_permission('upload_videos')
def upload_video():
    """Video upload for Master, CTO, and Teachers"""
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        course_category = request.form['course_category']
        subject = request.form['subject']
        
        if 'video_file' not in request.files:
            flash('No video file selected.', 'error')
            return redirect(request.url)
        
        file = request.files['video_file']
        if file.filename == '':
            flash('No video file selected.', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                # Add timestamp to avoid conflicts
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Check file size (9.03 MB should be well under 5GB limit)
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(0)  # Reset to beginning
                
                print(f"DEBUG: Uploading file {filename}, size: {file_size} bytes ({file_size/1024/1024:.2f} MB)")
                
                file.save(file_path)
                print(f"DEBUG: File saved successfully to {file_path}")
                
                # AUTOMATIC COMPRESSION FOR LARGE FILES
                final_file_path = file_path
                compression_applied = False
                
                if AUTO_COMPRESSION_AVAILABLE and auto_compressor:
                    if auto_compressor.should_compress(file_path):
                        print(f"INFO: File size {file_size/1024/1024:.2f} MB > 100 MB - applying automatic compression...")
                        flash(f'Large file detected ({file_size/1024/1024:.1f} MB) - compressing for optimal sync...', 'info')
                        
                        def progress_callback(message):
                            print(f"COMPRESSION: {message}")
                        
                        compressed_path = auto_compressor.auto_compress_for_upload(file_path, progress_callback)
                        
                        if compressed_path != file_path:
                            # Compression successful
                            final_file_path = compressed_path
                            compression_applied = True
                            compressed_size = os.path.getsize(compressed_path)
                            reduction = (1 - compressed_size / file_size) * 100
                            
                            print(f"SUCCESS: Video compressed from {file_size/1024/1024:.1f} MB to {compressed_size/1024/1024:.1f} MB ({reduction:.1f}% reduction)")
                            flash(f'Video automatically compressed: {file_size/1024/1024:.1f} MB → {compressed_size/1024/1024:.1f} MB (now syncs perfectly!)', 'success')
                            
                            # Update filename for database
                            filename = os.path.basename(compressed_path)
                        else:
                            print("INFO: Compression not applied - using original file")
                    else:
                        print(f"INFO: File size {file_size/1024/1024:.2f} MB ≤ 100 MB - no compression needed")
                else:
                    print("INFO: Automatic compression not available")
                
            except Exception as e:
                print(f"ERROR: File upload failed: {str(e)}")
                flash(f'File upload failed: {str(e)}', 'error')
                return redirect(request.url)
            
            # Save to database
            conn = sqlite3.connect('bs_nexora_educational.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO videos (title, description, filename, file_path, uploaded_by, 
                                  course_category, subject, teacher_subdivision)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, description, filename, final_file_path, session['user_id'],
                  course_category, subject, session.get('subdivision')))
            conn.commit()
            conn.close()
            
            # Log and trigger comprehensive sync for cross-device availability
            log_and_sync_change(session['user_id'], 'video_upload', 
                               f'Uploaded video: {title} - Available on all devices (Mobile, Desktop, Web)')
            flash('Video uploaded and synced across ALL devices! Students can now watch on mobile, desktop, and web.', 'success')
            
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid file type. Please upload a video file.', 'error')
    
    return render_template('upload_video.html')

@app.route('/manage_users')
@check_permission('user_management')
def manage_users():
    """User management for Master and CTO"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, email, role, full_name, subdivision, created_date, is_active
        FROM users ORDER BY created_date DESC
    ''')
    users = cursor.fetchall()
    conn.close()
    
    return render_template('manage_users.html', users=users)

@app.route('/student_faqs')
@check_permission('student_faqs')
def student_faqs():
    """Student FAQ management for CAO"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT f.id, f.question, f.answer, f.status, f.created_at,
               u.username as student_name
        FROM student_faqs f
        JOIN users u ON f.student_id = u.id
        ORDER BY f.created_at DESC
    ''')
    faqs = cursor.fetchall()
    conn.close()
    
    return render_template('student_faqs.html', faqs=faqs)

@app.route('/view_videos')
@check_permission('view_videos')
def view_videos():
    """Video viewing for students - Cross-device compatible"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT v.id, v.title, v.description, v.course_category, v.subject,
               v.upload_date, u.username as uploaded_by, u.full_name as teacher_name,
               v.teacher_subdivision, v.views, v.filename
        FROM videos v
        JOIN users u ON v.uploaded_by = u.id
        WHERE v.is_active = 1
        ORDER BY v.upload_date DESC
    ''')
    videos = cursor.fetchall()
    conn.close()
    
    return render_template('view_videos.html', videos=videos)

@app.route('/mobile_videos')
@check_permission('view_videos')
def mobile_videos():
    """Mobile-optimized video viewing for cross-device access"""
    return render_template('mobile_videos.html')

@app.route('/api/videos', methods=['GET'])
def api_get_videos():
    """Cross-device API endpoint for video access - Works on all devices"""
    try:
        # Check if user is authenticated (for API access)
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'message': 'Authentication required',
                'videos': []
            }), 401
        
        # Get user role to determine access level
        user_role = session.get('role', 'student')
        
        conn = sqlite3.connect('bs_nexora_educational.db')
        cursor = conn.cursor()
        
        if user_role == 'student':
            # Students see all active videos from all teachers
            cursor.execute('''
                SELECT v.id, v.title, v.description, v.course_category, v.subject,
                       v.upload_date, u.username as uploaded_by, u.full_name as teacher_name,
                       v.teacher_subdivision, v.views, v.filename, v.file_path
                FROM videos v
                JOIN users u ON v.uploaded_by = u.id
                WHERE v.is_active = 1
                ORDER BY v.upload_date DESC
            ''')
        else:
            # Teachers/Admins see all videos (including inactive)
            cursor.execute('''
                SELECT v.id, v.title, v.description, v.course_category, v.subject,
                       v.upload_date, u.username as uploaded_by, u.full_name as teacher_name,
                       v.teacher_subdivision, v.views, v.filename, v.file_path, v.is_active
                FROM videos v
                JOIN users u ON v.uploaded_by = u.id
                ORDER BY v.upload_date DESC
            ''')
        
        videos_data = cursor.fetchall()
        conn.close()
        
        # Format videos for cross-device compatibility
        videos_list = []
        for video in videos_data:
            video_info = {
                'id': video[0],
                'title': video[1],
                'description': video[2],
                'course_category': video[3],
                'subject': video[4],
                'upload_date': video[5],
                'uploaded_by': video[6],
                'teacher_name': video[7],
                'teacher_subdivision': video[8],
                'views': video[9],
                'filename': video[10],
                'video_url': f"/uploads/{video[10]}",  # Direct video access URL
                'streaming_url': f"/stream_video/{video[0]}",  # Streaming endpoint
                'cross_device_compatible': True,
                'mobile_optimized': True
            }
            
            # Add admin-only fields
            if user_role != 'student' and len(video) > 12:
                video_info['is_active'] = video[12]
                video_info['file_path'] = video[11]
            
            videos_list.append(video_info)
        
        return jsonify({
            'success': True,
            'message': f'Retrieved {len(videos_list)} videos for cross-device access',
            'videos': videos_list,
            'user_role': user_role,
            'cross_device_sync': True,
            'total_videos': len(videos_list)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving videos: {str(e)}',
            'videos': []
        }), 500

@app.route('/stream_video/<int:video_id>')
def stream_video(video_id):
    """Stream video for cross-device compatibility"""
    try:
        # Check authentication
        if 'user_id' not in session:
            flash('Please log in to watch videos.', 'error')
            return redirect(url_for('login'))
        
        # Get video info
        conn = sqlite3.connect('bs_nexora_educational.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT filename, file_path, title, views
            FROM videos 
            WHERE id = ? AND is_active = 1
        ''', (video_id,))
        video = cursor.fetchone()
        
        if not video:
            conn.close()
            return "Video not found or inactive", 404
        
        # Update view count
        cursor.execute('UPDATE videos SET views = views + 1 WHERE id = ?', (video_id,))
        conn.commit()
        conn.close()
        
        filename, file_path, title, views = video
        
        # Serve video file with cross-device headers
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], 
            filename,
            as_attachment=False,
            mimetype='video/mp4'  # Ensure proper MIME type for cross-device compatibility
        )
        
    except Exception as e:
        return f"Error streaming video: {str(e)}", 500

@app.route('/teacher_management')
@check_permission('teacher_management')
def teacher_management():
    """Teacher management for Crew Lead"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, email, subdivision, created_date, is_active
        FROM users WHERE role = 'teacher'
        ORDER BY subdivision, username
    ''')
    teachers = cursor.fetchall()
    conn.close()
    
    return render_template('teacher_management.html', teachers=teachers)

@app.route('/system_logs')
@check_permission('system_access')
def system_logs():
    """System logs for Master and CTO"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT l.action, l.details, l.timestamp, u.username
        FROM system_logs l
        JOIN users u ON l.user_id = u.id
        ORDER BY l.timestamp DESC
        LIMIT 100
    ''')
    logs = cursor.fetchall()
    conn.close()
    
    return render_template('system_logs.html', logs=logs)

@app.route('/create_account', methods=['GET', 'POST'])
@check_permission('user_management')
def create_account():
    """Create new accounts - Master and CTO only (Cloud + Local)"""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        full_name = request.form.get('full_name')
        subdivision = request.form.get('subdivision')
        account_type = request.form.get('account_type', 'cloud')  # Default to cloud
        
        # Try to create cloud account first if enabled
        cloud_success = False
        if CLOUD_ACCOUNTS_AVAILABLE and account_type == 'cloud':
            try:
                cloud_account_id = create_cloud_account(username, email, password, role, full_name, subdivision)
                if cloud_account_id:
                    cloud_success = True
                    log_and_sync_change(session['user_id'], 'cloud_account_creation', 
                                      f'Created cloud account for {username} with role {role}')
                    flash(f'🌐 Cloud account created successfully! Username: {username} (accessible from any device)', 'success')
                else:
                    flash('Failed to create cloud account. Creating local account instead.', 'warning')
            except Exception as e:
                print(f"Cloud account creation error: {e}")
                flash('Cloud account creation failed. Creating local account instead.', 'warning')
        
        # Create local account if cloud failed or local was requested
        if not cloud_success:
            password_hash = generate_password_hash(password)
            
            conn = sqlite3.connect('bs_nexora_educational.db')
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, role, full_name, subdivision, account_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (username, email, password_hash, role, full_name, subdivision, 'local'))
                conn.commit()
                
                # Log and trigger comprehensive sync for new account
                log_and_sync_change(session['user_id'], 'account_creation', 
                                f'Created local account for {username} with role {role}')
                flash(f'Local account created successfully! Username: {username}', 'success')
            except sqlite3.IntegrityError:
                flash('Username or email already exists.', 'error')
            finally:
                conn.close()
    
    # Pass cloud availability to template
    return render_template('create_account.html', 
                         cloud_enabled=CLOUD_ACCOUNTS_AVAILABLE if CLOUD_ACCOUNTS_AVAILABLE else False)

@app.route('/cloud_account_setup', methods=['GET', 'POST'])
@check_permission('system_access')
def cloud_account_setup():
    """Setup cloud account system - Master and CTO only"""
    if request.method == 'POST':
        github_token = request.form['github_token']
        github_owner = request.form['github_owner']
        github_repo = request.form['github_repo']
        
        if CLOUD_ACCOUNTS_AVAILABLE:
            try:
                success = cloud_account_manager.setup_cloud_storage(github_token, github_owner, github_repo)
                if success:
                    flash('🌐 Cloud account system setup successfully! Accounts will now be accessible from any device.', 'success')
                    log_and_sync_change(session['user_id'], 'cloud_setup', 
                                      f'Cloud account system configured by {session["username"]}')
                else:
                    flash('Failed to setup cloud account system. Please check your GitHub credentials.', 'error')
            except Exception as e:
                flash(f'Cloud setup error: {str(e)}', 'error')
        else:
            flash('Cloud account system not available.', 'error')
    
    return render_template('cloud_account_setup.html', 
                         cloud_enabled=CLOUD_ACCOUNTS_AVAILABLE if CLOUD_ACCOUNTS_AVAILABLE else False,
                         is_configured=cloud_account_manager.cloud_enabled if CLOUD_ACCOUNTS_AVAILABLE else False)

@app.route('/cloud_accounts_list')
@check_permission('user_management')
def cloud_accounts_list():
    """List all cloud accounts - Master and CTO only"""
    accounts = []
    if CLOUD_ACCOUNTS_AVAILABLE:
        try:
            accounts = cloud_account_manager.list_cloud_accounts()
        except Exception as e:
            flash(f'Error loading cloud accounts: {str(e)}', 'error')
    
    return render_template('cloud_accounts_list.html', 
                         accounts=accounts,
                         cloud_enabled=CLOUD_ACCOUNTS_AVAILABLE if CLOUD_ACCOUNTS_AVAILABLE else False)

# CTO-specific routes for actual functionality

@app.route('/widget_management')
@check_permission('widgets')
def widget_management():
    """Widget management for CTO"""
    # Get system statistics for widgets
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get basic stats
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM videos')
    total_videos = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM system_logs')
    total_logs = cursor.fetchone()[0]
    
    conn.close()
    
    widgets = [
        {'name': 'User Counter', 'value': total_users, 'type': 'counter', 'color': '#4ecdc4'},
        {'name': 'Video Library', 'value': total_videos, 'type': 'counter', 'color': '#ff6b6b'},
        {'name': 'System Logs', 'value': total_logs, 'type': 'counter', 'color': '#feca57'},
        {'name': 'Platform Status', 'value': 'Online', 'type': 'status', 'color': '#5f27cd'}
    ]
    
    return render_template('widget_management.html', widgets=widgets)

@app.route('/database_stats')
@check_permission('system_access')
def database_stats():
    """Database statistics for CTO and Master"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get table statistics
    stats = {}
    tables = ['users', 'videos', 'system_logs', 'student_faqs', 'enrollments', 'video_progress']
    
    for table in tables:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            stats[table] = cursor.fetchone()[0]
        except:
            stats[table] = 0
    
    # Get recent activity
    cursor.execute('''
        SELECT action, details, timestamp, u.username
        FROM system_logs l
        JOIN users u ON l.user_id = u.id
        ORDER BY l.timestamp DESC
        LIMIT 10
    ''')
    recent_activity = cursor.fetchall()
    
    conn.close()
    
    return render_template('database_stats.html', stats=stats, recent_activity=recent_activity)

@app.route('/system_settings')
@check_permission('system_access')
def system_settings():
    """System settings for CTO and Master"""
    settings = {
        'max_upload_size': '5GB',
        'allowed_formats': ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'],
        'debug_mode': app.config.get('DEBUG', False),
        'database_path': 'bs_nexora_educational.db'
    }
    
    return render_template('system_settings.html', settings=settings)

@app.route('/video_management')
@check_permission('video_management')
def video_management():
    """Video management for Master and CTO"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get all videos with uploader info
    cursor.execute('''
        SELECT v.id, v.title, v.description, v.filename, v.uploaded_date, 
               u.username, u.full_name, v.course_category, v.subject
        FROM videos v
        JOIN users u ON v.uploaded_by = u.id
        ORDER BY v.uploaded_date DESC
    ''')
    videos = cursor.fetchall()
    
    # Get video statistics
    cursor.execute('SELECT COUNT(*) FROM videos')
    total_videos = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT uploaded_by) FROM videos')
    unique_uploaders = cursor.fetchone()[0]
    
    conn.close()
    
    return render_template('video_management.html', 
                         videos=videos, 
                         total_videos=total_videos,
                         unique_uploaders=unique_uploaders)

@app.route('/delete_video/<int:video_id>', methods=['POST'])
@check_permission('video_management')
def delete_video(video_id):
    """Delete video - Master and CTO only"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get video info before deletion
    cursor.execute('SELECT title, filename, file_path FROM videos WHERE id = ?', (video_id,))
    video_info = cursor.fetchone()
    
    if not video_info:
        flash('Video not found.', 'error')
        return redirect(url_for('video_management'))
    
    title, filename, file_path = video_info
    
    try:
        # Delete video file from filesystem
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"SUCCESS: Deleted video file: {file_path}")
        
        # Delete from database
        cursor.execute('DELETE FROM videos WHERE id = ?', (video_id,))
        conn.commit()
        
        # Log and trigger comprehensive sync for video deletion
        log_and_sync_change(session['user_id'], 'video_deletion', 
                         f'Deleted video: {title} (ID: {video_id})')
        
        flash(f'Video "{title}" deleted and synced!', 'success')
        
    except Exception as e:
        print(f"ERROR: Error deleting video: {str(e)}")
        flash(f'Error deleting video: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('video_management'))

@app.route('/toggle_video_status/<int:video_id>', methods=['POST'])
@check_permission('video_management')
def toggle_video_status(video_id):
    """Toggle video active/inactive status - Master and CTO only"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get current status
    cursor.execute('SELECT title, is_active FROM videos WHERE id = ?', (video_id,))
    video_info = cursor.fetchone()
    
    if not video_info:
        flash('Video not found.', 'error')
        return redirect(url_for('video_management'))
    
    title, current_status = video_info
    new_status = 0 if current_status else 1
    status_text = "activated" if new_status else "deactivated"
    
    try:
        # Update status
        cursor.execute('UPDATE videos SET is_active = ? WHERE id = ?', (new_status, video_id))
        conn.commit()
        
        # Log the action
        log_system_action(session['user_id'], 'video_status_change', 
                         f'{status_text.capitalize()} video: {title} (ID: {video_id})')
        
        flash(f'Video "{title}" {status_text} successfully!', 'success')
        
    except Exception as e:
        print(f"ERROR: Error updating video status: {str(e)}")
        flash(f'Error updating video status: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('video_management'))

@app.route('/analytics')
@check_permission('system_access')
def analytics():
    """Platform analytics for Master and CTO"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # User analytics
    cursor.execute('SELECT role, COUNT(*) FROM users GROUP BY role')
    user_by_role = cursor.fetchall()
    
    # Video analytics
    cursor.execute('SELECT course_category, COUNT(*) FROM videos GROUP BY course_category')
    videos_by_category = cursor.fetchall()
    
    # Activity analytics
    cursor.execute('''
        SELECT DATE(timestamp) as date, COUNT(*) as activities
        FROM system_logs 
        WHERE timestamp >= date('now', '-7 days')
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
    ''')
    daily_activity = cursor.fetchall()
    
    conn.close()
    
    analytics_data = {
        'user_by_role': user_by_role,
        'videos_by_category': videos_by_category,
        'daily_activity': daily_activity
    }
    
    return render_template('analytics.html', analytics=analytics_data)

@app.route('/security_audit')
@check_permission('system_access')
def security_audit():
    """Security audit for Master and CTO"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Check for security issues
    security_checks = []
    
    # Check for inactive users
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 0')
    inactive_users = cursor.fetchone()[0]
    security_checks.append({
        'check': 'Inactive Users',
        'status': 'warning' if inactive_users > 0 else 'good',
        'message': f'{inactive_users} inactive user accounts found' if inactive_users > 0 else 'No inactive users',
        'action': 'Review and clean up inactive accounts' if inactive_users > 0 else None
    })
    
    # Check recent login attempts
    cursor.execute('''
        SELECT COUNT(*) FROM system_logs 
        WHERE action = 'login' AND timestamp >= datetime('now', '-24 hours')
    ''')
    recent_logins = cursor.fetchone()[0]
    security_checks.append({
        'check': 'Recent Login Activity',
        'status': 'good',
        'message': f'{recent_logins} login attempts in last 24 hours',
        'action': None
    })
    
    # Check for admin accounts
    cursor.execute("SELECT COUNT(*) FROM users WHERE role IN ('master', 'cto')")
    admin_count = cursor.fetchone()[0]
    security_checks.append({
        'check': 'Admin Accounts',
        'status': 'good' if admin_count >= 2 else 'warning',
        'message': f'{admin_count} admin accounts configured',
        'action': 'Ensure proper admin account backup' if admin_count < 2 else None
    })
    
    conn.close()
    
    return render_template('security_audit.html', security_checks=security_checks)

@app.route('/homepage_video_management', methods=['GET', 'POST'])
@check_permission('system_access')
def homepage_video_management():
    """Homepage video management for CTO and Master"""
    if request.method == 'POST':
        if 'video_file' not in request.files:
            flash('No video file selected.', 'error')
            return redirect(request.url)
        
        file = request.files['video_file']
        if file.filename == '':
            flash('No video file selected.', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                # Special naming for homepage video
                homepage_filename = f"homepage_intro_video.{filename.rsplit('.', 1)[1].lower()}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], homepage_filename)
                
                # Remove old homepage video if exists
                for ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv']:
                    old_file = os.path.join(app.config['UPLOAD_FOLDER'], f"homepage_intro_video.{ext}")
                    if os.path.exists(old_file):
                        os.remove(old_file)
                
                # Ensure upload directory exists
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                file.save(file_path)
                print(f"Homepage video saved to: {file_path}")
                
                # Update database with homepage video info
                conn = sqlite3.connect('bs_nexora_educational.db')
                cursor = conn.cursor()
                
                # Remove old homepage video record
                cursor.execute("DELETE FROM videos WHERE title = 'Homepage Introduction Video'")
                
                # Add new homepage video record
                cursor.execute('''
                    INSERT INTO videos (title, description, filename, file_path, uploaded_by, 
                                      course_category, subject, teacher_subdivision)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', ('Homepage Introduction Video', 'Introduction video displayed on homepage', 
                      homepage_filename, file_path, session['user_id'],
                      'Platform Introduction', 'General', None))
                
                conn.commit()
                conn.close()
                
                # Log and trigger comprehensive sync for homepage video
                log_and_sync_change(session['user_id'], 'homepage_video_upload', 
                                f'Uploaded homepage video: {homepage_filename}')
                flash('Homepage video uploaded and ALL changes synced automatically!', 'success')
                
            except Exception as e:
                flash(f'Error uploading homepage video: {str(e)}', 'error')
        else:
            flash('Invalid file format. Please upload a video file.', 'error')
    
    # Get current homepage video if exists
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT filename, upload_date, u.full_name, u.username
        FROM videos v
        JOIN users u ON v.uploaded_by = u.id
        WHERE v.title = 'Homepage Introduction Video'
        ORDER BY v.upload_date DESC
        LIMIT 1
    ''')
    current_video = cursor.fetchone()
    conn.close()
    
    return render_template('homepage_video_management.html', current_video=current_video)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    try:
        # Ensure uploads directory exists
        upload_path = os.path.abspath(app.config['UPLOAD_FOLDER'])
        if not os.path.exists(upload_path):
            os.makedirs(upload_path, exist_ok=True)
        
        file_path = os.path.join(upload_path, filename)
        if os.path.exists(file_path):
            response = send_from_directory(upload_path, filename)
            # Add headers for video streaming
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Content-Type'] = 'video/mp4'
            return response
        else:
            print(f"File not found: {file_path}")
            return "File not found", 404
    except Exception as e:
        print(f"Error serving file {filename}: {str(e)}")
        return "Error serving file", 500

@app.route('/static/uploads/<filename>')
def static_uploaded_file(filename):
    """Alternative route for serving uploaded files"""
    return uploaded_file(filename)

@app.route('/debug/uploads')
@check_permission('system_access')
def debug_uploads():
    """Debug route to check upload directory"""
    upload_path = os.path.abspath(app.config['UPLOAD_FOLDER'])
    files = []
    if os.path.exists(upload_path):
        files = os.listdir(upload_path)
    
    return f"""
    <h2>Upload Directory Debug</h2>
    <p><strong>Upload Path:</strong> {upload_path}</p>
    <p><strong>Directory Exists:</strong> {os.path.exists(upload_path)}</p>
    <p><strong>Files:</strong></p>
    <ul>
    {''.join([f'<li>{file}</li>' for file in files])}
    </ul>
    <p><a href="/">Back to Home</a></p>
    """

# CEO-specific routes
@app.route('/executive_overview')
@check_permission('executive_overview')
def executive_overview():
    """Executive overview for CEO"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get executive statistics
    cursor.execute('SELECT COUNT(*) FROM users WHERE role IN ("student", "crew_lead", "teacher")')
    managed_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM videos')
    total_content = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM system_logs WHERE timestamp >= date("now", "-30 days")')
    monthly_activity = cursor.fetchone()[0]
    
    # Get user breakdown
    cursor.execute('SELECT role, COUNT(*) FROM users GROUP BY role')
    user_breakdown = cursor.fetchall()
    
    conn.close()
    
    stats = {
        'managed_users': managed_users,
        'total_content': total_content,
        'monthly_activity': monthly_activity,
        'user_breakdown': user_breakdown
    }
    
    return render_template('executive_overview.html', stats=stats)

@app.route('/strategic_reports')
@check_permission('strategic_reports')
def strategic_reports():
    """Strategic reports for CEO"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Platform growth metrics
    cursor.execute('''
        SELECT DATE(created_date) as date, COUNT(*) as new_users
        FROM users 
        WHERE created_date >= date('now', '-30 days')
        GROUP BY DATE(created_date)
        ORDER BY date DESC
    ''')
    growth_data = cursor.fetchall()
    
    # Content creation metrics
    cursor.execute('''
        SELECT DATE(upload_date) as date, COUNT(*) as videos
        FROM videos 
        WHERE upload_date >= date('now', '-30 days')
        GROUP BY DATE(upload_date)
        ORDER BY date DESC
    ''')
    content_data = cursor.fetchall()
    
    conn.close()
    
    reports = {
        'growth_data': growth_data,
        'content_data': content_data
    }
    
    return render_template('strategic_reports.html', reports=reports)

# CAO-specific routes
@app.route('/academic_oversight')
@check_permission('academic_operations')
def academic_oversight():
    """Academic oversight for CAO"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get academic statistics
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "student"')
    total_students = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "teacher"')
    total_teachers = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM student_faqs')
    total_faqs = cursor.fetchone()[0]
    
    # Get recent FAQs
    cursor.execute('''
        SELECT question, answer, submitted_date, u.username
        FROM student_faqs f
        JOIN users u ON f.student_id = u.id
        ORDER BY f.submitted_date DESC
        LIMIT 10
    ''')
    recent_faqs = cursor.fetchall()
    
    conn.close()
    
    data = {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_faqs': total_faqs,
        'recent_faqs': recent_faqs
    }
    
    return render_template('academic_oversight.html', data=data)

@app.route('/manage_faqs')
@check_permission('student_faqs')
def manage_faqs():
    """FAQ management for CAO"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT f.id, f.question, f.answer, f.submitted_date, f.answered_date,
               u.username, u.full_name
        FROM student_faqs f
        JOIN users u ON f.student_id = u.id
        ORDER BY f.submitted_date DESC
    ''')
    faqs = cursor.fetchall()
    
    conn.close()
    
    return render_template('manage_faqs.html', faqs=faqs)

# Student-specific routes
@app.route('/student_progress')
@check_permission('view_videos')
def student_progress():
    """Student progress tracking"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get student's progress
    cursor.execute('''
        SELECT v.title, v.course_category, vp.progress_percentage, vp.last_watched
        FROM video_progress vp
        JOIN videos v ON vp.video_id = v.id
        WHERE vp.user_id = ?
        ORDER BY vp.last_watched DESC
    ''', (session['user_id'],))
    progress_data = cursor.fetchall()
    
    # Get enrolled courses
    cursor.execute('''
        SELECT course_name, enrollment_date, completion_status
        FROM enrollments
        WHERE student_id = ?
        ORDER BY enrollment_date DESC
    ''', (session['user_id'],))
    enrollments = cursor.fetchall()
    
    conn.close()
    
    return render_template('student_progress.html', 
                         progress_data=progress_data, 
                         enrollments=enrollments)

@app.route('/submit_faq', methods=['GET', 'POST'])
@check_permission('submit_faqs')
def submit_faq():
    """Submit FAQ for students"""
    if request.method == 'POST':
        question = request.form.get('question')
        if question:
            conn = sqlite3.connect('bs_nexora_educational.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO student_faqs (student_id, question, submitted_date)
                VALUES (?, ?, ?)
            ''', (session['user_id'], question, datetime.now()))
            
            conn.commit()
            conn.close()
            
            flash('Your question has been submitted successfully!', 'success')
            return redirect(url_for('submit_faq'))
    
    return render_template('submit_faq.html')

# Teacher-specific routes
@app.route('/teacher_content')
@check_permission('upload_videos')
def teacher_content():
    """Teacher content management"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get teacher's uploaded videos
    cursor.execute('''
        SELECT id, title, description, course_category, subject, upload_date
        FROM videos
        WHERE uploaded_by = ?
        ORDER BY upload_date DESC
    ''', (session['user_id'],))
    teacher_videos = cursor.fetchall()
    
    conn.close()
    
    return render_template('teacher_content.html', videos=teacher_videos)

@app.route('/lesson_planner')
@check_permission('upload_videos')
def lesson_planner():
    """Lesson planning for teachers"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get teacher's subject
    cursor.execute('SELECT teacher_subdivision FROM users WHERE id = ?', (session['user_id'],))
    subject = cursor.fetchone()[0] if cursor.fetchone() else 'General'
    
    # Get subject-specific videos
    cursor.execute('''
        SELECT title, description, upload_date
        FROM videos
        WHERE subject = ? OR uploaded_by = ?
        ORDER BY upload_date DESC
    ''', (subject, session['user_id']))
    subject_videos = cursor.fetchall()
    
    conn.close()
    
    return render_template('lesson_planner.html', 
                         subject=subject, 
                         videos=subject_videos)

# CEO Executive Dashboard Routes
@app.route('/ceo/executive-overview')
@check_permission('oversight')
def ceo_executive_overview():
    """CEO Executive Overview Dashboard"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get comprehensive platform statistics
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE role IN ('student', 'teacher', 'crew_lead')")
    managed_accounts = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM videos")
    total_videos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM student_faqs")
    total_faqs = cursor.fetchone()[0]
    
    # Get recent activity
    cursor.execute("""
        SELECT u.username, u.role, u.created_date, u.full_name
        FROM users u 
        WHERE u.role IN ('student', 'teacher', 'crew_lead')
        ORDER BY u.created_date DESC 
        LIMIT 10
    """)
    recent_activity = cursor.fetchall()
    
    # Get performance metrics
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN role = 'student' THEN 1 END) as students,
            COUNT(CASE WHEN role = 'teacher' THEN 1 END) as teachers,
            COUNT(CASE WHEN role = 'crew_lead' THEN 1 END) as crew_leads
        FROM users
    """)
    role_breakdown = cursor.fetchone()
    
    conn.close()
    
    return render_template('ceo_executive_overview.html',
                         total_users=total_users,
                         managed_accounts=managed_accounts,
                         total_videos=total_videos,
                         total_faqs=total_faqs,
                         recent_activity=recent_activity,
                         role_breakdown=role_breakdown)

@app.route('/ceo/strategic-reports')
@check_permission('reports')
def ceo_strategic_reports():
    """CEO Strategic Reports and Analytics"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Generate comprehensive reports
    reports = {
        'user_growth': [],
        'content_metrics': [],
        'engagement_stats': [],
        'system_health': []
    }
    
    # User growth analysis
    cursor.execute("""
        SELECT DATE(created_date) as date, COUNT(*) as new_users
        FROM users 
        WHERE created_date >= DATE('now', '-30 days')
        GROUP BY DATE(created_date)
        ORDER BY date DESC
    """)
    reports['user_growth'] = cursor.fetchall()
    
    # Content metrics
    cursor.execute("""
        SELECT 
            subject,
            COUNT(*) as video_count,
            0 as avg_size
        FROM videos 
        GROUP BY subject
    """)
    reports['content_metrics'] = cursor.fetchall()
    
    conn.close()
    
    return render_template('ceo_strategic_reports.html', reports=reports)

@app.route('/ceo/account-oversight')
@check_permission('account_management')
def ceo_account_oversight():
    """CEO Account Management and Oversight"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get all managed accounts (students, teachers, crew leads)
    cursor.execute("""
        SELECT id, username, email, role, subdivision, full_name, created_date, 'Never' as last_login
        FROM users 
        WHERE role IN ('student', 'teacher', 'crew_lead')
        ORDER BY role, created_date DESC
    """)
    managed_accounts = cursor.fetchall()
    
    conn.close()
    
    return render_template('ceo_account_oversight.html', accounts=managed_accounts)

# CAO Academic Operations Routes
@app.route('/cao/academic-operations')
@check_permission('oversight')
def cao_academic_operations():
    """CAO Academic Operations Dashboard"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get academic statistics
    cursor.execute("SELECT COUNT(*) FROM student_faqs WHERE status = 'pending'")
    pending_faqs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM videos WHERE course_category IS NOT NULL")
    academic_content = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
    total_students = cursor.fetchone()[0]
    
    # Get recent FAQ submissions
    cursor.execute("""
        SELECT f.id, f.question, 'general' as category, f.status, f.created_at, u.full_name
        FROM student_faqs f
        JOIN users u ON f.student_id = u.id
        ORDER BY f.created_at DESC
        LIMIT 15
    """)
    recent_faqs = cursor.fetchall()
    
    conn.close()
    
    return render_template('cao_academic_operations.html',
                         pending_faqs=pending_faqs,
                         academic_content=academic_content,
                         total_students=total_students,
                         recent_faqs=recent_faqs)

@app.route('/cao/student-faq-management')
@check_permission('student_faqs')
def cao_faq_management():
    """CAO Student FAQ Management System"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get all FAQs with student information
    cursor.execute("""
        SELECT f.id, f.question, 'general' as category, f.status, f.created_at, f.answer, u.full_name, u.username
        FROM student_faqs f
        JOIN users u ON f.student_id = u.id
        ORDER BY f.created_at DESC
    """)
    all_faqs = cursor.fetchall()
    
    conn.close()
    
    return render_template('cao_faq_management.html', faqs=all_faqs)

@app.route('/cao/answer-faq', methods=['POST'])
@check_permission('student_faqs')
def cao_answer_faq():
    """CAO Answer Student FAQ"""
    faq_id = request.form.get('faq_id')
    answer = request.form.get('answer')
    
    if not faq_id or not answer:
        flash('FAQ ID and answer are required.', 'error')
        return redirect(url_for('cao_faq_management'))
    
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE student_faqs 
        SET answer = ?, status = 'answered', answered_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (answer, faq_id))
    
    conn.commit()
    conn.close()
    
    flash('FAQ answered successfully!', 'success')
    return redirect(url_for('cao_faq_management'))

@app.route('/cao/academic-reports')
@check_permission('academic_operations')
def cao_academic_reports():
    """CAO Academic Reports and Analytics"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Student performance metrics
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
    total_students = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM videos")
    total_content = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM student_faqs WHERE status = 'answered'")
    resolved_faqs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM student_faqs WHERE status = 'pending'")
    pending_faqs = cursor.fetchone()[0]
    
    # Recent activity
    cursor.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM student_faqs 
        WHERE created_at >= DATE('now', '-7 days')
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """)
    faq_activity = cursor.fetchall()
    
    conn.close()
    
    reports = {
        'total_students': total_students,
        'total_content': total_content,
        'resolved_faqs': resolved_faqs,
        'pending_faqs': pending_faqs,
        'faq_activity': faq_activity,
        'satisfaction_rate': 95.8,
        'response_time': '2.3 hours'
    }
    
    return render_template('cao_academic_reports.html', reports=reports)

@app.route('/cao/account-oversight')
@check_permission('oversight')
def cao_account_oversight():
    """CAO Account Oversight for Students, Teachers, and Crew Leads"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get students
    cursor.execute("""
        SELECT id, username, email, full_name, created_date, is_active
        FROM users 
        WHERE role = 'student'
        ORDER BY created_date DESC
    """)
    students = cursor.fetchall()
    
    # Get teachers
    cursor.execute("""
        SELECT id, username, email, full_name, subdivision, created_date, is_active
        FROM users 
        WHERE role = 'teacher'
        ORDER BY subdivision, created_date DESC
    """)
    teachers = cursor.fetchall()
    
    # Get crew leads
    cursor.execute("""
        SELECT id, username, email, full_name, created_date, is_active
        FROM users 
        WHERE role = 'crew_lead'
        ORDER BY created_date DESC
    """)
    crew_leads = cursor.fetchall()
    
    conn.close()
    
    return render_template('cao_account_oversight.html', 
                         students=students, 
                         teachers=teachers, 
                         crew_leads=crew_leads)

@app.route('/cao/student-support')
@check_permission('student_support')
def cao_student_support():
    """CAO Student Support Center - Complete Implementation"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # === SUPPORT STATISTICS ===
    
    # Open tickets
    cursor.execute("SELECT COUNT(*) FROM student_faqs WHERE status = 'pending'")
    open_tickets = cursor.fetchone()[0]
    
    # Resolved today
    cursor.execute("SELECT COUNT(*) FROM student_faqs WHERE status = 'answered' AND DATE(answered_at) = DATE('now')")
    resolved_today = cursor.fetchone()[0]
    
    # Total tickets
    cursor.execute("SELECT COUNT(*) FROM student_faqs")
    total_tickets = cursor.fetchone()[0]
    
    # Resolved this week
    cursor.execute("SELECT COUNT(*) FROM student_faqs WHERE status = 'answered' AND DATE(answered_at) >= DATE('now', '-7 days')")
    resolved_week = cursor.fetchone()[0]
    
    # Average response time calculation
    cursor.execute("""
        SELECT AVG(JULIANDAY(answered_at) - JULIANDAY(created_at)) * 24
        FROM student_faqs
        WHERE status = 'answered' AND answered_at IS NOT NULL
    """)
    avg_hours = cursor.fetchone()[0]
    avg_response_time = f"{avg_hours:.1f} hours" if avg_hours else "N/A"
    
    # === URGENT SUPPORT REQUESTS ===
    cursor.execute("""
        SELECT f.id, f.question, f.status, f.created_at, u.full_name, u.username, u.email,
               ROUND((JULIANDAY('now') - JULIANDAY(f.created_at)) * 24, 1) as hours_waiting
        FROM student_faqs f
        JOIN users u ON f.student_id = u.id
        WHERE f.status = 'pending'
        ORDER BY f.created_at ASC
        LIMIT 15
    """)
    urgent_requests = cursor.fetchall()
    
    # === RECENT RESOLVED TICKETS ===
    cursor.execute("""
        SELECT f.id, f.question, f.answer, f.answered_at, 
               u.full_name as student_name,
               cao.full_name as answered_by
        FROM student_faqs f
        JOIN users u ON f.student_id = u.id
        LEFT JOIN users cao ON f.answered_by = cao.id
        WHERE f.status = 'answered'
        ORDER BY f.answered_at DESC
        LIMIT 10
    """)
    recent_resolved = cursor.fetchall()
    
    # === STUDENT ACTIVITY ===
    cursor.execute("""
        SELECT u.id, u.username, u.full_name, u.email, u.created_date,
               COUNT(f.id) as total_questions,
               SUM(CASE WHEN f.status = 'pending' THEN 1 ELSE 0 END) as pending_questions,
               MAX(f.created_at) as last_question_date
        FROM users u
        LEFT JOIN student_faqs f ON u.id = f.student_id
        WHERE u.role = 'student' AND u.is_active = 1
        GROUP BY u.id
        ORDER BY pending_questions DESC, last_question_date DESC
        LIMIT 20
    """)
    active_students = cursor.fetchall()
    
    # === SUPPORT CATEGORIES ===
    cursor.execute("""
        SELECT 
            CASE 
                WHEN LOWER(question) LIKE '%video%' OR LOWER(question) LIKE '%watch%' THEN 'Video Issues'
                WHEN LOWER(question) LIKE '%login%' OR LOWER(question) LIKE '%password%' THEN 'Login Issues'
                WHEN LOWER(question) LIKE '%course%' OR LOWER(question) LIKE '%enroll%' THEN 'Course Access'
                WHEN LOWER(question) LIKE '%progress%' OR LOWER(question) LIKE '%track%' THEN 'Progress Tracking'
                WHEN LOWER(question) LIKE '%account%' OR LOWER(question) LIKE '%profile%' THEN 'Account Issues'
                ELSE 'General Support'
            END as category,
            COUNT(*) as count
        FROM student_faqs
        WHERE DATE(created_at) >= DATE('now', '-30 days')
        GROUP BY category
        ORDER BY count DESC
    """)
    support_categories = cursor.fetchall()
    
    # === PERFORMANCE METRICS ===
    cursor.execute("""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as tickets_created,
            SUM(CASE WHEN status = 'answered' THEN 1 ELSE 0 END) as tickets_resolved
        FROM student_faqs
        WHERE DATE(created_at) >= DATE('now', '-7 days')
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """)
    daily_metrics = cursor.fetchall()
    
    # === TOP SUPPORT AGENTS (CAO users who answered most) ===
    cursor.execute("""
        SELECT cao.full_name, cao.username,
               COUNT(f.id) as tickets_answered,
               AVG(JULIANDAY(f.answered_at) - JULIANDAY(f.created_at)) * 24 as avg_response_hours
        FROM student_faqs f
        JOIN users cao ON f.answered_by = cao.id
        WHERE f.status = 'answered' AND f.answered_at IS NOT NULL
        GROUP BY cao.id
        ORDER BY tickets_answered DESC
        LIMIT 5
    """)
    top_agents = cursor.fetchall()
    
    # === SATISFACTION SCORE (based on resolved tickets) ===
    resolution_rate = (resolved_week / total_tickets * 100) if total_tickets > 0 else 0
    satisfaction_score = min(5.0, 3.0 + (resolution_rate / 50))  # Scale to 3.0-5.0
    
    conn.close()
    
    support_data = {
        # Statistics
        'open_tickets': open_tickets,
        'resolved_today': resolved_today,
        'total_tickets': total_tickets,
        'resolved_week': resolved_week,
        'avg_response_time': avg_response_time,
        'satisfaction_score': round(satisfaction_score, 1),
        'resolution_rate': round(resolution_rate, 1),
        
        # Lists
        'urgent_requests': urgent_requests,
        'recent_resolved': recent_resolved,
        'active_students': active_students,
        'support_categories': support_categories,
        'daily_metrics': daily_metrics,
        'top_agents': top_agents,
        
        # Current user
        'cao_name': session.get('full_name', 'CAO Admin')
    }
    
    return render_template('cao_student_support.html', support=support_data)

@app.route('/cao/support/answer-ticket/<int:ticket_id>', methods=['POST'])
@check_permission('student_support')
def cao_answer_ticket(ticket_id):
    """Answer a student support ticket"""
    try:
        data = request.get_json()
        answer = data.get('answer', '').strip()
        
        if not answer:
            return jsonify({'success': False, 'message': 'Answer cannot be empty'})
        
        conn = sqlite3.connect('bs_nexora_educational.db')
        cursor = conn.cursor()
        
        # Update the FAQ with answer
        cursor.execute("""
            UPDATE student_faqs
            SET answer = ?, status = 'answered', answered_at = CURRENT_TIMESTAMP, answered_by = ?
            WHERE id = ?
        """, (answer, session['user_id'], ticket_id))
        
        # Get student info for notification
        cursor.execute("""
            SELECT u.full_name, u.email, f.question
            FROM student_faqs f
            JOIN users u ON f.student_id = u.id
            WHERE f.id = ?
        """, (ticket_id,))
        student_info = cursor.fetchone()
        
        conn.commit()
        conn.close()
        
        # Log action
        log_system_action(session['user_id'], 'support_ticket_answered', 
                         f'Answered support ticket #{ticket_id} for {student_info[0] if student_info else "student"}')
        
        return jsonify({
            'success': True,
            'message': f'Ticket #{ticket_id} answered successfully',
            'student_name': student_info[0] if student_info else 'Unknown'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/cao/support/close-ticket/<int:ticket_id>', methods=['POST'])
@check_permission('student_support')
def cao_close_ticket(ticket_id):
    """Close a support ticket"""
    try:
        conn = sqlite3.connect('bs_nexora_educational.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE student_faqs
            SET status = 'closed'
            WHERE id = ?
        """, (ticket_id,))
        
        conn.commit()
        conn.close()
        
        log_system_action(session['user_id'], 'support_ticket_closed', f'Closed support ticket #{ticket_id}')
        
        return jsonify({'success': True, 'message': f'Ticket #{ticket_id} closed'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/cao/support/reopen-ticket/<int:ticket_id>', methods=['POST'])
@check_permission('student_support')
def cao_reopen_ticket(ticket_id):
    """Reopen a support ticket"""
    try:
        conn = sqlite3.connect('bs_nexora_educational.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE student_faqs
            SET status = 'pending'
            WHERE id = ?
        """, (ticket_id,))
        
        conn.commit()
        conn.close()
        
        log_system_action(session['user_id'], 'support_ticket_reopened', f'Reopened support ticket #{ticket_id}')
        
        return jsonify({'success': True, 'message': f'Ticket #{ticket_id} reopened'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/cao/support/get-ticket/<int:ticket_id>')
@check_permission('student_support')
def cao_get_ticket(ticket_id):
    """Get full ticket details"""
    try:
        conn = sqlite3.connect('bs_nexora_educational.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT f.id, f.question, f.answer, f.status, f.created_at, f.answered_at,
                   u.full_name as student_name, u.email as student_email, u.username,
                   cao.full_name as answered_by_name
            FROM student_faqs f
            JOIN users u ON f.student_id = u.id
            LEFT JOIN users cao ON f.answered_by = cao.id
            WHERE f.id = ?
        """, (ticket_id,))
        
        ticket = cursor.fetchone()
        conn.close()
        
        if ticket:
            return jsonify({
                'success': True,
                'ticket': {
                    'id': ticket[0],
                    'question': ticket[1],
                    'answer': ticket[2],
                    'status': ticket[3],
                    'created_at': ticket[4],
                    'answered_at': ticket[5],
                    'student_name': ticket[6],
                    'student_email': ticket[7],
                    'student_username': ticket[8],
                    'answered_by': ticket[9]
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Ticket not found'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/cao/support/bulk-action', methods=['POST'])
@check_permission('student_support')
def cao_bulk_action():
    """Perform bulk actions on tickets"""
    try:
        data = request.get_json()
        ticket_ids = data.get('ticket_ids', [])
        action = data.get('action', '')
        
        if not ticket_ids or not action:
            return jsonify({'success': False, 'message': 'Missing ticket IDs or action'})
        
        conn = sqlite3.connect('bs_nexora_educational.db')
        cursor = conn.cursor()
        
        if action == 'close':
            cursor.executemany("UPDATE student_faqs SET status = 'closed' WHERE id = ?", 
                             [(tid,) for tid in ticket_ids])
            message = f'Closed {len(ticket_ids)} tickets'
            
        elif action == 'reopen':
            cursor.executemany("UPDATE student_faqs SET status = 'pending' WHERE id = ?", 
                             [(tid,) for tid in ticket_ids])
            message = f'Reopened {len(ticket_ids)} tickets'
            
        elif action == 'delete':
            cursor.executemany("DELETE FROM student_faqs WHERE id = ?", 
                             [(tid,) for tid in ticket_ids])
            message = f'Deleted {len(ticket_ids)} tickets'
        else:
            conn.close()
            return jsonify({'success': False, 'message': 'Invalid action'})
        
        conn.commit()
        conn.close()
        
        log_system_action(session['user_id'], f'support_bulk_{action}', 
                         f'Bulk {action} on {len(ticket_ids)} tickets')
        
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/cao/support/search', methods=['POST'])
@check_permission('student_support')
def cao_search_tickets():
    """Search support tickets"""
    try:
        data = request.get_json()
        search_query = data.get('query', '').strip()
        status_filter = data.get('status', 'all')
        
        conn = sqlite3.connect('bs_nexora_educational.db')
        cursor = conn.cursor()
        
        query = """
            SELECT f.id, f.question, f.answer, f.status, f.created_at,
                   u.full_name, u.username
            FROM student_faqs f
            JOIN users u ON f.student_id = u.id
            WHERE (f.question LIKE ? OR f.answer LIKE ? OR u.full_name LIKE ?)
        """
        params = [f'%{search_query}%', f'%{search_query}%', f'%{search_query}%']
        
        if status_filter != 'all':
            query += " AND f.status = ?"
            params.append(status_filter)
        
        query += " ORDER BY f.created_at DESC LIMIT 50"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        tickets = [{
            'id': r[0],
            'question': r[1],
            'answer': r[2],
            'status': r[3],
            'created_at': r[4],
            'student_name': r[5],
            'student_username': r[6]
        } for r in results]
        
        return jsonify({'success': True, 'tickets': tickets, 'count': len(tickets)})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# Crew Lead-specific routes
@app.route('/crew_teacher_management')
@check_permission('teacher_management')
def crew_teacher_management():
    """Enhanced teacher management for Crew Lead"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get all teachers with detailed info
    cursor.execute('''
        SELECT id, username, full_name, teacher_subdivision, created_date, is_active
        FROM users
        WHERE role = 'teacher'
        ORDER BY teacher_subdivision, full_name
    ''')
    teachers = cursor.fetchall()
    
    # Get teacher statistics
    cursor.execute('SELECT teacher_subdivision, COUNT(*) FROM users WHERE role = "teacher" GROUP BY teacher_subdivision')
    teacher_stats = cursor.fetchall()
    
    # Get teacher video uploads
    cursor.execute('''
        SELECT u.full_name, u.teacher_subdivision, COUNT(v.id) as video_count
        FROM users u
        LEFT JOIN videos v ON u.id = v.uploaded_by
        WHERE u.role = 'teacher'
        GROUP BY u.id, u.full_name, u.teacher_subdivision
        ORDER BY video_count DESC
    ''')
    teacher_activity = cursor.fetchall()
    
    conn.close()
    
    return render_template('crew_teacher_management.html', 
                         teachers=teachers, 
                         teacher_stats=teacher_stats,
                         teacher_activity=teacher_activity)

@app.route('/content_approval')
@check_permission('teacher_management')
def content_approval():
    """Content approval for Crew Lead"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get recent teacher uploads for approval
    cursor.execute('''
        SELECT v.id, v.title, v.description, v.course_category, v.subject, 
               v.upload_date, u.full_name, u.teacher_subdivision
        FROM videos v
        JOIN users u ON v.uploaded_by = u.id
        WHERE u.role = 'teacher'
        ORDER BY v.upload_date DESC
    ''')
    pending_content = cursor.fetchall()
    
    conn.close()
    
    return render_template('content_approval.html', content=pending_content)

# Enhanced Crew Lead Routes
@app.route('/crew/performance-analytics')
@check_permission('teacher_management')
def crew_performance_analytics():
    """Crew Lead Performance Analytics Dashboard"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get comprehensive teacher performance data
    cursor.execute("""
        SELECT 
            u.full_name,
            u.subdivision,
            COUNT(v.id) as total_videos,
            0 as avg_video_size,
            MAX(v.upload_date) as last_upload
        FROM users u
        LEFT JOIN videos v ON u.id = v.uploaded_by
        WHERE u.role = 'teacher'
        GROUP BY u.id, u.full_name, u.subdivision
        ORDER BY total_videos DESC
    """)
    teacher_performance = cursor.fetchall()
    
    # Get subdivision statistics
    cursor.execute("""
        SELECT 
            subdivision,
            COUNT(*) as teacher_count,
            SUM(CASE WHEN created_date >= DATE('now', '-7 days') THEN 1 ELSE 0 END) as active_teachers
        FROM users 
        WHERE role = 'teacher'
        GROUP BY subdivision
    """)
    subdivision_stats = cursor.fetchall()
    
    conn.close()
    
    return render_template('crew_performance_analytics.html',
                         teacher_performance=teacher_performance,
                         subdivision_stats=subdivision_stats)

@app.route('/crew/content-management')
@check_permission('course_management')
def crew_content_management():
    """Crew Lead Content Management System"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get all content by subdivision
    cursor.execute("""
        SELECT v.id, v.title, v.subject, v.course_category, v.upload_date, 
               u.full_name, u.subdivision, v.status
        FROM videos v
        JOIN users u ON v.uploaded_by = u.id
        WHERE u.role = 'teacher'
        ORDER BY v.upload_date DESC
    """)
    all_content = cursor.fetchall()
    
    conn.close()
    
    return render_template('crew_content_management.html', content=all_content)

# Teacher Subdivision-Specific Routes
@app.route('/teacher/python-classes-tools')
@check_permission('upload_videos')
def teacher_python_classes_tools():
    """Python Classes Teacher Specialized Tools"""
    if session.get('subdivision') != 'Python Classes':
        flash('Access denied. Python Classes teachers only.', 'error')
        return redirect(url_for('dashboard'))
    
    # Python-specific tools and resources
    python_tools = {
        'environments': ['VS Code Setup', 'PyCharm Configuration', 'Jupyter Notebooks'],
        'resources': ['Code Templates', 'Practice Projects', 'Debugging Tools'],
        'lesson_types': ['Basic Syntax', 'Data Structures', 'OOP', 'Web Development', 'Data Science']
    }
    
    return render_template('teacher_python_classes_tools.html', tools=python_tools)

@app.route('/teacher/prompt-engineering-tools')
@check_permission('upload_videos')
def teacher_prompt_engineering_tools():
    """Prompt Engineering Teacher Specialized Tools"""
    if session.get('subdivision') != 'Prompt Engineering':
        flash('Access denied. Prompt Engineering teachers only.', 'error')
        return redirect(url_for('dashboard'))
    
    # Prompt Engineering-specific tools and resources
    prompt_tools = {
        'platforms': ['ChatGPT', 'Claude', 'Gemini', 'Custom APIs'],
        'resources': ['Prompt Templates', 'Best Practices', 'Testing Tools'],
        'lesson_types': ['Basic Prompting', 'Advanced Techniques', 'Chain of Thought', 'Few-shot Learning']
    }
    
    return render_template('teacher_prompt_engineering_tools.html', tools=prompt_tools)

@app.route('/teacher/ai-editing-tools')
@check_permission('upload_videos')
def teacher_ai_editing_tools():
    """AI Editing and Content Creation Teacher Tools"""
    if session.get('subdivision') != 'AI Editing and Content Creation':
        flash('Access denied. AI Editing and Content Creation teachers only.', 'error')
        return redirect(url_for('dashboard'))
    
    # AI Editing-specific tools and resources
    ai_tools = {
        'platforms': ['Adobe AI', 'Canva AI', 'Midjourney', 'DALL-E', 'Runway ML'],
        'resources': ['Content Templates', 'Style Guides', 'Workflow Automation'],
        'lesson_types': ['Image Generation', 'Video Editing', 'Content Writing', 'Design Automation']
    }
    
    return render_template('teacher_ai_editing_tools.html', tools=ai_tools)

@app.route('/teacher/windows-creation-tools')
@check_permission('upload_videos')
def teacher_windows_creation_tools():
    """Professional Windows Creation Teacher Tools"""
    if session.get('subdivision') != 'Professional Windows Creation':
        flash('Access denied. Professional Windows Creation teachers only.', 'error')
        return redirect(url_for('dashboard'))
    
    # Windows Creation-specific tools and resources
    windows_tools = {
        'development': ['Visual Studio', 'WPF', 'WinUI 3', 'Windows Forms'],
        'resources': ['UI Templates', 'Design Patterns', 'Deployment Guides'],
        'lesson_types': ['Desktop Apps', 'Modern UI', 'System Integration', 'Performance Optimization']
    }
    
    return render_template('teacher_windows_creation_tools.html', tools=windows_tools)

@app.route('/teacher/app-development-tools')
@check_permission('upload_videos')
def teacher_app_development_tools():
    """App Development Teacher Tools"""
    if session.get('subdivision') != 'App Development':
        flash('Access denied. App Development teachers only.', 'error')
        return redirect(url_for('dashboard'))
    
    # App Development-specific tools and resources
    app_tools = {
        'platforms': ['React Native', 'Flutter', 'Xamarin', 'Native iOS/Android'],
        'resources': ['Code Templates', 'UI Kits', 'Testing Frameworks'],
        'lesson_types': ['Mobile UI/UX', 'API Integration', 'Database Design', 'App Store Deployment']
    }
    
    return render_template('teacher_app_development_tools.html', tools=app_tools)

@app.route('/teacher/youtube-channel-tools')
@check_permission('upload_videos')
def teacher_youtube_channel_tools():
    """YouTube Channel Creation Teacher Tools"""
    if session.get('subdivision') != 'Creating Professional YouTube Channel':
        flash('Access denied. YouTube Channel Creation teachers only.', 'error')
        return redirect(url_for('dashboard'))
    
    # YouTube-specific tools and resources
    youtube_tools = {
        'creation': ['Channel Setup', 'Branding Tools', 'Thumbnail Creators', 'Video Editors'],
        'resources': ['Content Planning', 'SEO Optimization', 'Analytics Tools'],
        'lesson_types': ['Channel Strategy', 'Content Creation', 'Monetization', 'Audience Growth']
    }
    
    return render_template('teacher_youtube_channel_tools.html', tools=youtube_tools)

@app.route('/teacher/machine-learning-tools')
@check_permission('upload_videos')
def teacher_machine_learning_tools():
    """Machine Learning Teacher Tools"""
    if session.get('subdivision') != 'Machine Learning':
        flash('Access denied. Machine Learning teachers only.', 'error')
        return redirect(url_for('dashboard'))
    
    # Machine Learning-specific tools and resources
    ml_tools = {
        'platforms': ['TensorFlow', 'PyTorch', 'Scikit-learn', 'Keras', 'Jupyter'],
        'resources': ['Dataset Libraries', 'Model Templates', 'Visualization Tools'],
        'lesson_types': ['Supervised Learning', 'Deep Learning', 'NLP', 'Computer Vision', 'MLOps']
    }
    
    return render_template('teacher_machine_learning_tools.html', tools=ml_tools)

@app.route('/teacher/cyber-security-tools')
@check_permission('upload_videos')
def teacher_cyber_security_tools():
    """Cyber Security Teacher Tools"""
    if session.get('subdivision') != 'Cyber Security':
        flash('Access denied. Cyber Security teachers only.', 'error')
        return redirect(url_for('dashboard'))
    
    # Cyber Security-specific tools and resources
    security_tools = {
        'platforms': ['Kali Linux', 'Wireshark', 'Metasploit', 'Burp Suite', 'Nmap'],
        'resources': ['Security Frameworks', 'Vulnerability Databases', 'Compliance Guides'],
        'lesson_types': ['Ethical Hacking', 'Network Security', 'Incident Response', 'Risk Assessment']
    }
    
    return render_template('teacher_cyber_security_tools.html', tools=security_tools)

@app.route('/teacher/power-bi-tools')
@check_permission('upload_videos')
def teacher_power_bi_tools():
    """Power BI Teacher Tools"""
    if session.get('subdivision') != 'Power BI':
        flash('Access denied. Power BI teachers only.', 'error')
        return redirect(url_for('dashboard'))
    
    # Power BI-specific tools and resources
    powerbi_tools = {
        'platforms': ['Power BI Desktop', 'Power BI Service', 'Power Query', 'DAX Studio'],
        'resources': ['Dashboard Templates', 'Data Connectors', 'Best Practices'],
        'lesson_types': ['Data Modeling', 'Visualization', 'DAX Functions', 'Report Deployment']
    }
    
    return render_template('teacher_power_bi_tools.html', tools=powerbi_tools)

@app.route('/teacher/advanced-excel-tools')
@check_permission('upload_videos')
def teacher_advanced_excel_tools():
    """Advanced Excel Teacher Tools"""
    if session.get('subdivision') != 'Advanced Excel':
        flash('Access denied. Advanced Excel teachers only.', 'error')
        return redirect(url_for('dashboard'))
    
    # Advanced Excel-specific tools and resources
    excel_tools = {
        'features': ['Power Query', 'Power Pivot', 'VBA Macros', 'Advanced Formulas'],
        'resources': ['Template Library', 'Function References', 'Automation Scripts'],
        'lesson_types': ['Data Analysis', 'Financial Modeling', 'Dashboard Creation', 'Process Automation']
    }
    
    return render_template('teacher_advanced_excel_tools.html', tools=excel_tools)

# Enhanced CTO Development Routes
@app.route('/cto/system-monitoring')
@check_permission('system_access')
def cto_system_monitoring():
    """CTO System Monitoring Dashboard"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get system health metrics
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM videos")
    total_videos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM chat_messages WHERE created_at >= DATE('now', '-24 hours')")
    daily_messages = cursor.fetchone()[0]
    
    # Get database size
    cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
    db_size = cursor.fetchone()[0] if cursor.fetchone() else 0
    
    system_metrics = {
        'total_users': total_users,
        'total_videos': total_videos,
        'daily_messages': daily_messages,
        'database_size': db_size,
        'uptime': '99.9%',
        'server_status': 'Healthy'
    }
    
    conn.close()
    
    return render_template('cto_system_monitoring.html', metrics=system_metrics)

@app.route('/cto/database-management')
@check_permission('system_access')
def cto_database_management():
    """CTO Database Management Interface"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get table information
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    table_info = []
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        table_info.append({'name': table_name, 'rows': row_count})
    
    conn.close()
    
    return render_template('cto_database_management.html', tables=table_info)

# CTO Layout Management Routes
@app.route('/cto/layout-manager')
@check_permission('widgets')  # CTO permission
def cto_layout_manager():
    """CTO Layout Management Interface"""
    import json
    from pathlib import Path
    
    # Get available layouts
    layouts = []
    custom_layouts_dir = Path('custom_layouts')
    layout_backups_dir = Path('layout_backups')
    
    # Predefined layouts
    predefined_layouts = [
        {
            'id': 'default',
            'name': "B's Nexora Default",
            'description': 'Original B\'s Nexora educational platform layout',
            'type': 'predefined',
            'theme_color': '#1a4d3a',
            'has_sidebar': True,
            'is_current': True  # Default as current
        },
        {
            'id': 'modern',
            'name': 'Modern Educational',
            'description': 'Clean, modern layout with card-based design',
            'type': 'predefined',
            'theme_color': '#0066cc',
            'has_sidebar': False,
            'is_current': False
        },
        {
            'id': 'corporate',
            'name': 'Corporate Professional',
            'description': 'Professional corporate-style layout',
            'type': 'predefined',
            'theme_color': '#2c3e50',
            'has_sidebar': True,
            'is_current': False
        },
        {
            'id': 'minimalist',
            'name': 'Minimalist Clean',
            'description': 'Ultra-clean minimalist design',
            'type': 'predefined',
            'theme_color': '#000000',
            'has_sidebar': False,
            'is_current': False
        }
    ]
    
    layouts.extend(predefined_layouts)
    
    # Custom layouts
    custom_layouts = []
    if custom_layouts_dir.exists():
        for layout_dir in custom_layouts_dir.iterdir():
            if layout_dir.is_dir():
                config_file = layout_dir / 'config.json'
                if config_file.exists():
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        custom_layout = {
                            'id': layout_dir.name,
                            'name': config.get('name', layout_dir.name),
                            'description': config.get('description', 'Custom layout'),
                            'type': 'custom',
                            'theme_color': '#8a2be2',
                            'has_sidebar': True,
                            'is_current': False,
                            'created_at': config.get('created_at', 'Unknown')
                        }
                        layouts.append(custom_layout)
                        custom_layouts.append(custom_layout)
                    except:
                        pass
    
    # Get backups
    backups = []
    if layout_backups_dir.exists():
        for backup_dir in layout_backups_dir.iterdir():
            if backup_dir.is_dir():
                backups.append({
                    'name': backup_dir.name,
                    'created_at': backup_dir.stat().st_mtime,
                    'size': sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
                })
    
    return render_template('cto_layout_manager.html', 
                         layouts=layouts,
                         custom_layouts=custom_layouts,
                         backups=backups,
                         current_layout={'name': 'Default'})

@app.route('/cto/create-layout', methods=['POST'])
@check_permission('widgets')
def cto_create_layout():
    """Create a new custom layout"""
    import json
    from pathlib import Path
    import time
    
    try:
        data = request.get_json()
        layout_name = data.get('name', '').strip()
        layout_description = data.get('description', '').strip()
        html_code = data.get('html_code', '').strip()
        css_code = data.get('css_code', '').strip()
        js_code = data.get('js_code', '').strip()
        
        if not layout_name or not html_code:
            return {'success': False, 'error': 'Layout name and HTML code are required'}
        
        # Create custom layouts directory
        custom_layouts_dir = Path('custom_layouts')
        custom_layouts_dir.mkdir(exist_ok=True)
        
        # Create layout directory
        layout_dir = custom_layouts_dir / layout_name.replace(' ', '_').lower()
        layout_dir.mkdir(exist_ok=True)
        
        # Save HTML file
        html_file = layout_dir / 'index.html'
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_code)
        
        # Save CSS file if provided
        css_file = None
        if css_code:
            css_file = layout_dir / 'styles.css'
            with open(css_file, 'w', encoding='utf-8') as f:
                f.write(css_code)
        
        # Save JS file if provided
        js_file = None
        if js_code:
            js_file = layout_dir / 'script.js'
            with open(js_file, 'w', encoding='utf-8') as f:
                f.write(js_code)
        
        # Create configuration file
        config = {
            'name': layout_name,
            'description': layout_description,
            'created_by': 'CTO',
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'html_file': str(html_file),
            'css_file': str(css_file) if css_file else None,
            'js_file': str(js_file) if js_file else None,
            'custom': True
        }
        
        config_file = layout_dir / 'config.json'
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        return jsonify({'success': True, 'message': f'Layout "{layout_name}" created successfully!'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/cto/apply-layout', methods=['POST'])
@check_permission('widgets')
def cto_apply_layout():
    """Apply a layout to the entire web application"""
    import json
    import shutil
    from pathlib import Path
    import time
    
    try:
        data = request.get_json()
        layout_id = data.get('layout_id')
        
        if not layout_id:
            return jsonify({'success': False, 'error': 'Layout ID is required'})
        
        # Create backup first
        backup_result = create_layout_backup()
        if not backup_result['success']:
            return jsonify({'success': False, 'error': 'Failed to create backup: ' + backup_result['error']})
        
        # Apply the layout
        templates_dir = Path('templates')
        static_dir = Path('static')
        custom_layouts_dir = Path('custom_layouts')
        
        if layout_id in ['default', 'modern', 'corporate', 'minimalist']:
            # Apply predefined layout
            apply_predefined_layout(layout_id, templates_dir, static_dir)
        else:
            # Apply custom layout
            layout_path = custom_layouts_dir / layout_id
            if not layout_path.exists():
                return jsonify({'success': False, 'error': 'Custom layout not found'})
            
            apply_custom_layout(layout_path, templates_dir, static_dir)
        
        return jsonify({'success': True, 'message': f'Layout "{layout_id}" applied successfully!'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/cto/delete-layout', methods=['POST'])
@check_permission('widgets')
def cto_delete_layout():
    """Delete a custom layout"""
    import shutil
    from pathlib import Path
    
    try:
        data = request.get_json()
        layout_id = data.get('layout_id')
        
        if not layout_id:
            return jsonify({'success': False, 'error': 'Layout ID is required'})
        
        # Don't allow deletion of predefined layouts
        if layout_id in ['default', 'modern', 'corporate', 'minimalist']:
            return jsonify({'success': False, 'error': 'Cannot delete predefined layouts'})
        
        # Delete custom layout
        custom_layouts_dir = Path('custom_layouts')
        layout_path = custom_layouts_dir / layout_id
        
        if not layout_path.exists():
            return jsonify({'success': False, 'error': 'Layout not found'})
        
        shutil.rmtree(layout_path)
        
        return jsonify({'success': True, 'message': f'Layout "{layout_id}" deleted successfully!'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/cto/backup-layout', methods=['POST'])
@check_permission('widgets')
def cto_backup_layout():
    """Create a backup of the current layout"""
    try:
        result = create_layout_backup()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/cto/restore-layout', methods=['POST'])
@check_permission('widgets')
def cto_restore_layout():
    """Restore a layout from backup"""
    import shutil
    from pathlib import Path
    
    try:
        data = request.get_json()
        backup_name = data.get('backup_name')
        
        if not backup_name:
            return jsonify({'success': False, 'error': 'Backup name is required'})
        
        backup_dir = Path('layout_backups') / backup_name
        if not backup_dir.exists():
            return jsonify({'success': False, 'error': 'Backup not found'})
        
        templates_dir = Path('templates')
        static_dir = Path('static')
        
        # Restore templates
        templates_backup = backup_dir / 'templates'
        if templates_backup.exists():
            if templates_dir.exists():
                shutil.rmtree(templates_dir)
            shutil.copytree(templates_backup, templates_dir)
        
        # Restore static files
        static_backup = backup_dir / 'static'
        if static_backup.exists():
            if static_dir.exists():
                shutil.rmtree(static_dir)
            shutil.copytree(static_backup, static_dir)
        
        return jsonify({'success': True, 'message': f'Layout restored from backup "{backup_name}"!'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def create_layout_backup():
    """Helper function to create layout backup"""
    import shutil
    import time
    from pathlib import Path
    
    try:
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        backup_name = f'backup_{timestamp}'
        backup_dir = Path('layout_backups') / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        templates_dir = Path('templates')
        static_dir = Path('static')
        
        # Backup templates
        if templates_dir.exists():
            shutil.copytree(templates_dir, backup_dir / 'templates', dirs_exist_ok=True)
        
        # Backup static files
        if static_dir.exists():
            shutil.copytree(static_dir, backup_dir / 'static', dirs_exist_ok=True)
        
        return {'success': True, 'backup_name': backup_name}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def apply_predefined_layout(layout_id, templates_dir, static_dir):
    """Apply a predefined layout"""
    # This would generate templates and CSS based on the predefined layout
    # For now, we'll just update the base template with theme colors
    
    theme_colors = {
        'default': {'primary': '#1a4d3a', 'secondary': '#2d7a5f'},
        'modern': {'primary': '#0066cc', 'secondary': '#4da6ff'},
        'corporate': {'primary': '#2c3e50', 'secondary': '#34495e'},
        'minimalist': {'primary': '#000000', 'secondary': '#333333'}
    }
    
    colors = theme_colors.get(layout_id, theme_colors['default'])
    
    # Update CSS variables in base template or create custom CSS
    css_dir = static_dir / 'css'
    css_dir.mkdir(parents=True, exist_ok=True)
    
    custom_css = f"""
/* CTO Applied Layout: {layout_id} */
:root {{
    --primary-color: {colors['primary']};
    --secondary-color: {colors['secondary']};
}}

body {{
    --accent-green: {colors['primary']};
    --accent-teal: {colors['secondary']};
}}
"""
    
    with open(css_dir / 'cto_layout.css', 'w') as f:
        f.write(custom_css)

def apply_custom_layout(layout_path, templates_dir, static_dir):
    """Apply a custom layout"""
    import json
    import shutil
    
    config_file = layout_path / 'config.json'
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Copy HTML file to templates
        if config.get('html_file'):
            html_file = Path(config['html_file'])
            if html_file.exists():
                shutil.copy2(html_file, templates_dir / 'custom_layout.html')
        
        # Copy CSS file to static
        if config.get('css_file'):
            css_file = Path(config['css_file'])
            if css_file.exists():
                css_dir = static_dir / 'css'
                css_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(css_file, css_dir / 'cto_layout.css')
        
        # Copy JS file to static
        if config.get('js_file'):
            js_file = Path(config['js_file'])
            if js_file.exists():
                js_dir = static_dir / 'js'
                js_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(js_file, js_dir / 'cto_layout.js')

# BULLETPROOF CTO TEST ROUTE
@app.route('/cto/test-access')
@check_permission('widgets')
def cto_test_access():
    """Test route to verify CTO access is working"""
    return jsonify({
        'success': True, 
        'message': '🎉 CTO ACCESS IS 100% FUNCTIONAL!',
        'user': session.get('username'),
        'role': session.get('role'),
        'timestamp': datetime.now().isoformat()
    })

# COMPREHENSIVE CHAT SYSTEM - ALL 7 ACCOUNTS
@app.route('/chat')
@check_permission('chat')
def chat_main():
    """Main chat interface for all account types"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get all users for chat (except current user)
    cursor.execute('''
        SELECT id, username, full_name, role 
        FROM users 
        WHERE id != ? AND is_active = 1
        ORDER BY role, full_name
    ''', (session['user_id'],))
    available_users = cursor.fetchall()
    
    # Get recent conversations
    cursor.execute('''
        SELECT DISTINCT 
            CASE 
                WHEN c.user1_id = ? THEN c.user2_id 
                ELSE c.user1_id 
            END as other_user_id,
            u.username, u.full_name, u.role,
            m.message, m.created_at, m.is_read,
            (SELECT COUNT(*) FROM chat_messages 
             WHERE receiver_id = ? AND sender_id = CASE WHEN c.user1_id = ? THEN c.user2_id ELSE c.user1_id END AND is_read = 0) as unread_count
        FROM chat_conversations c
        JOIN users u ON u.id = CASE WHEN c.user1_id = ? THEN c.user2_id ELSE c.user1_id END
        LEFT JOIN chat_messages m ON m.id = c.last_message_id
        WHERE c.user1_id = ? OR c.user2_id = ?
        ORDER BY c.last_activity DESC
        LIMIT 10
    ''', (session['user_id'], session['user_id'], session['user_id'], session['user_id'], session['user_id'], session['user_id']))
    recent_conversations = cursor.fetchall()
    
    conn.close()
    
    return render_template('chat_main.html', 
                         available_users=available_users,
                         recent_conversations=recent_conversations,
                         current_user_role=session.get('role'))

@app.route('/chat/conversation/<int:user_id>')
@check_permission('chat')
def chat_conversation(user_id):
    """View conversation with specific user"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get other user info
    cursor.execute('SELECT username, full_name, role FROM users WHERE id = ?', (user_id,))
    other_user = cursor.fetchone()
    
    if not other_user:
        flash('User not found', 'error')
        return redirect(url_for('chat_main'))
    
    # Get conversation messages
    cursor.execute('''
        SELECT m.id, m.sender_id, m.message, m.created_at, m.is_read,
               u.username, u.full_name
        FROM chat_messages m
        JOIN users u ON u.id = m.sender_id
        WHERE (m.sender_id = ? AND m.receiver_id = ?) 
           OR (m.sender_id = ? AND m.receiver_id = ?)
        AND m.is_deleted = 0
        ORDER BY m.created_at ASC
    ''', (session['user_id'], user_id, user_id, session['user_id']))
    messages = cursor.fetchall()
    
    # Mark messages as read
    cursor.execute('''
        UPDATE chat_messages 
        SET is_read = 1, read_at = CURRENT_TIMESTAMP
        WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
    ''', (user_id, session['user_id']))
    conn.commit()
    conn.close()
    
    return render_template('chat_conversation.html',
                         other_user=other_user,
                         messages=messages,
                         current_user_id=session['user_id'])

@app.route('/chat/send', methods=['POST'])
@check_permission('chat')
def chat_send_message():
    """Send a private message"""
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    message = data.get('message', '').strip()
    
    if not receiver_id or not message:
        return jsonify({'success': False, 'error': 'Missing receiver or message'})
    
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Verify receiver exists
    cursor.execute('SELECT id FROM users WHERE id = ? AND is_active = 1', (receiver_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': 'Invalid receiver'})
    
    # Insert message
    cursor.execute('''
        INSERT INTO chat_messages (sender_id, receiver_id, message)
        VALUES (?, ?, ?)
    ''', (session['user_id'], receiver_id, message))
    message_id = cursor.lastrowid
    
    # Update or create conversation
    cursor.execute('''
        INSERT OR REPLACE INTO chat_conversations 
        (user1_id, user2_id, last_message_id, last_activity)
        VALUES (
            MIN(?, ?), MAX(?, ?), ?, CURRENT_TIMESTAMP
        )
    ''', (session['user_id'], receiver_id, session['user_id'], receiver_id, message_id))
    
    conn.commit()
    conn.close()
    
    # Log the message for CTO oversight
    log_system_action(session['user_id'], 'chat_message_sent', f'Message sent to user {receiver_id}')
    
    return jsonify({'success': True, 'message_id': message_id})

@app.route('/chat/messages/<int:user_id>')
@check_permission('chat')
def chat_get_messages(user_id):
    """Get messages with specific user (AJAX)"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT m.id, m.sender_id, m.message, m.created_at, m.is_read,
               u.username, u.full_name
        FROM chat_messages m
        JOIN users u ON u.id = m.sender_id
        WHERE (m.sender_id = ? AND m.receiver_id = ?) 
           OR (m.sender_id = ? AND m.receiver_id = ?)
        AND m.is_deleted = 0
        ORDER BY m.created_at ASC
    ''', (session['user_id'], user_id, user_id, session['user_id']))
    messages = cursor.fetchall()
    
    # Mark as read
    cursor.execute('''
        UPDATE chat_messages 
        SET is_read = 1, read_at = CURRENT_TIMESTAMP
        WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
    ''', (user_id, session['user_id']))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'messages': [{
            'id': msg[0],
            'sender_id': msg[1],
            'message': msg[2],
            'created_at': msg[3],
            'is_read': msg[4],
            'sender_username': msg[5],
            'sender_name': msg[6]
        } for msg in messages]
    })

# CTO CHAT OVERSIGHT - READ ALL PRIVATE MESSAGES
@app.route('/cto/chat-oversight')
@check_permission('chat_admin')
def cto_chat_oversight():
    """CTO can read all private messages for oversight"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get all conversations with message counts
    cursor.execute('''
        SELECT 
            u1.username as user1_name, u1.full_name as user1_full, u1.role as user1_role,
            u2.username as user2_name, u2.full_name as user2_full, u2.role as user2_role,
            COUNT(m.id) as message_count,
            MAX(m.created_at) as last_message_time,
            c.id as conversation_id
        FROM chat_conversations c
        JOIN users u1 ON u1.id = c.user1_id
        JOIN users u2 ON u2.id = c.user2_id
        LEFT JOIN chat_messages m ON (m.sender_id = c.user1_id AND m.receiver_id = c.user2_id) 
                                  OR (m.sender_id = c.user2_id AND m.receiver_id = c.user1_id)
        GROUP BY c.id, u1.id, u2.id
        ORDER BY last_message_time DESC
    ''')
    conversations = cursor.fetchall()
    
    # Get recent messages across all conversations
    cursor.execute('''
        SELECT m.id, m.sender_id, m.receiver_id, m.message, m.created_at,
               s.username as sender_name, s.full_name as sender_full, s.role as sender_role,
               r.username as receiver_name, r.full_name as receiver_full, r.role as receiver_role
        FROM chat_messages m
        JOIN users s ON s.id = m.sender_id
        JOIN users r ON r.id = m.receiver_id
        WHERE m.is_deleted = 0
        ORDER BY m.created_at DESC
        LIMIT 100
    ''')
    recent_messages = cursor.fetchall()
    
    conn.close()
    
    return render_template('cto_chat_oversight.html',
                         conversations=conversations,
                         recent_messages=recent_messages)

@app.route('/cto/chat-conversation/<int:user1_id>/<int:user2_id>')
@check_permission('chat_admin')
def cto_view_conversation(user1_id, user2_id):
    """CTO can view any private conversation"""
    conn = sqlite3.connect('bs_nexora_educational.db')
    cursor = conn.cursor()
    
    # Get user info
    cursor.execute('SELECT username, full_name, role FROM users WHERE id IN (?, ?)', (user1_id, user2_id))
    users = cursor.fetchall()
    
    # Get all messages between these users
    cursor.execute('''
        SELECT m.id, m.sender_id, m.receiver_id, m.message, m.created_at, m.is_read,
               s.username as sender_name, s.full_name as sender_full,
               r.username as receiver_name, r.full_name as receiver_full
        FROM chat_messages m
        JOIN users s ON s.id = m.sender_id
        JOIN users r ON r.id = m.receiver_id
        WHERE (m.sender_id = ? AND m.receiver_id = ?) 
           OR (m.sender_id = ? AND m.receiver_id = ?)
        AND m.is_deleted = 0
        ORDER BY m.created_at ASC
    ''', (user1_id, user2_id, user2_id, user1_id))
    messages = cursor.fetchall()
    
    conn.close()
    
    return render_template('cto_conversation_view.html',
                         users=users,
                         messages=messages,
                         user1_id=user1_id,
                         user2_id=user2_id)

# ============================================================================
# CLOUD SYNC ROUTES - Real-time synchronization between multiple installations
# ============================================================================

@app.route('/cloud_sync_setup')
@check_permission('system_access')  # CTO only
def cloud_sync_setup():
    """Cloud sync setup page"""
    return render_template('cloud_sync_setup.html')

@app.route('/configure_cloud_sync', methods=['POST'])
@check_permission('system_access')  # CTO only
def configure_cloud_sync():
    """Configure cloud synchronization"""
    if not CLOUD_SYNC_AVAILABLE:
        flash('Cloud sync system not available', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        github_token = request.form.get('github_token', '').strip()
        github_owner = request.form.get('github_owner', '').strip()
        github_repo = request.form.get('github_repo', '').strip()
        
        if not all([github_token, github_owner, github_repo]):
            flash('All fields are required for cloud sync configuration', 'error')
            return redirect(url_for('cloud_sync_setup'))
        
        # Configure cloud sync
        if sync_manager.configure_cloud_sync(github_token, github_owner, github_repo):
            flash('Cloud sync configured successfully!', 'success')
            
            # Start real-time sync if requested
            if request.form.get('start_sync') == 'on':
                if sync_manager.start_real_time_sync():
                    flash('Real-time sync started! Videos will now sync automatically.', 'success')
                else:
                    flash('Cloud sync configured but failed to start real-time sync', 'warning')
        else:
            flash('Failed to configure cloud sync. Check your credentials.', 'error')
            
    except Exception as e:
        flash(f'Cloud sync configuration error: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/sync_status')
@check_permission('system_access')  # CTO only
def sync_status():
    """View cloud sync status"""
    if not CLOUD_SYNC_AVAILABLE:
        flash('Cloud sync system not available', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if sync is configured
    sync_configured = sync_manager.load_sync_config()
    
    # Get sync statistics
    sync_stats = {
        'configured': sync_configured,
        'active': sync_manager.is_syncing,
        'last_sync': 'Never' if not sync_configured else 'Recently'
    }
    
    return render_template('sync_status.html', sync_stats=sync_stats)

@app.route('/manual_sync', methods=['POST'])
@check_permission('system_access')  # CTO only
def manual_sync():
    """Trigger manual synchronization"""
    if not CLOUD_SYNC_AVAILABLE:
        flash('Cloud sync system not available', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        if sync_manager.manual_sync():
            flash('Manual sync completed successfully!', 'success')
        else:
            flash('Manual sync failed. Check cloud sync configuration.', 'error')
    except Exception as e:
        flash(f'Manual sync error: {str(e)}', 'error')
    
    return redirect(url_for('sync_status'))

@app.route('/start_sync', methods=['POST'])
@check_permission('system_access')  # CTO only
def start_sync():
    """Start real-time synchronization"""
    if not CLOUD_SYNC_AVAILABLE:
        flash('Cloud sync system not available', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        if sync_manager.start_real_time_sync():
            flash('Real-time sync started successfully!', 'success')
        else:
            flash('Failed to start real-time sync. Check configuration.', 'error')
    except Exception as e:
        flash(f'Start sync error: {str(e)}', 'error')
    
    return redirect(url_for('sync_status'))

@app.route('/stop_sync', methods=['POST'])
@check_permission('system_access')  # CTO only
def stop_sync():
    """Stop real-time synchronization"""
    if not CLOUD_SYNC_AVAILABLE:
        flash('Cloud sync system not available', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        sync_manager.stop_real_time_sync()
        flash('Real-time sync stopped', 'info')
    except Exception as e:
        flash(f'Stop sync error: {str(e)}', 'error')
    
    return redirect(url_for('sync_status'))

@app.route('/google_drive_setup')
@check_permission('system_access')  # CTO only
def google_drive_setup():
    """Google Drive setup page for large file sync"""
    return render_template('google_drive_setup.html')

@app.route('/configure_google_drive', methods=['POST'])
@check_permission('system_access')  # CTO only
def configure_google_drive():
    """Configure Google Drive for large file sync"""
    if not CLOUD_SYNC_AVAILABLE:
        flash('Cloud sync system not available', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Check if credentials file was uploaded
        if 'credentials_file' not in request.files:
            flash('Please upload Google Drive credentials.json file', 'error')
            return redirect(url_for('google_drive_setup'))
        
        file = request.files['credentials_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('google_drive_setup'))
        
        if file and file.filename.endswith('.json'):
            # Save credentials file
            credentials_path = 'google_drive_credentials.json'
            file.save(credentials_path)
            
            # Setup Google Drive
            if sync_manager.google_drive and sync_manager.google_drive.setup_google_drive(credentials_path):
                flash('Google Drive configured successfully! Large files (>100MB) will now sync via Google Drive.', 'success')
            else:
                flash('Failed to configure Google Drive. Please check your credentials file.', 'error')
        else:
            flash('Please upload a valid .json credentials file', 'error')
            
    except Exception as e:
        flash(f'Google Drive configuration error: {str(e)}', 'error')
    
    return redirect(url_for('sync_status'))

@app.route('/google_drive_status')
@check_permission('system_access')  # CTO only
def google_drive_status():
    """Check Google Drive integration status"""
    if not CLOUD_SYNC_AVAILABLE:
        return jsonify({'available': False, 'error': 'Cloud sync not available'})
    
    try:
        status = {
            'available': sync_manager.google_drive is not None,
            'configured': False,
            'files': []
        }
        
        if sync_manager.google_drive and sync_manager.google_drive.service:
            status['configured'] = True
            status['files'] = sync_manager.google_drive.list_drive_files()
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'available': False, 'error': str(e)})

# ============================================
# FACE ID AUTHENTICATION ROUTES
# ============================================

@app.route('/face_id_lock_screen')
def face_id_lock_screen():
    """Face ID lock screen - Always shown on app open"""
    if not FACE_ID_AVAILABLE:
        flash('Face ID system not available.', 'error')
        return redirect(url_for('login'))
    
    # Check if user is already authenticated in this session
    if session.get('face_id_authenticated'):
        # Already authenticated, go to dashboard
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        else:
            # Try to restore session
            if restore_session_if_exists():
                return redirect(url_for('dashboard'))
    
    return render_template('face_id_auto_login_round.html', lock_screen=True)

@app.route('/face_id_login', methods=['GET', 'POST'])
def face_id_login():
    """Face ID login page"""
    if not FACE_ID_AVAILABLE:
        flash('Face ID system not available. Please install face_recognition library.', 'error')
        return redirect(url_for('login'))
    
    return render_template('face_id_login.html')

@app.route('/api/face_id/authenticate', methods=['POST'])
def api_face_id_authenticate():
    """API endpoint for Face ID authentication"""
    if not FACE_ID_AVAILABLE:
        return jsonify({'success': False, 'message': 'Face ID system not available'})
    
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'message': 'No image data provided'})
        
        # Authenticate face
        result = face_id_system.authenticate_face(image_data, is_base64=True)
        
        if result['success']:
            username = result['username']
            is_master = result['is_master']
            
            # Get user from database
            conn = sqlite3.connect('bs_nexora_educational.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, role, email, full_name, subdivision
                FROM users WHERE username = ? AND is_active = 1
            ''', (username,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                # Create session
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['role'] = user[2]
                session['email'] = user[3]
                session['full_name'] = user[4]
                session['subdivision'] = user[5]
                session['face_id_login'] = True
                session['face_id_authenticated'] = True
                session['is_master_face'] = is_master
                
                # Save session (legacy)
                save_session_to_file(session)
                
                # Save universal session for auto-login
                save_universal_session({
                    'user_id': user[0],
                    'username': username,
                    'role': user[2],
                    'full_name': user[4],
                    'email': user[3]
                })
                
                # Log action
                log_system_action(user[0], 'face_id_login', 
                                f'Face ID login successful for {username}')
                
                return jsonify({
                    'success': True,
                    'message': f'Welcome, {user[4] or username}!',
                    'username': username,
                    'role': user[2],
                    'is_master': is_master,
                    'redirect': url_for('dashboard')
                })
            else:
                return jsonify({'success': False, 'message': 'User account not found'})
        else:
            return jsonify(result)
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Authentication error: {str(e)}'})

@app.route('/api/face_id/register', methods=['POST'])
def api_face_id_register():
    """API endpoint to register Face ID"""
    if not FACE_ID_AVAILABLE:
        return jsonify({'success': False, 'message': 'Face ID system not available'})
    
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'message': 'No image data provided'})
        
        username = session.get('username')
        
        # Register face
        result = face_id_system.register_face(username, image_data, is_base64=True)
        
        if result['success']:
            # Log action
            log_system_action(session['user_id'], 'face_id_registered', 
                            f'Face ID registered for {username}')
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Registration error: {str(e)}'})

@app.route('/api/face_id/remove', methods=['POST'])
def api_face_id_remove():
    """API endpoint to remove Face ID"""
    if not FACE_ID_AVAILABLE:
        return jsonify({'success': False, 'message': 'Face ID system not available'})
    
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    try:
        username = session.get('username')
        
        # Remove face
        result = face_id_system.remove_face(username)
        
        if result['success']:
            # Log action
            log_system_action(session['user_id'], 'face_id_removed', 
                            f'Face ID removed for {username}')
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Removal error: {str(e)}'})

@app.route('/api/face_id/status')
def api_face_id_status():
    """Get Face ID status for current user"""
    if not FACE_ID_AVAILABLE:
        return jsonify({'available': False, 'message': 'Face ID system not available'})
    
    if 'user_id' not in session:
        return jsonify({'available': False, 'message': 'Not logged in'})
    
    try:
        username = session.get('username')
        status = face_id_system.get_user_face_status(username)
        status['available'] = True
        return jsonify(status)
    except Exception as e:
        return jsonify({'available': False, 'message': str(e)})

@app.route('/face_id_setup')
def face_id_setup():
    """Face ID setup page for logged-in users - 360° version"""
    if 'user_id' not in session:
        flash('Please login first to set up Face ID', 'error')
        return redirect(url_for('login'))
    
    if not FACE_ID_AVAILABLE:
        flash('Face ID system not available', 'error')
        return redirect(url_for('dashboard'))
    
    # Get Face ID status
    username = session.get('username')
    status = face_id_system.get_user_face_status(username)
    
    return render_template('face_id_setup_360.html', 
                         face_status=status,
                         username=username,
                         role=session.get('role'))

@app.route('/api/face_id/register_360', methods=['POST'])
def api_face_id_register_360():
    """API endpoint to register 360° Face ID"""
    if not FACE_ID_AVAILABLE:
        return jsonify({'success': False, 'message': 'Face ID system not available'})
    
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    try:
        data = request.get_json()
        images = data.get('images', [])
        
        if not images or len(images) < 3:
            return jsonify({'success': False, 'message': 'Need at least 3 images for 360° capture'})
        
        username = session.get('username')
        
        # Register 360° face
        result = face_id_system.register_360_face(username, images)
        
        if result['success']:
            # Log action
            log_system_action(session['user_id'], 'face_id_360_registered', 
                            f'360° Face ID registered for {username} with {result.get("angles_captured", 0)} angles')
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Registration error: {str(e)}'})

@app.route('/api/face_id/auto_recognize', methods=['POST'])
def api_face_id_auto_recognize():
    """API endpoint for automatic face recognition with multi-account selection"""
    if not FACE_ID_AVAILABLE:
        return jsonify({'success': False, 'message': 'Face ID system not available'})
    
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'message': 'No image data provided'})
        
        # Auto-recognize face
        result = face_id_system.auto_recognize_face(image_data)
        
        if result['success']:
            # Face recognized
            username = result['username']
            is_master = result.get('is_master', False)
            
            conn = sqlite3.connect('bs_nexora_educational.db')
            cursor = conn.cursor()
            
            # Get the recognized user
            cursor.execute('''
                SELECT id, username, role, email, full_name, subdivision
                FROM users WHERE username = ? AND is_active = 1
            ''', (username,))
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                return jsonify({'success': False, 'message': 'User not found'})
            
            user_role = user[2]
            
            # Check if user is CTO or Master - they can login as any account
            if user_role in ['master', 'cto'] or is_master:
                # Get all available accounts for selection
                cursor.execute('''
                    SELECT id, username, role, full_name, email
                    FROM users 
                    WHERE is_active = 1
                    ORDER BY 
                        CASE role
                            WHEN 'master' THEN 1
                            WHEN 'cto' THEN 2
                            WHEN 'ceo' THEN 3
                            WHEN 'cao' THEN 4
                            WHEN 'crew_lead' THEN 5
                            WHEN 'teacher' THEN 6
                            WHEN 'student' THEN 7
                        END,
                        full_name
                ''')
                all_accounts = cursor.fetchall()
                conn.close()
                
                # Return account selection required
                accounts_list = [{
                    'id': acc[0],
                    'username': acc[1],
                    'role': acc[2],
                    'full_name': acc[3],
                    'email': acc[4]
                } for acc in all_accounts]
                
                return jsonify({
                    'success': True,
                    'requires_selection': True,
                    'recognized_user': username,
                    'recognized_role': user_role,
                    'is_master': is_master,
                    'available_accounts': accounts_list,
                    'message': f'Face recognized as {user[4]} ({user_role}). Select account to login:',
                    'confidence': result.get('confidence', 0)
                })
            
            else:
                # Regular user - direct login
                conn.close()
                
                # Create session
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['role'] = user[2]
                session['email'] = user[3]
                session['full_name'] = user[4]
                session['subdivision'] = user[5]
                session['face_id_login'] = True
                session['face_id_authenticated'] = True
                session['auto_login'] = True
                
                # Save session
                save_session_to_file(session)
                
                # Log action
                log_system_action(user[0], 'auto_face_id_login', 
                                f'Auto Face ID login for {username} (confidence: {result.get("confidence", 0):.1f}%)')
                
                return jsonify({
                    'success': True,
                    'requires_selection': False,
                    'message': f'Welcome back, {user[4]}!',
                    'username': username,
                    'role': user_role,
                    'confidence': result.get('confidence', 0),
                    'is_master': is_master
                })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Recognition error: {str(e)}'})

@app.route('/api/face_id/select_account', methods=['POST'])
def api_face_id_select_account():
    """Confirm account selection for CTO/Master Face ID login"""
    try:
        data = request.get_json()
        selected_username = data.get('selected_username')
        recognized_user = data.get('recognized_user')
        
        if not selected_username or not recognized_user:
            return jsonify({'success': False, 'message': 'Missing required data'})
        
        conn = sqlite3.connect('bs_nexora_educational.db')
        cursor = conn.cursor()
        
        # Verify the recognized user is CTO or Master
        cursor.execute('''
            SELECT id, username, role
            FROM users WHERE username = ? AND is_active = 1
        ''', (recognized_user,))
        auth_user = cursor.fetchone()
        
        if not auth_user or auth_user[2] not in ['master', 'cto']:
            conn.close()
            return jsonify({'success': False, 'message': 'Unauthorized access'})
        
        # Get the selected account
        cursor.execute('''
            SELECT id, username, role, email, full_name, subdivision
            FROM users WHERE username = ? AND is_active = 1
        ''', (selected_username,))
        target_user = cursor.fetchone()
        conn.close()
        
        if not target_user:
            return jsonify({'success': False, 'message': 'Selected account not found'})
        
        # Create session for selected account
        session['user_id'] = target_user[0]
        session['username'] = target_user[1]
        session['role'] = target_user[2]
        session['email'] = target_user[3]
        session['full_name'] = target_user[4]
        session['subdivision'] = target_user[5]
        session['face_id_login'] = True
        session['face_id_authenticated'] = True
        session['auto_login'] = True
        session['logged_in_as'] = recognized_user  # Track who actually logged in
        
        # Save session
        save_session_to_file(session)
        
        # Log action
        log_system_action(target_user[0], 'face_id_account_selection', 
                         f'{recognized_user} ({auth_user[2]}) logged in as {selected_username} ({target_user[2]}) via Face ID')
        
        return jsonify({
            'success': True,
            'message': f'Logged in as {target_user[4]} ({target_user[2]})',
            'username': target_user[1],
            'role': target_user[2],
            'full_name': target_user[4]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/face_id_auto_login')
def face_id_auto_login():
    """Auto Face ID login page with round interface"""
    if not FACE_ID_AVAILABLE:
        flash('Face ID system not available', 'error')
        return redirect(url_for('login'))
    
    return render_template('face_id_auto_login_round.html')

@app.route('/api/face_id/master_login', methods=['POST'])
def api_face_id_master_login():
    """Master Face ID login - CTO and Master can access any account"""
    if not FACE_ID_AVAILABLE:
        return jsonify({'success': False, 'message': 'Face ID system not available'})
    
    try:
        data = request.get_json()
        image_data = data.get('image')
        target_username = data.get('target_username')  # Account to login as
        
        if not image_data:
            return jsonify({'success': False, 'message': 'No image data provided'})
        
        # Authenticate face
        result = face_id_system.authenticate_face(image_data, is_base64=True)
        
        if result['success'] and result['is_master']:
            # Master face detected - can login as any account
            master_username = result['username']
            
            if target_username:
                # Login as target account
                conn = sqlite3.connect('bs_nexora_educational.db')
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, username, role, email, full_name, subdivision
                    FROM users WHERE username = ? AND is_active = 1
                ''', (target_username,))
                user = cursor.fetchone()
                conn.close()
                
                if user:
                    # Create session for target account
                    session['user_id'] = user[0]
                    session['username'] = user[1]
                    session['role'] = user[2]
                    session['email'] = user[3]
                    session['full_name'] = user[4]
                    session['subdivision'] = user[5]
                    session['face_id_login'] = True
                    session['master_face_access'] = True
                    session['master_face_user'] = master_username
                    
                    # Save session
                    save_session_to_file(session)
                    
                    # Log action
                    log_system_action(user[0], 'master_face_id_login', 
                                    f'Master Face ID ({master_username}) logged in as {target_username}')
                    
                    return jsonify({
                        'success': True,
                        'message': f'Master access granted. Logged in as {user[1]}',
                        'username': user[1],
                        'role': user[2],
                        'master_access': True,
                        'redirect': url_for('dashboard')
                    })
                else:
                    return jsonify({'success': False, 'message': 'Target account not found'})
            else:
                # Login as master account itself
                return api_face_id_authenticate()
        else:
            return jsonify({'success': False, 'message': 'Master Face ID required for this feature'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Master login error: {str(e)}'})

if __name__ == '__main__':
    import webbrowser
    import threading
    import time
    
    print("="*50)
    print("  B's Nexora Educational Platform Starting...")
    print("="*50)
    
    # Initialize database and create accounts
    print("Initializing database...")
    init_database()
    print("Creating default accounts...")
    create_default_accounts()
    
    # Security notice - simplified authentication
    print("\n" + "="*50)
    print("  SIMPLIFIED AUTHENTICATION SYSTEM")
    print("="*50)
    print("[OK] Database initialized successfully")
    print("[OK] Default accounts created securely")
    print("[OK] Username/Password authentication enabled")
    print("="*50)
    print("AUTHENTICATION: Simple username and password login")
    print("No product keys or passkeys required!")
    print("="*50)
    
    def open_browser():
        time.sleep(2)  # Wait for server to start
        try:
            webbrowser.open('http://localhost:5000')
            print("[OK] Browser opened automatically")
        except:
            print("! Could not open browser automatically")
            print("  Please manually open: http://localhost:5000")
    
    # Start browser opening in background
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    print("\nStarting Flask server...")
    print("Server will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop the server\n")
    
    try:
        app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\nError starting server: {e}")
        print("Try running on a different port or check if port 5000 is already in use")
