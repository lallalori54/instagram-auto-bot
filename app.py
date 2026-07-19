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

# ==================== INSTAGRAM PROFESSIONAL UI HTML ====================
INSTAGRAM_LOGIN_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram Auto Poster</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }
        .login-container {
            display: flex;
            max-width: 1000px;
            width: 100%;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
            backdrop-filter: blur(10px);
        }
        .login-left {
            flex: 1;
            padding: 50px 40px;
            background: linear-gradient(145deg, #f8f9fa, #ffffff);
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .login-right {
            flex: 1;
            background: linear-gradient(145deg, #667eea, #764ba2);
            padding: 50px 40px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: white;
            text-align: center;
        }
        .login-right h2 {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 20px;
        }
        .login-right p {
            font-size: 16px;
            opacity: 0.9;
            line-height: 1.6;
            max-width: 350px;
        }
        .login-right .icon {
            font-size: 80px;
            margin-bottom: 20px;
            background: rgba(255,255,255,0.2);
            padding: 20px;
            border-radius: 50%;
            width: 120px;
            height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .logo {
            margin-bottom: 30px;
        }
        .logo h1 {
            font-size: 32px;
            background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
        }
        .logo p {
            color: #8e8e8e;
            font-size: 14px;
            margin-top: 5px;
        }
        .input-group {
            margin-bottom: 12px;
            position: relative;
        }
        .input-group input {
            width: 100%;
            padding: 14px 16px;
            background: #fafafa;
            border: 2px solid #dbdbdb;
            border-radius: 10px;
            font-size: 14px;
            outline: none;
            transition: all 0.3s ease;
        }
        .input-group input:focus {
            border-color: #0095f6;
            background: white;
            box-shadow: 0 0 0 4px rgba(0,149,246,0.1);
        }
        .login-btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(45deg, #0095f6, #0077cc);
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            font-size: 16px;
            cursor: pointer;
            margin-top: 8px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,149,246,0.3);
        }
        .login-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,149,246,0.4);
        }
        .login-btn:disabled {
            opacity: 0.7;
            cursor: not-allowed;
            transform: none;
        }
        .divider {
            display: flex;
            align-items: center;
            margin: 20px 0;
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
        .social-login {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
            color: #385185;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            text-decoration: none;
            padding: 10px;
            border-radius: 10px;
            transition: background 0.2s;
        }
        .social-login:hover {
            background: #f0f2f5;
        }
        .social-login svg {
            width: 20px;
            height: 20px;
        }
        .forgot-password {
            color: #00376b;
            font-size: 13px;
            text-decoration: none;
            display: block;
            text-align: center;
            margin-top: 12px;
            transition: color 0.2s;
        }
        .forgot-password:hover {
            color: #0095f6;
        }
        .signup-box {
            text-align: center;
            font-size: 14px;
            margin-top: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        .signup-box a {
            color: #0095f6;
            font-weight: 600;
            text-decoration: none;
        }
        .signup-box a:hover {
            text-decoration: underline;
        }
        .error-msg {
            color: #ed4956;
            font-size: 13px;
            margin-bottom: 12px;
            text-align: center;
            background: #fde8e8;
            padding: 10px;
            border-radius: 8px;
        }
        .success-msg {
            color: #28a745;
            font-size: 13px;
            margin-bottom: 12px;
            text-align: center;
            background: #e8f5e9;
            padding: 10px;
            border-radius: 8px;
        }
        .loading {
            display: inline-block;
            width: 18px;
            height: 18px;
            border: 3px solid #fff;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 0.6s linear infinite;
            vertical-align: middle;
            margin-right: 8px;
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
        .twofa-input input {
            border-color: #ffc107 !important;
        }
        .twofa-input label {
            font-size: 12px;
            color: #856404;
            margin-bottom: 4px;
            display: block;
        }
        .features {
            display: flex;
            gap: 20px;
            margin-top: 20px;
            flex-wrap: wrap;
            justify-content: center;
        }
        .features span {
            font-size: 12px;
            opacity: 0.8;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        @media (max-width: 768px) {
            .login-container {
                flex-direction: column;
                border-radius: 15px;
            }
            .login-left {
                padding: 30px 25px;
            }
            .login-right {
                padding: 30px 25px;
                border-radius: 0 0 15px 15px;
            }
            .login-right .icon {
                width: 80px;
                height: 80px;
                font-size: 50px;
            }
            .login-right h2 {
                font-size: 24px;
            }
        }
    </style>
</head>
<body>
<div class="login-container">
    <div class="login-left">
        <div class="logo">
            <h1>📸 AutoPost</h1>
            <p>Instagram Automation Dashboard</p>
        </div>

        {% if error %}
        <div class="error-msg">❌ {{ error }}</div>
        {% endif %}
        {% if success %}
        <div class="success-msg">✅ {{ success }}</div>
        {% endif %}

        <form id="loginForm" method="POST" action="/instagram_login">
            <div class="input-group">
                <input type="text" id="username" name="username" placeholder="📱 Phone number, username, or email" required>
            </div>
            <div class="input-group">
                <input type="password" id="password" name="password" placeholder="🔒 Password" required>
            </div>
            <div class="input-group twofa-input" id="twofaGroup">
                <label>🔑 Two-Factor Authentication Code</label>
                <input type="text" id="twofa" name="twofa" placeholder="Enter 6-digit code">
            </div>
            <button type="submit" class="login-btn" id="loginBtn">🚀 Log in</button>
        </form>

        <div class="divider">
            <div class="divider-line"></div>
            <div class="divider-text">OR</div>
            <div class="divider-line"></div>
        </div>

        <a href="#" class="social-login">
            <svg viewBox="0 0 20 20"><path d="M20 10c0-5.5-4.5-10-10-10S0 4.5 0 10c0 5 3.7 9.1 8.4 9.9v-7H5.9V10h2.5V7.8c0-2.5 1.5-3.8 3.7-3.8 1.1 0 2.2.2 2.2.2v2.5h-1.2c-1.2 0-1.6.8-1.6 1.6V10h2.8l-.4 2.9h-2.4v7C16.3 19.1 20 15 20 10z" fill="#1877f2"/></svg>
            Log in with Facebook
        </a>
        <a href="#" class="forgot-password">🔑 Forgot password?</a>

        <div class="signup-box">
            Don't have an account? <a href="#">Sign up</a>
        </div>
    </div>

    <div class="login-right">
        <div class="icon">📸</div>
        <h2>AutoPost Pro</h2>
        <p>Manage multiple Instagram accounts, schedule posts, and automate your content strategy — all in one place.</p>
        <div class="features">
            <span>✅ Multi-Account</span>
            <span>⏰ Auto Schedule</span>
            <span>📊 Analytics</span>
            <span>🎬 Video & Story</span>
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

# ==================== ADMIN DASHBOARD ====================
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head><title>Admin Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;background:#f0f2f5;padding:20px}
.container{max-width:1200px;margin:0 auto}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:25px;flex-wrap:wrap;gap:10px}
.header h1{font-size:28px;display:flex;align-items:center;gap:10px}
.header h1 span{background:linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header-actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.header-actions a{color:#0095f6;text-decoration:none;font-weight:600}
.logout-btn{background:#dc3545;color:white;border:none;padding:10px 20px;border-radius:8px;cursor:pointer;font-weight:600;transition:background 0.2s}
.logout-btn:hover{background:#b02a37}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:15px;margin-bottom:25px}
.stat-card{background:white;padding:20px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,0.05);text-align:center;transition:transform 0.2s}
.stat-card:hover{transform:translateY(-3px)}
.stat-card .num{font-size:32px;font-weight:700;color:#0095f6}
.stat-card .label{font-size:13px;color:#8e8e8e;margin-top:4px}
.card{background:white;border-radius:12px;padding:24px;margin-bottom:20px;box-shadow:0 2px 10px rgba(0,0,0,0.05)}
.card h3{font-size:16px;margin-bottom:12px;display:flex;align-items:center;gap:8px}
input,textarea,select{width:100%;padding:12px 14px;border:2px solid #e0e0e0;border-radius:8px;font-size:14px;background:#fafafa;transition:border 0.2s}
input:focus,textarea:focus,select:focus{outline:none;border-color:#0095f6;background:white}
button{background:#0095f6;color:white;border:none;padding:12px 24px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;transition:all 0.2s}
button:hover{background:#0077cc;transform:translateY(-2px);box-shadow:0 4px 15px rgba(0,149,246,0.3)}
button.danger{background:#dc3545}
button.danger:hover{background:#b02a37;box-shadow:0 4px 15px rgba(220,53,69,0.3)}
button.success{background:#28a745}
button.success:hover{background:#1e7e34;box-shadow:0 4px 15px rgba(40,167,69,0.3)}
button.warning{background:#ffc107;color:#212529}
button.warning:hover{background:#e0a800}
.row{display:grid;grid-template-columns:1fr 1fr;gap:15px}
.flex{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.account-item{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:#f8f9fa;border-radius:8px;margin-bottom:8px;border-left:4px solid #28a745}
.account-item.inactive{border-left-color:#dc3545;opacity:0.6}
.msg{padding:12px 16px;border-radius:8px;margin-top:10px;font-weight:500}
.msg.success{background:#d4edda;color:#155724;border:1px solid #c3e6cb}
.msg.error{background:#f8d7da;color:#721c24;border:1px solid #f5c6cb}
.msg.info{background:#d1ecf1;color:#0c5460;border:1px solid #bee5eb}
.hidden{display:none}
.mt-10{margin-top:10px}
@media (max-width:600px){.row{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>📸 <span>Admin Dashboard</span></h1>
<div class="header-actions">
<a href="/">➕ Add Account</a>
<form method="POST" action="/logout" style="display:inline"><button class="logout-btn" type="submit">🚪 Logout</button></form>
</div>
</div>

<div class="stats">
<div class="stat-card"><div class="num">{{ accounts|length }}</div><div class="label">Accounts</div></div>
<div class="stat-card"><div class="num">{{ active_accounts }}</div><div class="label">Active</div></div>
<div class="stat-card"><div class="num">{{ posts_today }}</div><div class="label">Posts Today</div></div>
<div class="stat-card"><div class="num">{{ uploaded_videos|length }}</div><div class="label">Videos</div></div>
</div>

<div class="card"><h3>📋 Accounts</h3>
{% for acc in accounts %}
<div class="account-item {% if not acc.valid %}inactive{% endif %}">
<span>@{{ acc.username }}</span>
<span>{% if acc.valid %}✅ Active{% else %}❌ Invalid{% endif %}</span>
<button class="danger" onclick="removeAccount('{{ acc.username }}')">✕</button>
</div>
{% else %}<p style="color:#8e8e8e">No accounts added. <a href="/">Add one</a></p>{% endfor %}
</div>

<div class="card"><h3>📤 Upload Video</h3>
<input type="file" id="videoFile" accept="video/*">
<button class="success" onclick="uploadVideo()">📤 Upload</button>
<div id="uploadMsg" class="hidden"></div>
</div>

<div class="card"><h3>📤 Post</h3>
<div class="flex">
<button onclick="postRandomVideo()">🎲 Post Video to All</button>
<button onclick="postRandomStory()">📸 Post Story to All</button>
</div>
<div id="postMsg" class="hidden"></div>
</div>

<div class="card"><h3>⏰ Schedule</h3>
<div class="row">
<div><label>Time</label><input type="time" id="schedTime" value="08:00"></div>
<div><label>Type</label><select id="schedType"><option value="video">Video Post</option><option value="story">Story</option></select></div>
</div>
<button onclick="schedulePost()">⏰ Schedule</button>
<div id="schedMsg" class="hidden"></div>
</div>

<div class="card"><h3>📅 Scheduled Jobs</h3>
{% for job in scheduled_jobs %}<div class="account-item"><span>🕐 {{ job.time }} - {{ job.type }}</span><span>{{ job.status }}</span></div>{% else %}<p style="color:#8e8e8e">No scheduled jobs</p>{% endfor %}
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
    setTimeout(() => { el.style.display = 'none'; }, 5000);
}
</script>
</body>
</html>
"""

# ==================== ROUTES ====================

@app.route('/', methods=['GET'])
def index():
    return render_template_string(INSTAGRAM_LOGIN_UI, error=None, success=None)

@app.route('/instagram_login', methods=['POST'])
def instagram_login():
    global accounts
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        twofa = request.form.get('twofa', '')

        if not username or not password:
            return render_template_string(INSTAGRAM_LOGIN_UI, 
                error='Please enter username and password.', success=None)

        cl = Client()

        if twofa:
            cl.login(username, password, verification_code=twofa)
        else:
            try:
                cl.login(username, password)
            except TwoFactorRequired:
                return render_template_string(INSTAGRAM_LOGIN_UI, 
                    error='2FA required! Please enter verification code.', success=None)
            except PleaseWaitFewMinutes:
                return render_template_string(INSTAGRAM_LOGIN_UI, 
                    error='Too many attempts. Wait a few minutes.', success=None)
            except Exception as e:
                return render_template_string(INSTAGRAM_LOGIN_UI, 
                    error=f'Login failed: {str(e)}', success=None)

        logged_username = cl.username
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
        return redirect(url_for('admin'))

    except Exception as e:
        logger.error(f"Login error: {e}")
        return render_template_string(INSTAGRAM_LOGIN_UI, 
            error=f'Login failed: {str(e)}', success=None)

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    active = len([a for a in accounts if a.get('valid', False)])
    return render_template_string(ADMIN_HTML, accounts=accounts, active_accounts=active,
                                   posts_today=posts_today, uploaded_videos=uploaded_videos,
                                   scheduled_jobs=scheduled_jobs)

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
