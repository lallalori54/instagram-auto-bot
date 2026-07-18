from flask import Flask, request, render_template_string, jsonify, session
import os
import json
import time
import logging
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== HTML TEMPLATE ====================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram Auto Poster</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: #fafafa;
            padding: 20px;
            color: #262626;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        h1 {
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 25px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        h1 span { background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); 
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            border: 1px solid #dbdbdb;
        }
        .card h3 {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 12px;
            color: #262626;
        }
        .card p {
            font-size: 14px;
            color: #8e8e8e;
            margin-bottom: 12px;
        }
        label {
            font-size: 14px;
            font-weight: 500;
            display: block;
            margin-bottom: 4px;
            color: #262626;
        }
        input, textarea, select {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #dbdbdb;
            border-radius: 8px;
            font-size: 14px;
            background: #fafafa;
            transition: border 0.2s;
            font-family: inherit;
        }
        input:focus, textarea:focus, select:focus {
            outline: none;
            border-color: #0095f6;
            background: white;
        }
        textarea { resize: vertical; min-height: 60px; }
        button {
            background: #0095f6;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
            margin-top: 8px;
        }
        button:hover { background: #0077cc; }
        button.danger { background: #dc3545; }
        button.danger:hover { background: #b02a37; }
        button.success { background: #28a745; }
        button.success:hover { background: #1e7e34; }
        button:disabled { opacity: 0.6; cursor: not-allowed; }
        .row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        .account-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 14px;
            background: #f8f9fa;
            border-radius: 8px;
            margin-bottom: 6px;
            border-left: 4px solid #28a745;
        }
        .account-item.inactive {
            border-left-color: #dc3545;
            opacity: 0.6;
        }
        .account-item .username {
            font-weight: 500;
        }
        .account-item .status {
            font-size: 12px;
            padding: 2px 10px;
            border-radius: 12px;
            background: #e8f5e9;
            color: #2e7d32;
        }
        .account-item .status.inactive {
            background: #fbe9e7;
            color: #c62828;
        }
        .account-item .remove-btn {
            background: none;
            border: none;
            color: #dc3545;
            cursor: pointer;
            font-size: 16px;
            padding: 0 5px;
        }
        .account-item .remove-btn:hover { color: #b02a37; }
        .badge {
            font-size: 12px;
            padding: 2px 10px;
            border-radius: 12px;
            background: #e3f2fd;
            color: #0d47a1;
        }
        .msg {
            padding: 10px 14px;
            border-radius: 8px;
            margin-top: 10px;
            font-size: 14px;
        }
        .msg.success { background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }
        .msg.error { background: #fbe9e7; color: #c62828; border: 1px solid #ffcdd2; }
        .msg.info { background: #e3f2fd; color: #0d47a1; border: 1px solid #bbdefb; }
        .hidden { display: none; }
        .mt-10 { margin-top: 10px; }
        .flex { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
        .file-input-wrapper {
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }
        .file-input-wrapper input[type="file"] {
            width: auto;
            padding: 8px;
            background: white;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 12px;
            margin-bottom: 10px;
        }
        .stat-box {
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-box .num {
            font-size: 24px;
            font-weight: 700;
            color: #0095f6;
        }
        .stat-box .label {
            font-size: 12px;
            color: #8e8e8e;
        }
        @media (max-width: 600px) {
            .row { grid-template-columns: 1fr; }
            .flex { flex-direction: column; }
            .file-input-wrapper { flex-direction: column; }
        }
    </style>
</head>
<body>
<div class="container">
    <h1>📸 <span>Instagram Auto Poster</span></h1>

    <!-- Stats -->
    <div class="card">
        <div class="stats">
            <div class="stat-box">
                <div class="num">{{ accounts|length }}</div>
                <div class="label">Total Accounts</div>
            </div>
            <div class="stat-box">
                <div class="num">{{ active_accounts }}</div>
                <div class="label">Active</div>
            </div>
            <div class="stat-box">
                <div class="num">{{ posts_today }}</div>
                <div class="label">Posts Today</div>
            </div>
        </div>
    </div>

    <!-- Add Account via Cookie -->
    <div class="card">
        <h3>➕ Add Account via Cookie</h3>
        <p>Browser se <strong>sessionid</strong>, <strong>csrftoken</strong>, <strong>ds_user_id</strong> cookies copy karein.</p>
        <p style="font-size: 12px; color: #999;">How to get: Chrome DevTools → Application → Cookies → instagram.com</p>
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
                    <button class="remove-btn" onclick="removeAccount('{{ acc.username }}')" title="Remove">✕</button>
                </div>
            {% else %}
                <p style="color: #8e8e8e;">No accounts added yet. Add one above!</p>
            {% endfor %}
        </div>
    </div>

    <!-- Post Video -->
    <div class="card">
        <h3>📤 Post Video</h3>
        <div class="row">
            <div>
                <label>Video URL (public link)</label>
                <input type="text" id="videoUrl" placeholder="https://example.com/video.mp4">
            </div>
            <div>
                <label>Or Upload File</label>
                <div class="file-input-wrapper">
                    <input type="file" id="videoFile" accept="video/*">
                    <button class="success" onclick="uploadFile()">Upload</button>
                </div>
            </div>
        </div>
        <div class="mt-10">
            <label>Caption</label>
            <textarea id="caption" rows="3" placeholder="Write your caption here... #instagram #auto"></textarea>
        </div>
        <div class="flex mt-10">
            <button onclick="postVideo()">📤 Post Now</button>
            <button onclick="postVideoAll()" class="success">📤 Post to All (with delay)</button>
            <button onclick="postStory()" class="success">📸 Post as Story</button>
        </div>
        <div id="postMsg" class="hidden"></div>
    </div>

    <!-- Schedule -->
    <div class="card">
        <h3>⏰ Schedule Post</h3>
        <div class="row">
            <div>
                <label>Video URL</label>
                <input type="text" id="schedVideoUrl" placeholder="https://example.com/video.mp4">
            </div>
            <div>
                <label>Time (24hr format)</label>
                <input type="time" id="schedTime" value="08:00">
            </div>
        </div>
        <div class="mt-10">
            <label>Caption</label>
            <textarea id="schedCaption" rows="2" placeholder="Caption for scheduled post"></textarea>
        </div>
        <button onclick="schedulePost()">⏰ Schedule Post</button>
        <div id="schedMsg" class="hidden"></div>
    </div>

    <!-- Scheduled Jobs -->
    <div class="card">
        <h3>📅 Scheduled Jobs</h3>
        <div id="scheduledList">
            {% for job in scheduled_jobs %}
                <div class="account-item">
                    <span>{{ job.time }} - {{ job.video_url[:30] }}...</span>
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
// ========== Add Account ==========
function addAccount() {
    const data = document.getElementById('cookieInput').value;
    const msgEl = document.getElementById('addMsg');
    msgEl.className = 'hidden';
    
    if (!data.trim()) {
        showMsg('addMsg', 'Please paste cookie data', 'error');
        return;
    }
    
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
    .catch(err => showMsg('addMsg', '❌ Error: ' + err, 'error'));
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

// ========== Post Video ==========
function postVideo() {
    const url = document.getElementById('videoUrl').value;
    const caption = document.getElementById('caption').value;
    if (!url) { alert('Please enter video URL'); return; }
    doPost('/post_video', {video_url: url, caption: caption});
}

function postVideoAll() {
    const url = document.getElementById('videoUrl').value;
    const caption = document.getElementById('caption').value;
    if (!url) { alert('Please enter video URL'); return; }
    if (!confirm('Post to ALL accounts with 30s delay?')) return;
    doPost('/post_video_all', {video_url: url, caption: caption});
}

function postStory() {
    const url = document.getElementById('videoUrl').value;
    if (!url) { alert('Please enter video URL'); return; }
    doPost('/post_story', {video_url: url});
}

function doPost(endpoint, data) {
    const msgEl = document.getElementById('postMsg');
    msgEl.className = 'hidden';
    showMsg('postMsg', '⏳ Processing...', 'info');
    
    fetch(endpoint, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            showMsg('postMsg', '✅ ' + data.message, 'success');
        } else {
            showMsg('postMsg', '❌ ' + data.message, 'error');
        }
    })
    .catch(err => showMsg('postMsg', '❌ Error: ' + err, 'error'));
}

// ========== Upload File ==========
function uploadFile() {
    const fileInput = document.getElementById('videoFile');
    const file = fileInput.files[0];
    if (!file) { alert('Select a video file first'); return; }
    
    const formData = new FormData();
    formData.append('video', file);
    
    const msgEl = document.getElementById('postMsg');
    msgEl.className = 'hidden';
    showMsg('postMsg', '⏳ Uploading...', 'info');
    
    fetch('/upload_video', {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            document.getElementById('videoUrl').value = data.url;
            showMsg('postMsg', '✅ Uploaded! URL: ' + data.url, 'success');
        } else {
            showMsg('postMsg', '❌ ' + data.message, 'error');
        }
    })
    .catch(err => showMsg('postMsg', '❌ Error: ' + err, 'error'));
}

// ========== Schedule ==========
function schedulePost() {
    const url = document.getElementById('schedVideoUrl').value;
    const time = document.getElementById('schedTime').value;
    const caption = document.getElementById('schedCaption').value;
    if (!url || !time) { alert('Video URL and time required'); return; }
    
    fetch('/schedule_post', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({video_url: url, time: time, caption: caption})
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

# ==================== In-Memory Storage ====================
accounts = []  # List of {username, settings, valid}
scheduled_jobs = []  # List of {video_url, time, caption, status}
posts_today = 0
post_date = datetime.now().date()

# ==================== Helper Functions ====================
def get_active_accounts():
    """Return list of valid accounts"""
    return [acc for acc in accounts if acc.get('valid', False)]

def get_username_from_settings(settings):
    """Extract username from settings or by API call"""
    try:
        cl = Client()
        cl.set_settings(settings)
        return cl.get_username()
    except:
        return None

def test_session(settings):
    """Test if session is valid"""
    try:
        cl = Client()
        cl.set_settings(settings)
        cl.get_user_id()
        return True
    except:
        return False

def post_video_to_account(settings, video_url, caption):
    """Post video to single account using settings"""
    try:
        cl = Client()
        cl.set_settings(settings)
        cl.get_user_id()  # Verify session
        result = cl.clip_upload(video_url, caption)
        return True, "Success"
    except Exception as e:
        return False, str(e)

def post_story_to_account(settings, video_url):
    """Post story to single account"""
    try:
        cl = Client()
        cl.set_settings(settings)
        cl.get_user_id()
        result = cl.video_upload_to_story(video_url)
        return True, "Success"
    except Exception as e:
        return False, str(e)

# ==================== Routes ====================

@app.route('/')
def index():
    global posts_today, post_date
    # Reset daily counter
    today = datetime.now().date()
    if post_date != today:
        posts_today = 0
        post_date = today
    
    active = len(get_active_accounts())
    return render_template_string(
        HTML_TEMPLATE, 
        accounts=accounts,
        active_accounts=active,
        posts_today=posts_today,
        scheduled_jobs=scheduled_jobs
    )

@app.route('/add_account', methods=['POST'])
def add_account():
    try:
        data = request.json.get('cookie_data')
        
        # Parse if string
        if isinstance(data, str):
            try:
                cookie_dict = json.loads(data)
            except:
                # Try to extract from raw string
                cookie_dict = {}
                for key in ['sessionid', 'csrftoken', 'ds_user_id']:
                    match = re.search(f'"{key}"\\s*:\\s*"([^"]+)"', data)
                    if match:
                        cookie_dict[key] = match.group(1)
        else:
            cookie_dict = data
        
        # Validate required
        required = ['sessionid', 'csrftoken', 'ds_user_id']
        missing = [k for k in required if k not in cookie_dict]
        if missing:
            return jsonify({'status': 'error', 'message': f'Missing: {", ".join(missing)}'})
        
        # Test session
        if not test_session(cookie_dict):
            return jsonify({'status': 'error', 'message': 'Invalid session - cookie may be expired'})
        
        # Get username
        username = get_username_from_settings(cookie_dict)
        if not username:
            return jsonify({'status': 'error', 'message': 'Could not get username'})
        
        # Check duplicate
        if any(acc.get('username') == username for acc in accounts):
            return jsonify({'status': 'error', 'message': f'Account @{username} already added'})
        
        accounts.append({
            'username': username,
            'settings': cookie_dict,
            'valid': True
        })
        
        logger.info(f"✅ Added account: @{username}")
        return jsonify({'status': 'success', 'message': f'Account @{username} added successfully!'})
    
    except Exception as e:
        logger.error(f"Error adding account: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/remove_account', methods=['POST'])
def remove_account():
    try:
        username = request.json.get('username')
        global accounts
        accounts = [acc for acc in accounts if acc.get('username') != username]
        logger.info(f"Removed account: @{username}")
        return jsonify({'status': 'success', 'message': f'Removed @{username}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/post_video', methods=['POST'])
def post_video():
    try:
        video_url = request.json.get('video_url')
        caption = request.json.get('caption', '')
        
        if not video_url:
            return jsonify({'status': 'error', 'message': 'Video URL required'})
        
        active = get_active_accounts()
        if not active:
            return jsonify({'status': 'error', 'message': 'No active accounts'})
        
        # Post to first active account only
        acc = active[0]
        success, msg = post_video_to_account(acc['settings'], video_url, caption)
        
        if success:
            global posts_today
            posts_today += 1
            return jsonify({'status': 'success', 'message': f'Posted on @{acc["username"]}'})
        else:
            return jsonify({'status': 'error', 'message': f'Failed on @{acc["username"]}: {msg}'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/post_video_all', methods=['POST'])
def post_video_all():
    try:
        video_url = request.json.get('video_url')
        caption = request.json.get('caption', '')
        
        if not video_url:
            return jsonify({'status': 'error', 'message': 'Video URL required'})
        
        active = get_active_accounts()
        if not active:
            return jsonify({'status': 'error', 'message': 'No active accounts'})
        
        success_count = 0
        failed = []
        
        for acc in active:
            success, msg = post_video_to_account(acc['settings'], video_url, caption)
            if success:
                success_count += 1
                global posts_today
                posts_today += 1
            else:
                failed.append(f"@{acc['username']}: {msg}")
            time.sleep(30)  # Delay to avoid rate limit
        
        message = f"✅ Posted on {success_count}/{len(active)} accounts"
        if failed:
            message += f" | Failed: {', '.join(failed)}"
        
        return jsonify({'status': 'success', 'message': message})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/post_story', methods=['POST'])
def post_story():
    try:
        video_url = request.json.get('video_url')
        if not video_url:
            return jsonify({'status': 'error', 'message': 'Video URL required'})
        
        active = get_active_accounts()
        if not active:
            return jsonify({'status': 'error', 'message': 'No active accounts'})
        
        # Post to first active account
        acc = active[0]
        success, msg = post_story_to_account(acc['settings'], video_url)
        
        if success:
            return jsonify({'status': 'success', 'message': f'Story posted on @{acc["username"]}'})
        else:
            return jsonify({'status': 'error', 'message': f'Failed: {msg}'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

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
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        # Upload to a file hosting service (or just return local path)
        # For demo, we'll use a placeholder
        import urllib.parse
        filename = urllib.parse.quote(file.filename)
        url = f"/uploads/{filename}"
        
        # In production, you'd upload to Cloudinary, AWS S3, etc.
        return jsonify({'status': 'success', 'url': f"https://your-app.com/uploads/{filename}", 'message': 'File uploaded'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/schedule_post', methods=['POST'])
def schedule_post():
    try:
        video_url = request.json.get('video_url')
        time_str = request.json.get('time')
        caption = request.json.get('caption', '')
        
        if not video_url or not time_str:
            return jsonify({'status': 'error', 'message': 'Video URL and time required'})
        
        scheduled_jobs.append({
            'video_url': video_url,
            'time': time_str,
            'caption': caption,
            'status': 'pending'
        })
        
        logger.info(f"Scheduled post at {time_str}")
        return jsonify({'status': 'success', 'message': f'Scheduled at {time_str}'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/remove_job', methods=['POST'])
def remove_job():
    try:
        index = request.json.get('index')
        if isinstance(index, str):
            index = int(index)
        if 0 <= index < len(scheduled_jobs):
            removed = scheduled_jobs.pop(index)
            return jsonify({'status': 'success', 'message': 'Job removed'})
        return jsonify({'status': 'error', 'message': 'Job not found'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# ==================== Run ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
