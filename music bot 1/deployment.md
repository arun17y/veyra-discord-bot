# 🚀 SHADOW CHEATS MUSIC — Deployment & Production Hosting Guide

This guide details how to deploy the bot to a production hosting environment (such as a Linux VPS, Windows server, Docker container, or PM2 process manager) to keep the music bot running 24/7.

---

## 🛠️ Prerequisites & Port Openings

1.  **Server Requirements**: 
    *   Dual-core CPU, minimum 1GB RAM.
    *   Stable outbound network connection to Discord gateway and YouTube CDNs.
2.  **Required Tools**:
    *   Python 3.10 or 3.11
    *   FFmpeg (ensured in PATH or within the local `ffmpeg/bin` directory)
    *   Node.js (for `yt-dlp` cipher execution)

---

## 📥 Option A: Deploying on Linux VPS (systemd service)
Recommended for standard VPS providers (DigitalOcean, Linode, AWS EC2, Hetzner, etc.).

1.  **Clone or Copy files**:
    Transfer your bot directory to the server path: `/home/ubuntu/shadow-cheats-music`.

2.  **Install dependencies**:
    ```bash
    sudo apt update && sudo apt install -y python3 python3-pip python3-venv ffmpeg nodejs
    cd /home/ubuntu/shadow-cheats-music
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Setup System Service Manager**:
    Create a systemd unit file to auto-restart the bot on server restarts:
    ```bash
    sudo nano /etc/systemd/system/shadowcheats.service
    ```

    Paste the following configuration:
    ```ini
    [Unit]
    Description=SHADOW CHEATS MUSIC Bot
    After=network.target

    [Service]
    Type=simple
    User=ubuntu
    WorkingDirectory=/home/ubuntu/shadow-cheats-music
    ExecStart=/home/ubuntu/shadow-cheats-music/venv/bin/python bot.py
    Restart=always
    RestartSec=10
    StandardOutput=journal
    StandardError=journal

    [Install]
    WantedBy=multi-user.target
    ```

4.  **Start and Enable the Service**:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable shadowcheats.service
    sudo systemctl start shadowcheats.service
    ```

5.  **Monitor Logs**:
    To see live prints and debug logs:
    ```bash
    sudo journalctl -u shadowcheats.service -f
    ```

---

## 🟢 Option B: Deploying with PM2 (Process Manager)
Recommended if you host multiple bots/applications and want quick clustering and metrics.

1.  **Install PM2 globally**:
    Ensure Node.js is installed, then run:
    ```bash
    npm install pm2 -g
    ```

2.  **Start the Bot**:
    Navigate to the bot directory and launch:
    ```bash
    pm2 start bot.py --name "shadow-cheats" --interpreter python3
    ```

3.  **Manage Process**:
    *   Check status: `pm2 status`
    *   Monitor logs: `pm2 logs shadow-cheats`
    *   Restart bot: `pm2 restart shadow-cheats`
    *   Set auto-startup on boot: `pm2 startup` (and run the command printed).

---

## 🐳 Option C: Deploying with Docker
Recommended for containerized isolated environments.

1.  **Create a Dockerfile**:
    Save the following content as `Dockerfile` in the root bot directory:
    ```dockerfile
    FROM python:3.10-slim

    # Install system utilities, ffmpeg and nodejs
    RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
        && apt-get install -y nodejs \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

    WORKDIR /app
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    COPY . .
    CMD ["python", "bot.py"]
    ```

2.  **Build and Run**:
    ```bash
    docker build -t shadow-cheats-music .
    docker run -d --name cheats-bot --restart unless-stopped -v $(pwd)/bot_database.db:/app/bot_database.db shadow-cheats-music
    ```

---

## 💿 Option D: Local Windows Server
If you are hosting locally or on a Windows Server VM:

1.  **Use Task Scheduler**:
    *   Open **Task Scheduler** (`taskschd.msc`).
    *   Create a Basic Task -> trigger "At startup".
    *   Action: "Start a program".
    *   Program/script: Path to `python.exe` (or `venv\Scripts\python.exe`).
    *   Add arguments: `bot.py`
    *   Start in: `C:\Users\Arun Yadav\Downloads\Shadow lofi`
    *   Under settings, toggle: "If the task fails, restart every: 1 minute".

---

## 💾 Database Backups
All server states are saved in `bot_database.db`.
*   **Linux backup cron**: Add a daily backup cron script to copy the database file:
    ```bash
    crontab -e
    # Backup database daily at midnight
    0 0 * * * cp /home/ubuntu/shadow-cheats-music/bot_database.db /home/ubuntu/backups/bot_database_$(date +\%F).db
    ```
