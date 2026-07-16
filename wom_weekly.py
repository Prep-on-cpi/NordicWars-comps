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
API_KEY = "ml5jtxgo6m5mzbu0bwvhserf"  # Fixed API key for NordicWars comps
GROUP_ID = 7753  
VERIFICATION_CODE = "996-370-037"  
HISTORY_FILE = "wom_history.txt"

# --- POOL OF SKILLS TO RANDOMIZE ---
SKILL_POOL = [
    "attack", "strength", "defence", "ranged", "prayer", 
    "magic", "runecraft", "hitpoints", "crafting", "mining", 
    "smithing", "fishing", "cooking", "firemaking", "woodcutting"
]


def calculate_competition_dates():
    """Calculates the upcoming Saturday 10 PM to next Saturday 9:59 PM UTC."""
    now = datetime.datetime.now(datetime.timezone.utc)

    # Saturday is weekday 5
    days_until_saturday = (5 - now.weekday()) % 7

    # If today is Saturday and it's already past 10 PM UTC, schedule for next week
    if days_until_saturday == 0 and now.hour >= 22:
        days_until_saturday = 7

    start_date = (now + datetime.timedelta(days=days_until_saturday)).replace(
        hour=22, minute=0, second=0, microsecond=0
    )
    end_date = start_date + datetime.timedelta(days=6, hours=23, minutes=59)

    return start_date, end_date


def get_last_week_skills():
    """Reads the previously tracked skills from a text file."""
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]


def save_current_skills(skill_a, skill_b):
    """Saves the chosen skills to a text file for next week's check."""
    with open(HISTORY_FILE, "w") as f:
        f.write(f"{skill_a}\n{skill_b}\n")


def generate_unique_single_skills():
    """Selects two single metrics that don't match each other or last week."""
    last_week = get_last_week_skills()
    logging.info(f"Skipping previous week's metrics: {last_week}")

    # Remove last week's skills from the available pool
    available_pool = [skill for skill in SKILL_POOL if skill not in last_week]

    # In case history file corruption leaves us with too few items, fall back to pool
    if len(available_pool) < 2:
        available_pool = SKILL_POOL

    # Draw two completely unique metrics from the filtered pool
    selected_skills = random.sample(available_pool, 2)
    
    # Save selections to history file before returning
    save_current_skills(selected_skills[0], selected_skills[1])

    # Return them packaged as separate single-item lists required by WOM
    return [selected_skills[0]], [selected_skills[1]]


def send_creation_request(title, metrics_list):
    """Handles the API POST request for a single competition."""
    start_date, end_date = calculate_competition_dates()
    
    payload = {
        "title": f"{title} ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')})",
        "metric": "multi_metric",  
        "metrics": metrics_list, 
        "startsAt": start_date.isoformat(),
        "endsAt": end_date.isoformat(),
        "groupId": GROUP_ID,
        "groupVerificationCode": VERIFICATION_CODE,
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    logging.info(f"Attempting to create competition: '{payload['title']}' tracking: {metrics_list}")

    try:
        url = f"{BASE_URL}/competitions"
        response = requests.post(url, json=payload, headers=headers, timeout=15)

        if response.status_code == 201:
            data = response.json()
            logging.info(f"✅ Created successfully: {data['title']}")
            logging.info(f"🔗 Link: https://wiseoldman.net{data['id']}")
        else:
            logging.error(f"❌ API Rejected '{title}'. Status: {response.status_code}")
            logging.error(f"Response: {response.text}")

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Network error occurred for '{title}': {e}")


def main():
    # 1. Generate two unique individual skills distinct from last week
    comp_a_skill, comp_b_skill = generate_unique_single_skills()
    
    # 2. Run Competition A with its single random skill
    send_creation_request("SOTW payout 1m A", comp_a_skill)
    
    # 3. Run Competition B with a different single random skill
    send_creation_request("SOTW payout 1m B", comp_b_skill)


if __name__ == "__main__":
    main()
