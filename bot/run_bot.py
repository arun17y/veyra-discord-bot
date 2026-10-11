import time
import subprocess
import os

print("Starting Veyra Bot auto-restarter...")
print("Sleeping for 90 seconds initially to let the cleanup script run first and allow rate limits to clear...")
time.sleep(90)

bot_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "bot.py"))

while True:
    print(f"Starting bot at {time.strftime('%X')}...")
    # Run bot unbuffered so log outputs are written immediately
    res = subprocess.run(["python", "-u", bot_path], capture_output=True, text=True)
    print("STDOUT:")
    print(res.stdout)
    print("STDERR:")
    print(res.stderr)
    
    if "Too Many Requests" in res.stderr or "429" in res.stderr:
        print("Bot login rate limited. Retrying in 90 seconds to allow the ban to clear completely...")
        time.sleep(90)
    else:
        print("Bot process stopped or crashed. Restarting in 15 seconds...")
        time.sleep(15)
