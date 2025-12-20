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
STREAK_FILE = 'streak_data.json'

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

def load_streak_data():
    if os.path.exists(STREAK_FILE):
        try:
            with open(STREAK_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"current_streak": 0, "last_commit_date": None}
    return {"current_streak": 0, "last_commit_date": None}

def save_streak_data(data):
    with open(STREAK_FILE, 'w') as f:
        json.dump(data, f, indent=4)

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
        
        streak_data = load_streak_data()
        current_streak = streak_data.get('current_streak', 0)
        last_commit_date = streak_data.get('last_commit_date')
        
        today_str = now_ist.strftime('%Y-%m-%d')
        
        # Update streak logic
        if total_commits > 0:
            if last_commit_date:
                last_date = datetime.strptime(last_commit_date, '%Y-%m-%d').date()
                current_date = now_ist.date()
                
                if (current_date - last_date).days == 1:
                    current_streak += 1
                elif (current_date - last_date).days > 1:
                    current_streak = 1
                # If same day, don't increment
                elif (current_date - last_date).days == 0:
                    pass # Already counted for today? Or maybe re-running script.
            else:
                current_streak = 1
                
            streak_data['current_streak'] = current_streak
            streak_data['last_commit_date'] = today_str
            save_streak_data(streak_data)
            
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
            # Reset streak if missed yesterday (and it's not the first run ever)
            if last_commit_date:
                last_date = datetime.strptime(last_commit_date, '%Y-%m-%d').date()
                current_date = now_ist.date()
                if (current_date - last_date).days > 1:
                    current_streak = 0
                    streak_data['current_streak'] = 0
                    save_streak_data(streak_data)

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
