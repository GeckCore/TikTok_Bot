import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import time
import threading
import random
from collections import deque
from playwright.sync_api import sync_playwright

# --- CONFIG ---
BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
ADMIN_ID = "YOUR_TELEGRAM_USER_ID"
PASS_PREM = "1234"
HEADLESS_MODE = False 

PATH_BASE = os.path.dirname(os.path.abspath(__file__))
VID_FOLDER = os.path.join(PATH_BASE, 'queue_videos')
CHROME_DATA = os.path.join(PATH_BASE, "browser_session")

# Sync & Queues
lock = threading.Lock()
video_queue = deque()
approval_state = {"status": "IDLE"}

if not os.path.exists(VID_FOLDER):
    os.makedirs(VID_FOLDER)

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

def reload_queue():
    files = [f for f in os.listdir(VID_FOLDER) if f.endswith('.mp4')]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(VID_FOLDER, x)))
    for f in files:
        path = os.path.join(VID_FOLDER, f)
        if path not in video_queue:
            video_queue.append(path)
    if video_queue:
        print(f">> Restore: {len(video_queue)} items found in folder.")

def request_moderation(vid_path):
    approval_state["status"] = "WAITING"
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Post", callback_data="ok"),
        InlineKeyboardButton("❌ Bin", callback_data="no")
    )
    
    try:
        with open(vid_path, 'rb') as v:
            bot.send_video(
                ADMIN_ID, v, 
                caption=f"🛡️ MODERATION\nFile: {os.path.basename(vid_path)}\nNext slot in 1 hour.", 
                reply_markup=kb
            )
    except Exception as e:
        print(f"!! Admin alert failed: {e}")
        approval_state["status"] = "ERROR"

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if approval_state["status"] != "WAITING":
        return
        
    if call.data == "ok":
        approval_state["status"] = "APPROVED"
        bot.edit_message_caption("✅ Approved. Posting in 60min.", call.message.chat.id, call.message.message_id)
    elif call.data == "no":
        approval_state["status"] = "REJECTED"
        bot.edit_message_caption("❌ Rejected and deleted.", call.message.chat.id, call.message.message_id)

def upload_engine(vid_path, priority=False):
    tag = "PREM" if priority else "STD"
    
    if not os.path.exists(vid_path): return

    with lock:
        print(f"\n[RUN] [{tag}] Uploading: {os.path.basename(vid_path)}")
        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=CHROME_DATA,
                    headless=HEADLESS_MODE,
                    channel="chrome",
                    args=["--disable-blink-features=AutomationControlled"]
                )
                
                page = ctx.new_page()
                page.goto("https://www.tiktok.com/creator-center/upload?lang=en", timeout=60000)
                page.wait_for_timeout(5000)
                
                if "login" in page.url:
                    print(f"!! [{tag}] Session expired. Auth required.")
                    if not priority: video_queue.appendleft(vid_path)
                    ctx.close()
                    return

                page.locator("input[type='file']").set_input_files(vid_path)
                btn = page.locator('button:has-text("Post")').first
                btn.wait_for(state="visible", timeout=30000)
                
                for _ in range(300):
                    if not btn.is_disabled(): break
                    time.sleep(1)
                
                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)
                btn.click(force=True)
                
                btn.wait_for(state="hidden", timeout=120000)
                print(f">> [{tag}] Success: Posted.")
                time.sleep(4)
                ctx.close()

                if os.path.exists(vid_path):
                    os.remove(vid_path)

        except Exception as e:
            print(f"!! [{tag}] Engine error: {e}")
            if not priority: video_queue.appendleft(vid_path)

def scheduler_loop():
    while True:
        wait_time = random.randint(18000, 25200)
        pre_wait = wait_time - 3600
        
        print(f"** Next slot in {wait_time/3600:.2f}h. Moderation in {pre_wait/3600:.2f}h.")
        time.sleep(pre_wait)
        
        target_vid = None
        while video_queue:
            current = video_queue.popleft()
            request_moderation(current)
            
            while approval_state["status"] == "WAITING":
                time.sleep(2)
                
            if approval_state["status"] == "APPROVED":
                target_vid = current
                approval_state["status"] = "IDLE"
                break
            elif approval_state["status"] == "REJECTED":
                if os.path.exists(current): os.remove(current)
                approval_state["status"] = "IDLE"
            elif approval_state["status"] == "ERROR":
                video_queue.appendleft(current)
                approval_state["status"] = "IDLE"
                break

        if target_vid:
            time.sleep(3600)
            upload_engine(target_vid)
        else:
            time.sleep(3600)

@bot.message_handler(content_types=['video', 'document'])
def handle_incoming_video(message):
    try:
        f_id = message.video.file_id if message.video else message.document.file_id
        f_info = bot.get_file(f_id)
        downloaded = bot.download_file(f_info.file_path)
        
        save_path = os.path.join(VID_FOLDER, f"v_{int(time.time())}.mp4")
        with open(save_path, 'wb') as f:
            f.write(downloaded)
        
        cap = message.caption if message.caption else ""
        if f"/prem {PASS_PREM}" in cap:
            bot.reply_to(message, "⭐ PREM: Skip mod. Uploading now.")
            threading.Thread(target=lambda: (time.sleep(60), upload_engine(save_path, True)), daemon=True).start()
        else:
            video_queue.append(save_path)
            bot.reply_to(message, f"✅ Queued. Position: {len(video_queue)}")
    except Exception as e:
        print(f"!! Error: {e}")

if __name__ == "__main__":
    reload_queue()
    threading.Thread(target=scheduler_loop, daemon=True).start()
    print(">> Service Live.")
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except:
            time.sleep(5)
