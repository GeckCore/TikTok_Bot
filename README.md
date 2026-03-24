# 🚀 Autonomous TikTok Uploader Bot (Telegram Integrated)

An intelligent, autonomous system designed to manage, moderate, and upload videos to TikTok via Telegram. This bot uses **Playwright** with persistent browser contexts to mimic human behavior and maintain active sessions, bypassing modern bot detection (2026 Ready).

---

## 🔥 Key Features

* **🛡️ Admin Moderation Flow:** Every video in the normal queue is sent to the Admin 1 hour before posting for approval or rejection via interactive Telegram buttons.
* **⭐ Premium Mode:** Bypass the moderation queue and upload videos instantly using a custom password (`/prem`).
* **🕒 Randomized Scheduling:** Normal uploads are intelligently spaced (5 to 7 hours) to maintain account health and avoid "bot" patterns.
* **♻️ Auto-Recovery System:** Scans the local directory on startup to resume the queue automatically if the system or server restarts.
* **🎭 Stealth Engine:** Uses Playwright with a persistent Chrome profile, reducing captchas and eliminating the need for constant logins.
* **📊 FIFO Queue Management:** Videos are processed in order of arrival using a robust, thread-safe deque system.

---

## 🛠️ Prerequisites

* **Python 3.10+**
* **Google Chrome / Microsoft Edge** installed on the host machine.
* **Telegram Bot Token** (Obtained from [@BotFather](https://t.me/botfather)).
* **Your Telegram ID** (Obtained from [@userinfobot](https://t.me/userinfobot)).

---

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/GeckCore/TikTok_Bot.git](https://github.com/GeckCore/TikTok_Bot.git)
   cd TikTok_Bot
