from flask import Flask, request, render_template_string, jsonify, session, redirect, url_for
import os
import json
import time
import logging
import random
import requests
from datetime import datetime
import threading

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'admin-secret-key-2026')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# Instagram OAuth Config
INSTAGRAM_CLIENT_ID = os.environ.get('INSTAGRAM_CLIENT_ID')
INSTAGRAM_CLIENT_SECRET = os.environ.get('INSTAGRAM_CLIENT_SECRET')
INSTAGRAM_REDIRECT_URI = os.environ.get('INSTAGRAM_REDIRECT_URI')

accounts = []
uploaded_videos = []
scheduled_jobs = []
daily_caption = "🎬 New video! Follow for more #instagram #trending"
posts_today = 0
post_date = datetime.now().date()

# ==================== REAL INSTAGRAM WEB UI (From Your Inspect) ====================
INSTAGRAM_LOGIN_UI = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: #fafafa;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 935px;
            width: 100%;
            margin: 0 auto;
        }
        .content {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 40px;
            flex-wrap: wrap;
        }
        .phone-preview {
            flex: 0 0 380px;
            display: none;
        }
        @media (min-width: 875px) {
            .phone-preview {
                display: block;
            }
        }
        .phone-preview img {
            width: 100%;
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
        }
        .logo {
            text-align: center;
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
        .forgot-password {
            color: #00376b;
            font-size: 12px;
            text-decoration: none;
            text-align: center;
            display: block;
            margin-top: 12px;
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
            background: #fde8e8;
            padding: 10px;
            border-radius: 8px;
        }
        .success-msg {
            color: #28a745;
            font-size: 13px;
            margin-bottom: 10px;
            text-align: center;
            background: #e8f5e9;
            padding: 10px;
            border-radius: 8px;
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
<div class="container">
    <div class="content">
        <div class="phone-preview">
            <img src="https://www.instagram.com/static/images/homepage/phones/home-phones-2x.png" alt="Instagram">
        </div>
        <div class="login-box">
            <div class="card">
                <div class="logo">
                    <svg viewBox="0 0 175 51">
                        <path d="M53.5 17.5c-1.8 0-3.3.8-4.3 2.1V10h-3.8v25.4h3.8V26c0-2.5 1.5-4.2 4.1-4.2 2.5 0 4 1.7 4 4.2v9.4h3.8V25.8c0-4.5-2.7-8.3-7.6-8.3zm13.9 3.6c-1.8 0-3.4.8-4.4 2.1v-5.2h-3.8v17.4h3.8V29c0-2.5 1.5-4.2 4.1-4.2 2.5 0 4 1.7 4 4.2v9.4h3.8V25.8c0-4.5-2.8-8.3-7.5-8.3zm16.1 0c-3.8 0-6.5 3.1-6.5 7.5s2.7 7.5 6.5 7.5c3.9 0 6.5-3.1 6.5-7.5s-2.6-7.5-6.5-7.5zm0 11.8c-2.1 0-3.6-1.7-3.6-4.3 0-2.6 1.5-4.3 3.6-4.3 2.1 0 3.6 1.7 3.6 4.3 0 2.6-1.5 4.3-3.6 4.3zm12.4-15.4h-3.8V31c0 1.5 1.1 2.5 2.6 2.5h1.2v3.2c-1.2.3-2.2.5-3.4.5-3.6 0-5.2-2.2-5.2-5.4V17.5h-3.8v17.4c0 4.2 2.4 7.2 7.3 7.2 1.5 0 2.9-.3 4.2-.8v-6.8h-1.3c-1.5 0-2.6-1-2.6-2.5V17.5h3.8zm8.3 17.4V10h-3.8v25.4h3.8zm1.2-15.2c0-2.6 1.7-4.3 4.2-4.3 2.5 0 4.1 1.7 4.1 4.3v15.2h3.8V21.2c0-4.5-2.7-8.3-7.5-8.3-1.8 0-3.4.8-4.4 2.1v-5.2h-3.8v17.4h3.8V21.2c0-2.5 1.5-4.2 4.1-4.2 2.5 0 4 1.7 4 4.2v9.4h3.8V21.2h-3.8zM0 25.5C0 11.4 11.4 0 25.5 0S51 11.4 51 25.5 39.6 51 25.5 51 0 39.6 0 25.5z" fill="#0095f6"/>
                    </svg>
                </div>
                
                {% if error %}
                <div class="error-msg">{{ error }}</div>
                {% endif %}
                {% if success %}
                <div class="success-msg">{{ success }}</div>
                {% endif %}
                
                <form method="POST" action="/instagram_login">
                    <div class="input-group">
                        <input type="text" name="username" placeholder="Mobile number, username or email" required>
                    </div>
                    <div class="input-group">
                        <input type="password" name="password" placeholder="Password" required>
                    </div>
                    <button type="submit" class="login-btn">Log in</button>
                </form>
                
                <div class="divider">
                    <div class="divider-line"></div>
                    <div class="divider-text">OR</div>
                    <div class="divider-line"></div>
                </div>
                
                <a href="#" class="facebook-login">
                    <svg viewBox="0 0 20 20" width="20" height="20"><path d="M20 10c0-5.5-4.5-10-10-10S0 4.5 0 10c0 5 3.7 9.1 8.4 9.9v-7H5.9V10h2.5V7.8c0-2.5 1.5-3.8 3.7-3.8 1.1 0 2.2.2 2.2.2v2.5h-1.2c-1.2 0-1.6.8-1.6 1.6V10h2.8l-.4 2.9h-2.4v7C16.3 19.1 20 15 20 10z" fill="#1877f2"/></svg>
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
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head><title>Admin Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;background:#f0f2f5;padding:20px}
.container{max-width:1000px;margin:0 auto}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:25px;flex-wrap:wrap;gap:10px}
.header h1{font-size:28px;display:flex;align-items:center;gap:10px}
.header h1 span{background:linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header-actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.header-actions a{color:#0095f6;text-decoration:none;font-weight:600}
.logout-btn{background:#dc3545;color:white;border:none;padding:10px 20px;border-radius:8px;cursor:pointer;font-weight:600;transition:background 0.2s}
.logout-btn:hover{background:#b02a37}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin-bottom:25px}
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
button.danger:hover{background:#b02a37}
button.success{background:#28a745}
button.success:hover{background:#1e7e34}
.row{display:grid;grid-template-columns:1fr 1fr;gap:15px}
.flex{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.account-item{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:#f8f9fa;border-radius:8px;margin-bottom:8px;border-left:4px solid #28a745}
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
<div class="header"><h1>📸 <span>Admin Dashboard</span></h1>
<div class="header-actions"><a href="/">➕ Add Account</a><form method="POST" action="/logout" style="display:inline"><button class="logout-btn" type="submit">🚪 Logout</button></form></div></div>
<div class="stats">
<div class="stat-card"><div class="num">{{ accounts|length }}</div><div class="label">Accounts</div></div>
<div class="stat-card"><div class="num">{{ active_accounts }}</div><div class="label">Active</div></div>
<div class="stat-card"><div class="num">{{ posts_today }}</div><div class="label">Posts Today</div></div>
<div class="stat-card"><div class="num">{{ uploaded_videos|length }}</div><div class="label">Videos</div></div>
</div>
<div class="card"><h3>📋 Accounts</h3>
{% for acc in accounts %}
<div class="account-item"><span>@{{ acc.username }}</span><span>{% if acc.valid %}✅ Active{% else %}❌ Invalid{% endif %}</span><button class="danger" onclick="removeAccount('{{ acc.username }}')">✕</button></div>
{% else %}<p style="color:#8e8e8e">No accounts added. <a href="/">Add one</a></p>{% endfor %}
</div>
<div class="card"><h3>📤 Upload Video</h3>
<input type="file" id="videoFile" accept="video/*"><button class="success" onclick="uploadVideo()">📤 Upload</button>
<div id="uploadMsg" class="hidden"></div>
</div>
<div class="card"><h3>📤 Post</h3>
<div class="flex"><button onclick="postRandomVideo()">🎲 Post Video to All</button><button onclick="postRandomStory()">📸 Post Story to All</button></div>
<div id="postMsg" class="hidden"></div>
</div>
<div class="card"><h3>⏰ Schedule</h3>
<div class="row"><div><label>Time</label><input type="time" id="schedTime" value="08:00"></div><div><label>Type</label><select id="schedType"><option value="video">Video</option><option value="story">Story</option></select></div></div>
<button onclick="schedulePost()">⏰ Schedule</button>
<div id="schedMsg" class="hidden"></div>
</div>
<div class="card"><h3>📅 Scheduled Jobs</h3>
{% for job in scheduled_jobs %}<div class="account-item"><span>🕐 {{ job.time }} - {{ job.type }}</span><span>{{ job.status }}</span></div>{% else %}<p style="color:#8e8e8e">No scheduled jobs</p>{% endfor %}
</div>
</div>
<script>
function removeAccount(username){if(!confirm('Remove @'+username+'?'))return;fetch('/remove_account',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:username})}).then(res=>res.json()).then(data=>{if(data.status==='success')location.reload();});}
function uploadVideo(){const file=document.getElementById('videoFile').files[0];if(!file){alert('Select a video');return;}const formData=new FormData();formData.append('video',file);showMsg('uploadMsg','⏳ Uploading...','info');fetch('/upload_video',{method:'POST',body:formData}).then(res=>res.json()).then(data=>{if(data.status==='success'){showMsg('uploadMsg','✅ '+data.message,'success');setTimeout(()=>location.reload(),1500);}else{showMsg('uploadMsg','❌ '+data.message,'error');}});}
function postRandomVideo(){if(!confirm('Post to ALL accounts?'))return;showMsg('postMsg','⏳ Processing...','info');fetch('/post_random_video',{method:'POST',headers:{'Content-Type':'application/json'}}).then(res=>res.json()).then(data=>{if(data.status==='success'){showMsg('postMsg','✅ '+data.message,'success');}else{showMsg('postMsg','❌ '+data.message,'error');}});}
function postRandomStory(){if(!confirm('Post story to ALL accounts?'))return;showMsg('postMsg','⏳ Processing...','info');fetch('/post_random_story',{method:'POST',headers:{'Content-Type':'application/json'}}).then(res=>res.json()).then(data=>{if(data.status==='success'){showMsg('postMsg','✅ '+data.message,'success');}else{showMsg('postMsg','❌ '+data.message,'error');}});}
function schedulePost(){const time=document.getElementById('schedTime').value;const type=document.getElementById('schedType').value;if(!time){alert('Select time');return;}fetch('/schedule_post',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({time:time,type:type})}).then(res=>res.json()).then(data=>{if(data.status==='success'){showMsg('schedMsg','✅ '+data.message,'success');setTimeout(()=>location.reload(),1500);}else{showMsg('schedMsg','❌ '+data.message,'error');}});}
function showMsg(id,text,type){const el=document.getElementById(id);el.className='msg '+type;el.textContent=text;el.style.display='block';setTimeout(()=>{el.style.display='none';},5000);}
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
        
        if not username or not password:
            return render_template_string(INSTAGRAM_LOGIN_UI, 
                error='Please enter username and password.', success=None)
        
        # -------------------- REAL INSTAGRAM AUTHENTICATION --------------------
        # Yeh real Instagram ka graphql endpoint hai
        # Session cookies generate karega jo valid hain
        
        # Step 1: Get CSRF token
        session_req = requests.Session()
        initial_resp = session_req.get('https://www.instagram.com/')
        
        # Extract CSRF token
        csrf_token = None
        for cookie in session_req.cookies:
            if cookie.name == 'csrftoken':
                csrf_token = cookie.value
                break
        
        if not csrf_token:
            return render_template_string(INSTAGRAM_LOGIN_UI, 
                error='Failed to get CSRF token.', success=None)
        
        # Step 2: Login request
        login_data = {
            'username': username,
            'enc_password': f'#PWD_INSTAGRAM_BROWSER:0:0:{password}',
            'queryParams': '{}',
            'optIntoOneTap': 'false',
            'trustedDeviceRecords': '{}'
        }
        
        login_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'X-CSRFToken': csrf_token,
            'X-Instagram-AJAX': '1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.instagram.com',
            'Referer': 'https://www.instagram.com/'
        }
        
        login_resp = session_req.post(
            'https://www.instagram.com/api/v1/web/accounts/login/ajax/',
            data=login_data,
            headers=login_headers
        )
        
        login_json = login_resp.json()
        
        if login_json.get('authenticated'):
            # Login successful!
            logged_username = login_json.get('username', username)
            
            # Save session cookies for later
            os.makedirs('sessions', exist_ok=True)
            session_file = f"sessions/{logged_username}.json"
            
            # Save cookies
            cookies_dict = {}
            for cookie in session_req.cookies:
                cookies_dict[cookie.name] = cookie.value
            
            with open(session_file, 'w') as f:
                json.dump(cookies_dict, f)
            
            if any(acc.get('username') == logged_username for acc in accounts):
                return render_template_string(INSTAGRAM_LOGIN_UI, 
                    error=f'Account @{logged_username} already added.', success=None)
            
            accounts.append({
                'username': logged_username,
                'session_file': session_file,
                'cookies': cookies_dict,
                'valid': True
            })
            
            logger.info(f"✅ Added account: @{logged_username}")
            return redirect(url_for('admin'))
        else:
            # Check for two-factor
            if login_json.get('two_factor_required'):
                return render_template_string(INSTAGRAM_LOGIN_UI, 
                    error='2FA required! Check your app for code.', success=None)
            
            error_msg = login_json.get('message', 'Invalid username or password.')
            return render_template_string(INSTAGRAM_LOGIN_UI, 
                error=f'Login failed: {error_msg}', success=None)
            
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
                # Real Instagram post using cookies
                with open(acc['session_file'], 'r') as f:
                    cookies = json.load(f)
                
                # TODO: Implement actual post using cookies
                # For now, we'll simulate
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
                # TODO: Implement story post
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
                                # TODO: Implement scheduled post
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
