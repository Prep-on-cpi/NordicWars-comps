import datetime
import logging
import os
import random
import sys
import requests

# --- LOGGING CONFIGURATION ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("wom_automation.log"), logging.StreamHandler(sys.stdout)],
)

# --- LIVE CONFIGURATION VARIABLES ---
BASE_URL = "https://wiseoldman.net"
API_KEY = "ml5jtxgo6m5mzbu0bwvhserf"
GROUP_ID = 7753  
VERIFICATION_CODE = "996-370-037"  
HISTORY_FILE = "wom_history.txt"
DISCORD_WEBHOOK_URL = "https://discord.com"

# --- POOL OF SKILLS TO RANDOMIZE ---
SKILL_POOL = [
    "attack", "strength", "defence", "ranged", "prayer", 
    "magic", "runecraft", "hitpoints", "crafting", "mining", 
    "smithing", "fishing", "cooking", "firemaking", "woodcutting"
]


def calculate_competition_dates():
    now = datetime.datetime.now(datetime.timezone.utc)
    days_until_saturday = (5 - now.weekday()) % 7
    if days_until_saturday == 0 and now.hour >= 22:
        days_until_saturday = 7
    start_date = (now + datetime.timedelta(days=days_until_saturday)).replace(
        hour=22, minute=0, second=0, microsecond=0
    )
    end_date = start_date + datetime.timedelta(days=6, hours=23, minutes=59)
    return start_date, end_date


def get_last_week_skills():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]


def save_current_skills(skill_a, skill_b):
    with open(HISTORY_FILE, "w") as f:
        f.write(f"{skill_a}\n{skill_b}\n")


def generate_unique_single_skills():
    last_week = get_last_week_skills()
    available_pool = [skill for skill in SKILL_POOL if skill not in last_week]
    if len(available_pool) < 2:
        available_pool = SKILL_POOL
    selected_skills = random.sample(available_pool, 2)
    skill_a = str(selected_skills[0])
    skill_b = str(selected_skills[1])
    save_current_skills(skill_a, skill_b)
    return skill_a, skill_b


def send_discord_notification(payload):
    """Fires raw payload straight to Discord."""
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if 200 <= response.status_code < 300:
            logging.info("✅ Discord notification sent successfully!")
        else:
            logging.error(f"❌ Discord Webhook failed with status: {response.status_code}")
    except Exception as e:
        logging.error(f"❌ Failed to dispatch Discord Webhook: {e}")


def send_creation_request(title, metric_name):
    start_date, end_date = calculate_competition_dates()
    full_title = f"{title} ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')})"
    
    payload = {
        "title": full_title,
        "metric": metric_name,  
        "startsAt": start_date.isoformat(),
        "endsAt": end_date.isoformat(),
        "groupId": GROUP_ID,
        "groupVerificationCode": VERIFICATION_CODE
    }

    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
    logging.info(f"Attempting to create competition: '{full_title}' tracking: {metric_name}")

    try:
        url = f"{BASE_URL}/competitions"
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 201:
            data = response.json()
            return {"success": True, "title": data['title'], "id": data['id']}
        else:
            return {"success": False, "error": response.text}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def main():
    metric_a, metric_b = generate_unique_single_skills()
    
    # Run API Calls
    res_a = send_creation_request("SOTW payout 1m A", metric_a)
    res_b = send_creation_request("SOTW payout 1m B", metric_b)

    # BUILD DISCORD EMBED REGARDLESS OF SUCCESS/FAILURE
    embed = {
        "username": "NordicWars Automation",
        "avatar_url": "https://wiseoldman.net",
        "embeds": [{
            "title": "⚙️ Automation Runner Diagnostic ⚙️",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "fields": []
        }]
    }

    # Format Comp A for Discord
    if res_a["success"]:
        embed["embeds"][0]["fields"].append({
            "name": f"🏆 {res_a['title']}",
            "value": f"**Tracked Skill:** {metric_a.title()}\n🔗 [View Leaderboard](https://wiseoldman.net{res_a['id']})",
            "inline": False
        })
    else:
        embed["embeds"][0]["fields"].append({
            "name": "❌ Competition A Generation Failed",
            "value": f"**Attempted Metric:** {metric_a}\n**Reason:** `{res_a['error']}`",
            "inline": False
        })

    # Format Comp B for Discord
    if res_b["success"]:
        embed["embeds"][0]["fields"].append({
            "name": f"🏆 {res_b['title']}",
            "value": f"**Tracked Skill:** {metric_b.title()}\n🔗 [View Leaderboard](https://wiseoldman.net{res_b['id']})",
            "inline": False
        })
    else:
        embed["embeds"][0]["fields"].append({
            "name": "❌ Competition B Generation Failed",
            "value": f"**Attempted Metric:** {metric_b}\n**Reason:** `{res_b['error']}`",
            "inline": False
        })

    send_discord_notification(embed)


if __name__ == "__main__":
    main()
