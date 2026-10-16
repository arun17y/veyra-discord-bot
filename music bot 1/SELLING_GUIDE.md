# 📚 SHADOW CHEATS MUSIC — Buyer Setup & Installation Manual (A-to-Z Guide)

Welcome to **SHADOW CHEATS MUSIC**! This document provides step-by-step instructions to configure, run, and self-host your premium Discord music bot package.

---

## 📂 1. What's Inside the Folder
Your package contains the following files:
*   `bot.py`: The main Python source code of the bot.
*   `config.json`: The configuration file containing your bot token and owner settings.
*   `requirements.txt`: The list of Python modules required for running the bot.
*   `install.bat` / `run.bat`: Double-click scripts to automatically install dependencies and run the bot on **Windows**.
*   `install.sh` / `run.sh`: Command scripts to install dependencies and run the bot on **Linux (VPS)**.
*   `ffmpeg/bin/`: Includes built-in FFmpeg audio engine binaries so you don't have to install them manually.
*   `README.md`: General user manual detailing all bot commands.
*   `deployment.md`: High-scale dedicated production setup configurations (such as systemd services, PM2, or Docker).
*   `LICENSE`: Standard MIT license for code distribution.

---

## 🔑 2. Get Your Discord Bot Token
Before running the bot, you need to register it on Discord's developer platform:

1.  Open the **[Discord Developer Portal](https://discord.com/developers/applications)**.
2.  Click the **New Application** button in the top-right corner, name it (e.g. *SHADOW CHEATS MUSIC*), and click **Create**.
3.  Go to the **Bot** tab on the left sidebar:
    *   Click **Reset Token** and copy the long token code. **Save this token; you will need it in the next step!**
4.  Scroll down to the **Privileged Gateway Intents** section and toggle **ON** the following options:
    *   `Presence Intent`
    *   `Server Members Intent`
    *   `Message Content Intent` (important for text commands!)
5.  Click **Save Changes**.

---

## ⚙️ 3. Configure the Bot Settings
Open the [config.json](file:///C:/Users/Arun%20Yadav/Downloads/Shadow%20lofi/config.json) file inside your folder with any text editor (like Notepad) and set your tokens:

```json
{
  "token": "YOUR_DISCORD_BOT_TOKEN_HERE",
  "prefix": ".",
  "owner_ids": [
    YOUR_DISCORD_USER_ID
  ]
}
```
*Replace `YOUR_DISCORD_BOT_TOKEN_HERE` with the token you copied from the Developer Portal, and put your personal Discord User ID inside `owner_ids` to grant yourself developer administrative access.*

---

## 🚀 4. How to Start the Bot

### 💻 Option A: On Windows (Local Hosting)
1.  Make sure you have **[Python 3.10 or 3.11](https://www.python.org/downloads/)** installed on your computer. During installation, make sure to check the box that says **"Add Python to PATH"**.
2.  Double-click **`install.bat`**. This will open a command line window and automatically download all necessary Python packages.
3.  Once completed, double-click **`run.bat`** to start the bot. Keep this window open; closing it will turn the bot offline.

### 🐧 Option B: On Linux (VPS Server)
1.  Install Python and standard tools:
    ```bash
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv ffmpeg nodejs
    ```
2.  Run the installer script:
    ```bash
    bash install.sh
    ```
3.  Run the launcher script:
    ```bash
    bash run.sh
    ```
    *(To run it 24/7 on a VPS, refer to the [deployment.md](file:///C:/Users/Arun%20Yadav/Downloads/Shadow%20lofi/deployment.md) guide for PM2 or systemd setup.)*

---

## 🔗 5. How to Invite the Bot to Your Server
Once the bot window prints `🎵 SHADOW CHEATS MUSIC Online`, it is successfully running!

1.  In any server channel, type `/invite` or `.invite`.
2.  The bot will respond with a custom invite link.
3.  Click the link, select the server you want to add the bot to, and click **Authorize**.
4.  Join a Voice Channel and type `.play <song name>` or use slash commands (`/play`) to start listening!
