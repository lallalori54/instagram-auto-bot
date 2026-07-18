from flask import Flask, request, render_template_string, jsonify, session, redirect, url_for
import os
import json
import time
import logging
import random
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError
import re
from datetime import datetime
import tempfile
import shutil

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'admin-secret-key-2026')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== ADMIN CREDENTIALS ====================
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# ==================== IN-MEMORY STORAGE ====================
accounts = []  # List of {username, settings, valid}
uploaded_videos = []  # List of {filename, path, url, upload_time}
scheduled_jobs = []  # List of {video_file, caption, accounts, time, status}
daily_caption = "🎬 New video! Follow for more #instagram #trending"
last_caption_update = datetime.now().date()
posts_today = 0
post_date = datetime.now().date()

# ==================== HTML TEMPLATE ====================
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login</title>
    <style>
        body { font-family: Arial; background: #f5f5f5; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-box { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 350px; }
        h2 { text-align: center; color: #262626; }
        input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #dbdbdb; border-radius: 5px; }
        button { width: 100%; padding: 12px; background: #0095f6; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
        button:hover { background: #0077cc; }
        .error { color: red; text-align: center; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🔐 Admin Login</h2>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background: #fafafa; padding: 20px; color: #262626; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; flex-wrap: wrap; gap: 10px; }
        .header h1 { font-size: 28px; display: flex; align-items: center; gap: 10px; }
        .header h1 span { background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .logout-btn { background: #dc3545; color: white; border: none; padding: 8px 20px; border-radius: 5px; cursor: pointer; font-weight: 600; }
        .logout-btn:hover { background: #b02a37; }
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid #dbdbdb; }
        .card h3 { font-size: 16px; font-weight: 600; margin-bottom: 12px; color: #262626; }
        .card p { font-size: 14px; color: #8e8e8e; margin-bottom: 12px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 10px; }
        .stat-box { background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-box .num { font-size: 28px; font-weight: 700; color: #0095f6; }
        .stat-box .label { font-size: 12px; color: #8e8e8e; }
        input, textarea, select { width: 100%; padding: 10px 12px; border: 1px solid #dbdbdb; border-radius: 8px; font-size: 14px; background: #fafafa; transition: border 0.2s; font-family: inherit; }
        input:focus, textarea:focus, select:focus { outline: none; border-color: #0095f6; background: white; }
        textarea { resize: vertical; min-height: 60px; }
        button { background: #0095f6; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: background 0.2s; margin-top: 8px; }
        button:hover { background: #0077cc; }
        button.danger { background: #dc3545; }
        button.danger:hover { background: #b02a37; }
        button.success { background: #28a745; }
        button.success:hover { background: #1e7e34; }
        button.warning { background: #ffc107; color: #212529; }
        button.warning:hover { background: #e0a800; }
        .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .flex { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
        .account-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: #f8f9fa; border-radius: 8px; margin-bottom: 6px; border-left: 4px solid #28a745; }
        .account-item.inactive { border-left-color: #dc3545; opacity: 0.6; }
        .account-item .username { font-weight: 500; }
        .account-item .status { font-size: 12px; padding: 2px 10px; border-radius: 12px; background: #e8f5e9; color: #2e7d32; }
        .account-item .status.inactive { background: #fbe9e7; color: #c62828; }
        .account-item .remove-btn { background: none; border: none; color: #dc3545; cursor: pointer; font-size: 16px; padding: 0 5px; }
        .msg { padding: 10px 14px; border-radius: 8px; margin-top: 10px; font-size: 14px; }
        .msg.success { background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }
        .msg.error { background: #fbe9e7; color: #c62828; border: 1px solid #ffcdd2; }
        .msg.info { background: #e3f2fd; color: #0d47a1; border: 1px solid #bbdefb; }
        .hidden { display: none; }
        .mt-10 { margin-top: 10px; }
        .video-item { display: flex; justify-content: space-between; padding: 8px 12px; background: #f8f9fa; border-radius: 5px; margin-bottom: 4px; }
        .video-item .name { font-size: 13px; }
        .video-item .time { font-size: 12px; color: #8e8e8e; }
        .badge { font-size: 12px; padding: 2px 10px; border-radius: 12px; background: #e3f2fd; color: #0d47a1; }
        @media (max-width: 600px) { .row { grid-template-columns: 1fr; } .flex { flex-direction: column; } }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📸 <span>Admin Dashboard</span></h1>
        <form method="POST" action="/logout"><button class="logout-btn" type="submit">🚪 Logout</button></form>
    </div>

    <!-- Stats -->
    <div class="card">
        <div class="stats">
            <div class="stat-box"><div class="num">{{ accounts|length }}</div><div class="label">Total Accounts</div></div>
            <div class="stat-box"><div class="num">{{ active_accounts }}</div><div class="label">Active</div></div>
            <div class="stat-box"><div class="num">{{ posts_today }}</div><div class="label">Posts Today</div></div>
            <div class="stat-box"><div class="num">{{ uploaded_videos|length }}</div><div class="label">Videos Uploaded</div></div>
        </div>
    </div>

    <!-- Daily Caption -->
    <div class="card">
        <h3>✏️ Daily Caption</h3>
        <p>Jo caption aaj set kiya, aaj bhi din yehi caption use hoga.</p>
        <div class="flex">
            <input type="text" id="dailyCaptionInput" value="{{ daily_caption }}" style="flex:1;">
            <button onclick="updateCaption()">Update Caption</button>
        </div>
        <div id="captionMsg" class="hidden"></div>
    </div>

    <!-- Add Account via Cookie -->
    <div class="card">
        <h3>➕ Add Account via Cookie</h3>
        <p>Browser se <strong>sessionid</strong>, <strong>csrftoken</strong>, <strong>ds_user_id</strong> cookies copy karein.</p>
        <textarea id="cookieInput" rows="4" placeholder='{"sessionid": "your_sessionid", "csrftoken": "your_csrftoken", "ds_user_id": "your_user_id"}'></textarea>
        <button onclick="addAccount()">Add Account</button>
        <div id="addMsg" class="hidden"></div>
    </div>

    <!-- Account List -->
    <div class="card">
        <h3>📋 Active Accounts</h3>
        <div id="accountList">
            {% for acc in accounts %}
                <div class="account-item {% if not acc.valid %}inactive{% endif %}">
                    <span class="username">@{{ acc.username }}</span>
                    <span class="status {% if not acc.valid %}inactive{% endif %}">
                        {% if acc.valid %}✅ Active{% else %}❌ Invalid{% endif %}
                    </span>
                    <button class="remove-btn" onclick="removeAccount('{{ acc.username }}')">✕</button>
                </div>
            {% else %}
                <p style="color: #8e8e8e;">No accounts added yet.</p>
            {% endfor %}
        </div>
    </div>

    <!-- Upload Video -->
    <div class="card">
        <h3>📤 Upload Video</h3>
        <p>Video upload karo, URL auto-generate ho jayega.</p>
        <div class="flex">
            <input type="file" id="videoFile" accept="video/*" style="width:auto;">
            <button class="success" onclick="uploadVideo()">Upload Video</button>
        </div>
        <div id="uploadMsg" class="hidden"></div>
    </div>

    <!-- Video List -->
    <div class="card">
        <h3>🎬 Uploaded Videos</h3>
        <div id="videoList">
            {% for v in uploaded_videos %}
                <div class="video-item">
                    <span class="name">{{ v.filename }}</span>
                    <span class="time">{{ v.upload_time }}</span>
                </div>
            {% else %}
                <p style="color: #8e8e8e;">No videos uploaded yet.</p>
            {% endfor %}
        </div>
    </div>

    <!-- Post Now -->
    <div class="card">
        <h3>📤 Post Video (Random Selection)</h3>
        <p>Uploaded videos mein se <strong>random</strong> video pick hogi aur <strong>sab accounts</strong> pe post hogi.</p>
        <div class="flex">
            <button onclick="postRandomVideo()">🎲 Post Random Video to All</button>
            <button onclick="postRandomStory()">📸 Post Random Story</button>
        </div>
        <div id="postMsg" class="hidden"></div>
    </div>

    <!-- Schedule Post -->
    <div class="card">
        <h3>⏰ Schedule Auto-Post</h3>
        <p>Har din set time pe random video sab accounts pe post hogi.</p>
        <div class="row">
            <div>
                <label>Time (24hr format)</label>
                <input type="time" id="schedTime" value="08:00">
            </div>
            <div>
                <label>Post Type</label>
                <select id="schedType">
                    <option value="video">Video Post</option>
                    <option value="story">Story</option>
                </select>
            </div>
        </div>
        <button onclick="schedulePost()">⏰ Schedule</button>
        <div id="schedMsg" class="hidden"></div>
    </div>

    <!-- Scheduled Jobs -->
    <div class="card">
        <h3>📅 Scheduled Jobs</h3>
        <div id="scheduledList">
            {% for job in scheduled_jobs %}
                <div class="account-item">
                    <span>🕐 {{ job.time }} - {{ job.type }}</span>
                    <span class="badge">{{ job.status }}</span>
                    <button class="remove-btn" onclick="removeJob('{{ loop.index0 }}')">✕</button>
                </div>
            {% else %}
                <p style="color: #8e8e8e;">No scheduled jobs.</p>
            {% endfor %}
        </div>
    </div>
</div>

<script>
// ========== Daily Caption ==========
function updateCaption() {
    const caption = document.getElementById('dailyCaptionInput').value;
    fetch('/update_caption', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({caption: caption})
    })
    .then(res => res.json())
    .then(data => {
        showMsg('captionMsg', '✅ ' + data.message, 'success');
    })
    .catch(err => showMsg('captionMsg', '❌ Error', 'error'));
}

// ========== Add Account ==========
function addAccount() {
    const data = document.getElementById('cookieInput').value;
    if (!data.trim()) { alert('Please paste cookie data'); return; }
    fetch('/add_account', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({cookie_data: data})
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            showMsg('addMsg', '✅ ' + data.message, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showMsg('addMsg', '❌ ' + data.message, 'error');
        }
    })
    .catch(err => showMsg('addMsg', '❌ Error', 'error'));
}

// ========== Remove Account ==========
function removeAccount(username) {
    if (!confirm('Remove @' + username + '?')) return;
    fetch('/remove_account', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username: username})
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') location.reload();
        else alert('Error: ' + data.message);
    });
}

// ========== Upload Video ==========
function uploadVideo() {
    const fileInput = document.getElementById('videoFile');
    const file = fileInput.files[0];
    if (!file) { alert('Select a video file first'); return; }
    
    const formData = new FormData();
    formData.append('video', file);
    
    showMsg('uploadMsg', '⏳ Uploading...', 'info');
    fetch('/upload_video', {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            showMsg('uploadMsg', '✅ ' + data.message, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showMsg('uploadMsg', '❌ ' + data.message, 'error');
        }
    })
    .catch(err => showMsg('uploadMsg', '❌ Error', 'error'));
}

// ========== Post Random Video ==========
function postRandomVideo() {
    if (!confirm('Post random video to ALL accounts?')) return;
    showMsg('postMsg', '⏳ Processing...', 'info');
    fetch('/post_random_video', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            showMsg('postMsg', '✅ ' + data.message, 'success');
        } else {
            showMsg('postMsg', '❌ ' + data.message, 'error');
        }
    })
    .catch(err => showMsg('postMsg', '❌ Error', 'error'));
}

// ========== Post Random Story ==========
function postRandomStory() {
    if (!confirm('Post random story to ALL accounts?')) return;
    showMsg('postMsg', '⏳ Processing...', 'info');
    fetch('/post_random_story', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            showMsg('postMsg', '✅ ' + data.message, 'success');
        } else {
            showMsg('postMsg', '❌ ' + data.message, 'error');
        }
    })
    .catch(err => showMsg('postMsg', '❌ Error', 'error'));
}

// ========== Schedule ==========
function schedulePost() {
    const time = document.getElementById('schedTime').value;
    const type = document.getElementById('schedType').value;
    if (!time) { alert('Please select time'); return; }
    
    fetch('/schedule_post', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({time: time, type: type})
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            showMsg('schedMsg', '✅ ' + data.message, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showMsg('schedMsg', '❌ ' + data.message, 'error');
        }
    });
}

function removeJob(index) {
    if (!confirm('Remove this scheduled job?')) return;
    fetch('/remove_job', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({index: index})
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') location.reload();
    });
}

// ========== Utils ==========
function showMsg(id, text, type) {
    const el = document.getElementById(id);
    el.className = 'msg ' + type;
    el.textContent = text;
    el.style.display = 'block';
}
</script>
</body>
</html>
"""

# ==================== ROUTES ====================

@app.route('/', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('admin'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        return render_template_string(LOGIN_HTML, error='Invalid credentials')
    return render_template_string(LOGIN_HTML, error=None)

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    active = len([a for a in accounts if a.get('valid', False)])
    return render_template_string(
        ADMIN_HTML,
        accounts=accounts,
        active_accounts=active,
        posts_today=posts_today,
        uploaded_videos=uploaded_videos,
        daily_caption=daily_caption,
        scheduled_jobs=scheduled_jobs
    )

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==================== API ROUTES ====================

@app.route('/update_caption', methods=['POST'])
def update_caption():
    global daily_caption
    caption = request.json.get('caption', '')
    if caption:
        daily_caption = caption
        return jsonify({'status': 'success', 'message': 'Caption updated!'})
    return jsonify({'status': 'error', 'message': 'Caption empty'})

@app.route('/add_account', methods=['POST'])
def add_account():
    try:
        data = request.json.get('cookie_data')
        if isinstance(data, str):
            cookie_dict = json.loads(data)
        else:
            cookie_dict = data
        
        required = ['sessionid', 'csrftoken', 'ds_user_id']
        missing = [k for k in required if k not in cookie_dict]
        if missing:
            return jsonify({'status': 'error', 'message': f'Missing: {", ".join(missing)}'})
        
        # Test session
        cl = Client()
        cl.set_settings(cookie_dict)
        username = cl.get_username()
        
        if any(acc.get('username') == username for acc in accounts):
            return jsonify({'status': 'error', 'message': f'Account @{username} already added'})
        
        accounts.append({
            'username': username,
            'settings': cookie_dict,
            'valid': True
        })
        return jsonify({'status': 'success', 'message': f'Account @{username} added!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/remove_account', methods=['POST'])
def remove_account():
    global accounts
    username = request.json.get('username')
    accounts = [a for a in accounts if a.get('username') != username]
    return jsonify({'status': 'success', 'message': f'Removed @{username}'})

@app.route('/upload_video', methods=['POST'])
def upload_video():
    try:
        if 'video' not in request.files:
            return jsonify({'status': 'error', 'message': 'No video file'})
        file = request.files['video']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'})
        
        # Save to temp
        import tempfile
        import shutil
        import os
        from datetime import datetime
        
        # Create uploads directory if not exists
        os.makedirs('uploads', exist_ok=True)
        
        # Save file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join('uploads', filename)
        file.save(filepath)
        
        # Store metadata
        uploaded_videos.append({
            'filename': filename,
            'path': filepath,
            'upload_time': datetime.now().strftime('%H:%M'),
            'url': f"/uploads/{filename}"  # Local URL
        })
        
        return jsonify({
            'status': 'success',
            'message': f'Video uploaded: {filename}',
            'url': f"/uploads/{filename}"
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/post_random_video', methods=['POST'])
def post_random_video():
    try:
        if not uploaded_videos:
            return jsonify({'status': 'error', 'message': 'No videos uploaded. Upload first!'})
        
        active = [a for a in accounts if a.get('valid', False)]
        if not active:
            return jsonify({'status': 'error', 'message': 'No active accounts'})
        
        # Pick random video
        video = random.choice(uploaded_videos)
        video_path = video['path']
        
        # Post to all active accounts
        success_count = 0
        failed = []
        
        for acc in active:
            try:
                cl = Client()
                cl.set_settings(acc['settings'])
                cl.get_user_id()
                cl.clip_upload(video_path, daily_caption)
                success_count += 1
                global posts_today
                posts_today += 1
            except Exception as e:
                failed.append(f"@{acc['username']}: {str(e)[:30]}")
            time.sleep(30)
        
        message = f"✅ Posted '{video['filename']}' on {success_count}/{len(active)} accounts"
        if failed:
            message += f" | Failed: {', '.join(failed)}"
        return jsonify({'status': 'success', 'message': message})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/post_random_story', methods=['POST'])
def post_random_story():
    try:
        if not uploaded_videos:
            return jsonify({'status': 'error', 'message': 'No videos uploaded'})
        
        active = [a for a in accounts if a.get('valid', False)]
        if not active:
            return jsonify({'status': 'error', 'message': 'No active accounts'})
        
        video = random.choice(uploaded_videos)
        video_path = video['path']
        
        success_count = 0
        for acc in active:
            try:
                cl = Client()
                cl.set_settings(acc['settings'])
                cl.get_user_id()
                cl.video_upload_to_story(video_path)
                success_count += 1
            except Exception as e:
                pass
            time.sleep(30)
        
        return jsonify({'status': 'success', 'message': f'Story posted on {success_count}/{len(active)} accounts'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/schedule_post', methods=['POST'])
def schedule_post():
    try:
        time_str = request.json.get('time')
        post_type = request.json.get('type', 'video')
        if not time_str:
            return jsonify({'status': 'error', 'message': 'Time required'})
        
        scheduled_jobs.append({
            'time': time_str,
            'type': post_type,
            'status': 'pending'
        })
        return jsonify({'status': 'success', 'message': f'Scheduled at {time_str} ({post_type})'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/remove_job', methods=['POST'])
def remove_job():
    try:
        index = int(request.json.get('index', -1))
        if 0 <= index < len(scheduled_jobs):
            scheduled_jobs.pop(index)
            return jsonify({'status': 'success', 'message': 'Job removed'})
        return jsonify({'status': 'error', 'message': 'Job not found'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# ==================== SERVE UPLOADS ====================
from flask import send_from_directory
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

# ==================== SCHEDULED TASK (Run every minute) ====================
import threading
import time
from datetime import datetime

def scheduler_loop():
    """Background thread that checks scheduled jobs every minute"""
    global posts_today, post_date
    while True:
        try:
            now = datetime.now()
            current_time = now.strftime('%H:%M')
            
            # Reset daily counter
            today = now.date()
            if post_date != today:
                posts_today = 0
                post_date = today
            
            # Check scheduled jobs
            for job in scheduled_jobs[:]:
                if job['time'] == current_time and job['status'] == 'pending':
                    job['status'] = 'running'
                    
                    # Post random video or story
                    if job['type'] == 'video':
                        # Run post function
                        active = [a for a in accounts if a.get('valid', False)]
                        if active and uploaded_videos:
                            video = random.choice(uploaded_videos)
                            for acc in active:
                                try:
                                    cl = Client()
                                    cl.set_settings(acc['settings'])
                                    cl.get_user_id()
                                    cl.clip_upload(video['path'], daily_caption)
                                    posts_today += 1
                                except Exception as e:
                                    pass
                                time.sleep(30)
                    elif job['type'] == 'story':
                        active = [a for a in accounts if a.get('valid', False)]
                        if active and uploaded_videos:
                            video = random.choice(uploaded_videos)
                            for acc in active:
                                try:
                                    cl = Client()
                                    cl.set_settings(acc['settings'])
                                    cl.get_user_id()
                                    cl.video_upload_to_story(video['path'])
                                except Exception as e:
                                    pass
                                time.sleep(30)
                    
                    job['status'] = 'completed'
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        
        time.sleep(30)  # Check every 30 seconds

# Start scheduler thread
thread = threading.Thread(target=scheduler_loop, daemon=True)
thread.start()

# ==================== RUN ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
