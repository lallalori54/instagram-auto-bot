from flask import Flask, request, render_template_string, jsonify, session, redirect, url_for
import os
import json
import time
import logging
import random
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, PleaseWaitFewMinutes, LoginRequired
from datetime import datetime
import threading

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'admin-secret-key-2026')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

accounts = []  # {username, client, valid, settings}
uploaded_videos = []
scheduled_jobs = []
daily_caption = "🎬 New video! Follow for more #instagram #trending"
posts_today = 0
post_date = datetime.now().date()

# ==================== HTML ====================
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head><title>Login</title>
<style>
body{font-family:Arial;background:#f5f5f5;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
.login-box{background:white;padding:40px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);width:350px}
h2{text-align:center}
input{width:100%;padding:12px;margin:8px 0;border:1px solid #dbdbdb;border-radius:5px}
button{width:100%;padding:12px;background:#0095f6;color:white;border:none;border-radius:5px;font-size:16px;cursor:pointer}
button:hover{background:#0077cc}
.error{color:red;text-align:center}
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
<html>
<head><title>Admin</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial,sans-serif;background:#fafafa;padding:20px}
.container{max-width:1000px;margin:0 auto}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:25px}
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
.video-item{display:flex;justify-content:space-between;padding:8px 12px;background:#f8f9fa;border-radius:5px;margin-bottom:4px}
</style>
</head>
<body>
<div class="container">
<div class="header"><h1>📸 <span>Admin Dashboard</span></h1><form method="POST" action="/logout"><button class="logout-btn" type="submit">🚪 Logout</button></form></div>

<div class="stats">
<div class="stat-box"><div class="num">{{ accounts|length }}</div><div>Accounts</div></div>
<div class="stat-box"><div class="num">{{ active_accounts }}</div><div>Active</div></div>
<div class="stat-box"><div class="num">{{ posts_today }}</div><div>Posts Today</div></div>
<div class="stat-box"><div class="num">{{ uploaded_videos|length }}</div><div>Videos</div></div>
</div>

<!-- Add Account -->
<div class="card" style="border:2px solid #0095f6;">
<h3>🔑 Add Account (Username + Password)</h3>
<p>Instagram account ka username aur password daalo - session save ho jayegi [citation:7].</p>
<div class="row">
<div><label>Username</label><input type="text" id="loginUsername" placeholder="Instagram username"></div>
<div><label>Password</label><input type="password" id="loginPassword" placeholder="Password"></div>
</div>
<div class="mt-10"><label>2FA Code (agar hai toh)</label><input type="text" id="login2FA" placeholder="Leave empty if no 2FA"></div>
<button class="success" onclick="addAccount()">✅ Add Account</button>
<div id="loginMsg" class="hidden"></div>
</div>

<!-- Account List -->
<div class="card"><h3>📋 Accounts</h3>
{% for acc in accounts %}
<div class="account-item"><span>@{{ acc.username }}</span><span>{% if acc.valid %}✅ Active{% else %}❌ Invalid{% endif %}</span>
<button class="danger" onclick="removeAccount('{{ acc.username }}')">✕</button></div>
{% else %}<p>No accounts</p>{% endfor %}
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
function addAccount() {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const twofa = document.getElementById('login2FA').value;
    if (!username || !password) { alert('Username and password required!'); return; }
    showMsg('loginMsg', '⏳ Logging in...', 'info');
    fetch('/add_account', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username: username, password: password, twofa: twofa || ''})
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            showMsg('loginMsg', '✅ ' + data.message, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showMsg('loginMsg', '❌ ' + data.message, 'error');
        }
    })
    .catch(err => showMsg('loginMsg', '❌ ' + err, 'error'));
}

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
    return render_template_string(ADMIN_HTML, accounts=accounts, active_accounts=active,
                                   posts_today=posts_today, uploaded_videos=uploaded_videos,
                                   scheduled_jobs=scheduled_jobs)

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==================== API ROUTES ====================

@app.route('/add_account', methods=['POST'])
def add_account():
    global accounts
    try:
        username = request.json.get('username')
        password = request.json.get('password')
        twofa = request.json.get('twofa', '')

        if not username or not password:
            return jsonify({'status': 'error', 'message': 'Username and password required'})

        cl = Client()

        # 2FA handle with verification code [citation:3]
        if twofa:
            cl.login(username, password, verification_code=twofa)
        else:
            try:
                cl.login(username, password)
            except TwoFactorRequired:
                return jsonify({'status': 'error', 'message': '2FA required! Please enter verification code.'})
            except PleaseWaitFewMinutes:
                return jsonify({'status': 'error', 'message': 'Too many attempts. Wait a few minutes.'})

        logged_username = cl.username

        # Session save for next time [citation:7]
        cl.dump_settings(f"session_{logged_username}.json")

        if any(acc.get('username') == logged_username for acc in accounts):
            return jsonify({'status': 'error', 'message': f'Account @{logged_username} already added'})

        accounts.append({
            'username': logged_username,
            'settings': f"session_{logged_username}.json",
            'client': cl,
            'valid': True
        })

        logger.info(f"✅ Added account: @{logged_username}")
        return jsonify({'status': 'success', 'message': f'Account @{logged_username} added! Session saved.'})

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'status': 'error', 'message': f'Login failed: {str(e)}'})

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
                # Load saved session if exists [citation:7]
                if acc.get('settings') and os.path.exists(acc['settings']):
                    cl.load_settings(acc['settings'])
                    cl.login(acc['username'], '')  # Empty password works with session
                elif 'client' in acc:
                    cl = acc['client']
                else:
                    # Fresh login
                    cl.login(acc['username'], os.environ.get('PASS_' + acc['username'], ''))
                    cl.dump_settings(f"session_{acc['username']}.json")

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
                if acc.get('settings') and os.path.exists(acc['settings']):
                    cl.load_settings(acc['settings'])
                    cl.login(acc['username'], '')
                elif 'client' in acc:
                    cl = acc['client']
                else:
                    cl.login(acc['username'], os.environ.get('PASS_' + acc['username'], ''))

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
                                if acc.get('settings') and os.path.exists(acc['settings']):
                                    cl.load_settings(acc['settings'])
                                    cl.login(acc['username'], '')
                                elif 'client' in acc:
                                    cl = acc['client']
                                else:
                                    cl.login(acc['username'], os.environ.get('PASS_' + acc['username'], ''))

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
    app.run(host='0.0.0.0', port=port, debug=False)
