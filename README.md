# 🚀 Autonomous TikTok Uploader Bot (Telegram Integrated)

An intelligent, autonomous system designed to manage, moderate, and upload videos to TikTok via Telegram. This bot uses **Playwright** with persistent browser contexts to mimic human behavior and maintain active sessions, bypassing modern bot detection.

---

## 🔥 Key Features

* **🛡️ Admin Moderation:** Every video in the normal queue is sent to the Admin 1 hour before posting for approval or rejection.
* **⭐ Premium Mode:** Bypass the moderation queue and upload videos instantly with a custom password.
* **🕒 Randomized Scheduling:** Normal uploads are spaced between 5 to 7 hours to maintain account health.
* **♻️ Auto-Recovery:** Scans the local directory on startup to resume the queue if the system restarts.
* **🎭 Stealth Engine:** Uses Playwright with a persistent Chrome profile to avoid constant logins and captchas.
* **📊 FIFO Queue:** Videos are processed in order of arrival using a robust deque system.

---

## 🛠️ Prerequisites

* **Python 3.10+**
* **Google Chrome** (installed on the host machine)
* **Telegram Bot Token** (from [@BotFather](https://t.me/botfather))
* **Your Telegram ID** (get it from [@userinfobot](https://t.me/userinfobot))

---

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YourUsername/TikTok-Auto-Uploader.git](https://github.com/YourUsername/TikTok-Auto-Uploader.git)
   cd TikTok-Auto-Uploader
