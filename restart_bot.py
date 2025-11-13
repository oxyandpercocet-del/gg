# restart_bot.py — AUTO-RESTART
import subprocess, time, os, sys
from datetime import datetime

BOT_SCRIPT = "fortnite_checker.py"
LOG_FILE = "crash_log.txt"

def log(msg):
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{t}] {msg}")
    with open(LOG_FILE, "a", encoding="utf-8") as f: f.write(f"[{t}] {msg}\n")

def run_bot():
    while True:
        log("Starting bot...")
        p = subprocess.Popen([sys.executable, BOT_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in p.stdout:
            print(line, end="")
            with open(LOG_FILE, "a", encoding="utf-8") as f: f.write(line)
        p.wait()
        log(f"Bot crashed! Restarting in 5s...")
        time.sleep(5)

if __name__ == "__main__":
    if not os.path.exists(BOT_SCRIPT):
        print("bot.py not found!")
        sys.exit(1)
    run_bot()