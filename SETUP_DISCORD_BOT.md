# How to Run and Configure the VEYRA Discord Bot

The VEYRA Discord Bot is powered completely by Python 3.11+, providing all server management, music, antinuke, ticketing, moderation, 24/7 voice, and security features.

---

## 🔑 1. Where to Add Your Credentials (Token & Client ID)

Your credentials are set inside the **`.env`** configuration file located at the root of the project directory:

```env
PORT=3000

# 1. Enter your Discord Application Client ID here
DISCORD_CLIENT_ID=your_client_id_here

# 2. Enter your Discord Bot Gateway Token here
DISCORD_BOT_TOKEN=your_bot_token_here
```

---

## ⚙️ 2. How to Retrieve Your Token and Client ID

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Select your application (or click **New Application** to create one).
3. **Client ID:** Copy it from the **General Information** page and paste it into `DISCORD_CLIENT_ID` in `.env`.
4. **Bot Token:**
   * Go to the **Bot** tab on the left menu.
   * If you haven't created a bot user, click **Add Bot**.
   * Click **Reset Token**, copy the generated token string, and paste it into `DISCORD_BOT_TOKEN` in `.env`.
   * **Crucial:** Enable all **Privileged Gateway Intents** (Presence Intent, Server Members Intent, Message Content Intent) at the bottom of the Bot page so the bot can receive event logs.

---

## 🚀 3. How to Run the Bot

### Prerequisites
Make sure you have Python installed and the dependencies loaded:
```bash
pip install -r requirements.txt
```

### Start the Bot
Execute the script from your terminal:
```bash
python bot/bot.py
```

VEYRA will automatically load the `.env` file, report the loaded configuration status, initialize the internal health check server, and connect to Discord.
