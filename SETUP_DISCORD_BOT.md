# How to Run and Configure the SENTRIX Discord Bot

The SENTRIX Discord Bot is powered by Python and links directly with the SQLite database that synchronizes settings from the web dashboard.

---

## 🔑 1. Where to Add Your Credentials (Token & Client ID)

Your credentials are set inside the **`.env`** configuration file located at the root of the project directory:

👉 **[Edit Environment Config File (.env)](file:///C:/Users/yadav/.gemini/antigravity/scratch/sentrix-ultimate/.env)**

Open the file and fill in your values:

```env
PORT=3000

# 1. Enter your Discord Application Client ID here (Used for Web OAuth login)
DISCORD_CLIENT_ID=your_client_id_here

# 2. Enter your Discord Application Secret here (Used for Web OAuth authentication handshake)
DISCORD_CLIENT_SECRET=your_client_secret_here

DISCORD_REDIRECT_URI=https://veyra.vercel.app/api/auth/callback

# 3. Enter your Discord Bot Gateway Token here (Used by the python bot to connect to Discord)
DISCORD_BOT_TOKEN=your_bot_token_here
```

---

## ⚙️ 2. How to Retrieve Your Token and Client ID

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Select your application (or click **New Application** to create one).
3. **Client ID:** Copy it from the **General Information** page and paste it into `DISCORD_CLIENT_ID` in `.env`.
4. **Client Secret:** On the same page, click **Reset Secret** and copy it into `DISCORD_CLIENT_SECRET` in `.env`.
5. **Bot Token:**
   * Go to the **Bot** tab on the left menu.
   * If you haven't created a bot user, click **Add Bot**.
   * Click **Reset Token**, copy the generated token string, and paste it into `DISCORD_BOT_TOKEN` in `.env`.
   * **Crucial:** Enable all **Privileged Gateway Intents** (Presence Intent, Server Members Intent, Message Content Intent) at the bottom of the Bot page so the anti-nuke scanner can receive event logs.

---

## 🚀 3. How to Run the Bot

### Prerequisites
Make sure you have Python installed and the Discord dependency loaded:
```bash
pip install discord.py
```

### Start the Bot
Execute the script from your terminal:
```bash
python bot/bot.py
```

Sentrix will automatically load the `.env` file, report the loaded configuration status, and initialize connection gateways.
