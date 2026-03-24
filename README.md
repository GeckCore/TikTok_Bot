# 🚀 Autonomous TikTok Uploader Bot (2026 Ready)

An advanced, autonomous engine designed to manage, moderate, and upload content to TikTok via Telegram. Powered by **Playwright**, this system utilizes persistent browser contexts to maintain active sessions and mimic human behavior, effectively bypassing modern bot detection.

---

## 🛠️ Choose Your Version

This repository contains two specialized scripts. Choose the one that best fits your workflow:

### 1. `normal_bot.py` (The Hands-Off Experience)
Designed for users who trust their content source or run private bots.
* **Workflow:** Receive video → Queue → Automatic upload every 5-7 hours.
* **Best for:** Personal archives, trusted content streams, or 100% hands-free automation.

### 2. `Bot2.py` (The Shielded Experience)
Designed for public bots or community-driven content where safety is a priority.
* **Workflow:** Receive video → Queue → **1 hour before posting, the bot sends the video to the Admin for Approval/Rejection** → Upload only if approved.
* **Best for:** Public community bots, preventing "bannable" content, and maintaining strict quality control.

---

## 🔥 Key Features

* **🛡️ Admin Moderation:** (Exclusive to `Bot2.py`) Interactive Telegram buttons to approve or discard content before it goes live.
* **⭐ Premium Bypass:** Use `/prem <password>` in the video caption to skip the queue and moderation for instant uploads (60s).
* **🕒 Smart Scheduling:** Randomized intervals (5-7h) to avoid "bot patterns" and protect account health.
* **♻️ Auto-Recovery:** Scans local directories on startup to resume pending tasks after a reboot or crash.
* **🎭 Stealth Engine:** Uses a persistent Chrome profile to eliminate constant logins and solve captchas once.
* **📊 Robust Queue:** Thread-safe `deque` management for high-reliability content handling.

---

## 📋 Prerequisites

* **Python 3.10+**
* **Google Chrome** installed on the host machine.
* **Telegram Bot Token** (Obtained from [@BotFather](https://t.me/botfather)).
* **Your Telegram ID** (Obtained from [@userinfobot](https://t.me/userinfobot)).

---

## ⚙️ Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/GeckCore/TikTok_Bot.git](https://github.com/GeckCore/TikTok_Bot.git)
   cd TikTok_Bot
