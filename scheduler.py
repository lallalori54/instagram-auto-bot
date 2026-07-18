import os
import time
import json
import logging
from datetime import datetime
from instagrapi import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
ACCOUNTS_JSON = os.environ.get('INSTAGRAM_ACCOUNTS', '[]')
VIDEO_URL = os.environ.get('VIDEO_URL', '')
CAPTION = os.environ.get('CAPTION', 'Auto-posted video #instagram #automation')

def load_accounts():
    """Load accounts from environment variable"""
    try:
        return json.loads(ACCOUNTS_JSON)
    except:
        return []

def post_video(settings, video_url, caption):
    """Post video to single account"""
    try:
        cl = Client()
        cl.set_settings(settings)
        cl.get_user_id()
        result = cl.clip_upload(video_url, caption)
        return True, "Success"
    except Exception as e:
        return False, str(e)

def main():
    accounts = load_accounts()
    
    if not accounts:
        logger.info("No accounts found. Set INSTAGRAM_ACCOUNTS environment variable.")
        return
    
    if not VIDEO_URL:
        logger.info("No VIDEO_URL set. Set VIDEO_URL environment variable.")
        return
    
    logger.info(f"📤 Posting to {len(accounts)} accounts at {datetime.now()}")
    
    success_count = 0
    failed = []
    
    for acc in accounts:
        settings = acc.get('settings', {})
        username = acc.get('username', 'unknown')
        
        success, msg = post_video(settings, VIDEO_URL, CAPTION)
        if success:
            success_count += 1
            logger.info(f"✅ Posted on @{username}")
        else:
            failed.append(f"@{username}: {msg}")
            logger.error(f"❌ Failed on @{username}: {msg}")
        
        time.sleep(30)
    
    logger.info(f"✅ Done! Posted on {success_count}/{len(accounts)} accounts")
    if failed:
        logger.info(f"Failed: {', '.join(failed)}")

if __name__ == '__main__':
    main()
