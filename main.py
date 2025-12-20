import os
import json
import smtplib
import requests
import random
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pytz
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GITHUB_TOKEN = os.getenv('GH_TOKEN')
GITHUB_USERNAME = os.getenv('GH_USERNAME')
EMAIL_SENDER = os.getenv('EMAIL_SENDER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_RECIPIENT = os.getenv('EMAIL_RECIPIENT')

# Constants
IST = pytz.timezone('Asia/Kolkata')

MOTIVATIONAL_QUOTES = [
    "Code is like humor. When you have to explain it, it’s bad. – Cory House",
    "First, solve the problem. Then, write the code. – John Johnson",
    "Experience is the name everyone gives to their mistakes. – Oscar Wilde",
    "In order to be irreplaceable, one must always be different. – Coco Chanel",
    "Java is to JavaScript what car is to Carpet. – Chris Heilmann",
    "Knowledge is power. – Francis Bacon",
    "Sometimes it pays to stay in bed on Monday, rather than spending the rest of the week debugging Monday’s code. – Dan Salomon",
    "Perfection is achieved not when there is nothing more to add, but rather when there is nothing more to take away. – Antoine de Saint-Exupery",
    "Ruby is rubbish! PHP is phpantastic! – Nikita Popov",
    "Code never lies, comments sometimes do. – Ron Jeffries"
]

def get_current_time_ist():
    return datetime.now(IST)

def fetch_streak_from_github():
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    
    # Fetch contribution calendar (defaults to last year)
    query = """
    query($userName:String!) {
      user(login: $userName) {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """
    
    variables = {"userName": GITHUB_USERNAME}
    
    response = requests.post('https://api.github.com/graphql', json={'query': query, 'variables': variables}, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"GitHub API failed: {response.text}")
        
    data = response.json()
    calendar = data['data']['user']['contributionsCollection']['contributionCalendar']
    
    # Flatten the weeks into a single list of days
    all_days = []
    for week in calendar['weeks']:
        for day in week['contributionDays']:
            all_days.append(day)
            
    # Sort by date just in case
    all_days.sort(key=lambda x: x['date'])
    
    # Calculate streak ending yesterday (or today)
    # We iterate backwards from the last day in the calendar
    current_streak = 0
    
    # The calendar goes up to "today" (UTC usually).
    # We want to find the consecutive run of days with contributions > 0
    # starting from the most recent day with contributions.
    
    # However, if today has 0 commits so far, we shouldn't break the streak yet if yesterday had commits.
    # So we find the last day with contributions.
    
    # Let's iterate backwards
    streak_days = 0
    gap_found = False
    
    # We need to handle "today" carefully.
    # If today has commits, streak includes today.
    # If today has 0 commits, streak is whatever it was up to yesterday.
    # But if yesterday also had 0, streak is 0.
    
    # Let's look at the last few days
    today_str = datetime.now(pytz.UTC).strftime('%Y-%m-%d')
    
    # Reverse iteration
    for i in range(len(all_days) - 1, -1, -1):
        day = all_days[i]
        count = day['contributionCount']
        date = day['date']
        
        if count > 0:
            streak_days += 1
        else:
            # If we hit a zero
            # If this zero is "today" (and we haven't committed yet), we ignore it and continue checking yesterday.
            # If this zero is "yesterday" or before, the streak is broken.
            
            if date == today_str:
                continue # Skip today if it's 0, don't break streak yet
            else:
                # Break the streak
                if streak_days > 0:
                    break
                # If we haven't started a streak yet (e.g. today 0, yesterday 0), keep going? No, streak is 0.
                # Actually, if we haven't found any commits yet, and we hit a 0 for yesterday, streak is definitely 0.
                break
                
    return streak_days

def fetch_github_contributions(date_ist):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    
    # Calculate start and end of the day in UTC for the query
    # We want to check commits made on "today" IST.
    # So from 00:00:00 IST to 23:59:59 IST converted to UTC.
    
    start_of_day_ist = date_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day_ist = date_ist.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    start_utc = start_of_day_ist.astimezone(pytz.UTC).isoformat()
    end_utc = end_of_day_ist.astimezone(pytz.UTC).isoformat()

    query = """
    query($userName:String!, $from:DateTime!, $to:DateTime!) {
      user(login: $userName) {
        contributionsCollection(from: $from, to: $to) {
          commitContributionsByRepository {
            repository {
              name
            }
            contributions(first: 100) {
              nodes {
                occurredAt
              }
            }
          }
        }
      }
    }
    """
    
    variables = {
        "userName": GITHUB_USERNAME,
        "from": start_utc,
        "to": end_utc
    }
    
    response = requests.post('https://api.github.com/graphql', json={'query': query, 'variables': variables}, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"GitHub API failed: {response.text}")
        
    return response.json()

def send_email(subject, html_content):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECIPIENT
    msg['Subject'] = subject

    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

def generate_email_content(template_path, context):
    with open(template_path, 'r') as f:
        template = f.read()
    
    for key, value in context.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    
    return template

def main():
    print("Starting GitHub Daily Reminder...")
    
    try:
        now_ist = get_current_time_ist()
        print(f"Current time (IST): {now_ist}")
        
        # Fetch data (using the same range as before, but we will filter strictly in Python)
        data = fetch_github_contributions(now_ist)
        
        # Process contributions to filter strictly for TODAY in IST
        total_commits = 0
        repo_stats = []
        today_date = now_ist.date()
        
        if 'data' in data and 'user' in data['data'] and data['data']['user']['contributionsCollection']:
            collection = data['data']['user']['contributionsCollection']
            
            for repo_data in collection['commitContributionsByRepository']:
                repo_name = repo_data['repository']['name']
                repo_commits_today = 0
                
                # Iterate through individual commits
                if 'contributions' in repo_data and 'nodes' in repo_data['contributions']:
                    for contribution in repo_data['contributions']['nodes']:
                        # Parse ISO format (e.g., 2023-12-19T14:30:00Z)
                        occurred_at_str = contribution['occurredAt'].replace('Z', '+00:00')
                        occurred_at_utc = datetime.fromisoformat(occurred_at_str)
                        occurred_at_ist = occurred_at_utc.astimezone(IST)
                        
                        if occurred_at_ist.date() == today_date:
                            repo_commits_today += 1
                
                if repo_commits_today > 0:
                    total_commits += repo_commits_today
                    repo_stats.append((repo_name, repo_commits_today))
        
        # Calculate streak dynamically from GitHub API
        current_streak = fetch_streak_from_github()
        
        today_str = now_ist.strftime('%Y-%m-%d')
        
        # Update streak logic
        if total_commits > 0:
            # Prepare success email
            repos_html = []
            for name, count in repo_stats:
                repos_html.append(f'<div class="repo-item"><span class="repo-icon">📂</span> {name} <span style="margin-left:auto; font-weight:bold;">{count}</span></div>')
            
            stats_html = f"""
            <div class="streak-hero">
                <div class="streak-count-big">{current_streak}</div>
                <div class="streak-subtext">🔥 On Fire!</div>
            </div>
            
            <div class="repo-section-title">Repositories Committed To</div>
            <div class="repo-list">
                {''.join(repos_html)}
            </div>
            """
            
            context = {
                "title": "🎉 Great Job! Commits Detected",
                "message": f"You've made <strong>{total_commits}</strong> commits today. Keep up the momentum!",
                "stats_section": stats_html,
                "quote": random.choice(MOTIVATIONAL_QUOTES),
                "timestamp": now_ist.strftime('%Y-%m-%d %H:%M:%S IST')
            }
            
            email_html = generate_email_content('email_template.html', context)
            send_email(f"✅ GitHub Daily Update: {total_commits} Commits!", email_html)
            
        else:
            # Prepare reminder email
            stats_html = f"""
            <div class="streak-hero">
                <div class="streak-count-big">{current_streak}</div>
                <div class="streak-subtext warning">⚠️ Don't let it break!</div>
            </div>
            
            <div class="stat-row">
                <span class="stat-label">Commits Today</span>
                <span class="stat-value" style="color: #d73a49;">0</span>
            </div>
            """
            
            context = {
                "title": "⚠️ Reminder: Keep the Streak Alive!",
                "message": "Warning: You haven't committed yet today! Push some code to maintain your streak.",
                "stats_section": stats_html,
                "quote": random.choice(MOTIVATIONAL_QUOTES),
                "timestamp": now_ist.strftime('%Y-%m-%d %H:%M:%S IST')
            }
            
            email_html = generate_email_content('email_template.html', context)
            send_email("⚠️ GitHub Daily Reminder: No Commits Yet!", email_html)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        # Optionally send an error email to yourself
        
if __name__ == "__main__":
    main()
