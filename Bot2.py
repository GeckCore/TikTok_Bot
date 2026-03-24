import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import time
import threading
import random
from collections import deque
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
API_TOKEN = 'YOUR_BOT_TOKEN_HERE'
ADMIN_ID = "YOUR_TELEGRAM_ID_HERE"
ACCESS_KEY = "1234"
HEADLESS = False  # Set to True for server deployment

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(BASE_PATH, 'cola_videos')
SESSION_DIR = os.path.join(BASE_PATH, "tiktok_session")

# Global instances
bot = telebot.TeleBot(API_TOKEN, threaded=True)
queue = deque()
io_lock = threading.Lock()
approval_state = {"status": "IDLE"}

if not os.path.exists(VIDEO_DIR):
    os.makedirs(VIDEO_DIR)

# --- UTILS ---
def sync_local_queue():
    """Initial scan to recover pending videos on startup."""
    files = [f for f in os.listdir(VIDEO_DIR) if f.endswith('.mp4')]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(VIDEO_DIR, x)))
    for f in files:
        full_path = os.path.join(VIDEO_DIR, f)
        if full_path not in queue:
            queue.append(full_path)
    if queue:
        print(f"[*] Queue synced: {len(queue)} items ready.")

# --- TELEGRAM MODERATION ---
def dispatch_moderation(file_path):
    approval_state["status"] = "PENDING"
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Approve", callback_data="post_ok"),
        InlineKeyboardButton("❌ Discard", callback_data="post_no")
    )
    
    try:
        with open(file_path, 'rb') as video:
            bot.send_video(
                ADMIN_ID, video, 
                caption=f"🛡️ MODERATION REQUIRED\nFile: {os.path.basename(file_path)}\nSlot: T-60min", 
                reply_markup=kb
            )
    except Exception as e:
        print(f"[!] Alert failed: {e}")
        approval_state["status"] = "ERROR"

@bot.callback_query_handler(func=lambda call: True)
def handle_approval(call):
    if approval_state["status"] != "PENDING":
        bot.answer_callback_query(call.id, "Request expired.")
        return
        
    if call.data == "post_ok":
        approval_state["status"] = "APPROVED"
        bot.edit_message_caption("✅ Approved. Publishing in 1h.", call.message.chat.id, call.message.message_id)
    elif call.data == "post_no":
        approval_state["status"] = "REJECTED"
        bot.edit_message_caption("❌ Discarded. Moving to next.", call.message.chat.id, call.message.message_id)

# --- CORE UPLOADER ---
def tiktok_executor(video_path, is_priority=False):
    tag = "PRIORITY" if is_priority else "NORMAL"
    
    if not os.path.exists(video_path): return

    with io_lock:
        print(f"\n[ENGINE] [{tag}] Uploading: {os.path.basename(video_path)}")
        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=SESSION_DIR,
                    headless=HEADLESS,
                    channel="chrome",
                    args=["--disable-blink-features=AutomationControlled"]
                )
                
                page = ctx.new_page()
                page.goto("https://www.tiktok.com/creator-center/upload?lang=en", timeout=60000)
                page.wait_for_timeout(5000)
                
                if "login" in page.url:
                    print(f"[!] [{tag}] Error: Active session not found.")
                    if not is_priority: queue.appendleft(video_path)
                    ctx.close()
                    return

                page.locator("input[type='file']").set_input_files(video_path)
                btn_post = page.locator('button:has-text("Post"), button:has-text("Publicar")').first
                btn_post.wait_for(state="visible", timeout=30000)
                
                # Polling for upload completion
                for _ in range(300):
                    if not btn_post.is_disabled(): break
                    time.sleep(1)
                
                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)
                btn_post.click(force=True)
                
                btn_post.wait_for(state="hidden", timeout=120000)
                print(f"[SUCCESS] [{tag}] Content live.")
                time.sleep(4)
                ctx.close()

                if os.path.exists(video_path):
                    os.remove(video_path)

        except Exception as e:
            print(f"[ERROR] [{tag}] Runtime error: {e}")
            if not is_priority: queue.appendleft(video_path)

# --- SCHEDULING ---
def scheduler_loop():
    while True:
        delay = random.randint(18000, 25200) # 5-7h
        pre_post_window = delay - 3600
        
        print(f"[*] Next slot in {delay/3600:.2f}h. Reviewing in {pre_post_window/3600:.2f}h.")
        time.sleep(pre_post_window)
        
        selected_vid = None
        while queue:
            candidate = queue.popleft()
            dispatch_moderation(candidate)
            
            while approval_state["status"] == "PENDING":
                time.sleep(2)
                
            if approval_state["status"] == "APPROVED":
                selected_vid = candidate
                approval_state["status"] = "IDLE"
                break
            elif approval_state["status"] == "REJECTED":
                if os.path.exists(candidate): os.remove(candidate)
                approval_state["status"] = "IDLE"
            elif approval_state["status"] == "ERROR":
                queue.appendleft(candidate)
                approval_state["status"] = "IDLE"
                break

        if selected_vid:
            time.sleep(3600)
            tiktok_executor(selected_vid)
        else:
            time.sleep(3600)

# --- TELEGRAM HANDLERS ---
@bot.message_handler(content_types=['video', 'document'])
def on_video_received(message):
    try:
        f_id = message.video.file_id if message.video else message.document.file_id
        f_info = bot.get_file(f_id)
        raw_data = bot.download_file(f_info.file_path)
        
        f_path = os.path.join(VIDEO_DIR, f"v_{int(time.time())}.mp4")
        with open(f_path, 'wb') as f:
            f.write(raw_data)
        
        caption = message.caption or ""
        if f"/prem {ACCESS_KEY}" in caption:
            bot.reply_to(message, "⭐ Priority access. Posting in 60s...")
            threading.Thread(target=lambda: (time.sleep(60), tiktok_executor(f_path, True)), daemon=True).start()
        else:
            queue.append(f_path)
            bot.reply_to(message, f"✅ Added to queue. Position: {len(queue)}")
            
    except Exception as e:
        print(f"Recv error: {e}")

if __name__ == "__main__":
    print("--- TIKTOK AUTOMATION SERVICE STARTING ---")
    sync_local_queue()
    threading.Thread(target=scheduler_loop, daemon=True).start()
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except:
            time.sleep(5)
