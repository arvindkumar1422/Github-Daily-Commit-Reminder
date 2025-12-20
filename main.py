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

def fetch_streak_from_github(today_ist_str):
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
    
    # Find today's count (IST)
    today_count = 0
    for day in all_days:
        if day['date'] == today_ist_str:
            today_count = day['contributionCount']
            break
            
    # Calculate streak
    streak_days = 0
    
    # Reverse iteration
    for i in range(len(all_days) - 1, -1, -1):
        day = all_days[i]
        count = day['contributionCount']
        date = day['date']
        
        # We only care about days up to today (IST)
        if date > today_ist_str:
            continue
            
        if count > 0:
            streak_days += 1
        else:
            # If we hit a zero
            if date == today_ist_str:
                continue # Skip today if it's 0, don't break streak yet
            else:
                break
                
    return streak_days, today_count

def fetch_github_contributions(date_ist):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    
    # Calculate start and end of the day in UTC for the query
    # We want to check commits made on "today" IST.
    # So from 00:00:00 IST to 23:59:59 IST converted to UTC.
    
    start_of_day_ist = date_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day_ist = date_ist.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Convert to UTC
    start_utc = start_of_day_ist.astimezone(pytz.UTC).isoformat()
    end_utc = end_of_day_ist.astimezone(pytz.UTC).isoformat()

    query = """
    query($from:DateTime!, $to:DateTime!) {
      viewer {
        contributionsCollection(from: $from, to: $to) {
          restrictedContributionsCount
          totalCommitContributions
          totalIssueContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
          totalRepositoryContributions
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
          issueContributionsByRepository {
            repository {
              name
            }
            contributions(first: 100) {
              nodes {
                occurredAt
              }
            }
          }
          pullRequestContributionsByRepository {
            repository {
              name
            }
            contributions(first: 100) {
              nodes {
                occurredAt
              }
            }
          }
          pullRequestReviewContributionsByRepository {
            repository {
              name
            }
            contributions(first: 100) {
              nodes {
                occurredAt
              }
            }
          }
          repositoryContributions(first: 100) {
            nodes {
              occurredAt
              repository {
                name
              }
            }
          }
        }
      }
    }
    """
    
    variables = {
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
        template = template.replace("{{" + key + "}}", str(value))
    
    return template

def main():
    print("Starting GitHub Daily Reminder...")
    
    try:
        now_ist = get_current_time_ist()
        print(f"Current time (IST): {now_ist}")
        
        # Fetch data (using the same range as before, but we will filter strictly in Python)
        data = fetch_github_contributions(now_ist)
        
        # Process contributions to filter strictly for TODAY in IST
        repo_stats = {}
        today_date = now_ist.date()
        
        if 'data' in data and 'viewer' in data['data'] and data['data']['viewer']['contributionsCollection']:
            collection = data['data']['viewer']['contributionsCollection']
            
            # Helper to process a list of contribution collections
            def process_contributions(contribution_list):
                if not contribution_list:
                    return
                for repo_data in contribution_list:
                    repo_name = repo_data['repository']['name']
                    
                    if 'contributions' in repo_data and 'nodes' in repo_data['contributions']:
                        for contribution in repo_data['contributions']['nodes']:
                            # We trust the API date range now, but double check just in case
                            repo_stats[repo_name] = repo_stats.get(repo_name, 0) + 1

            process_contributions(collection.get('commitContributionsByRepository', []))
            process_contributions(collection.get('issueContributionsByRepository', []))
            process_contributions(collection.get('pullRequestContributionsByRepository', []))
            process_contributions(collection.get('pullRequestReviewContributionsByRepository', []))
            
            # Process repository creations
            if 'repositoryContributions' in collection and 'nodes' in collection['repositoryContributions']:
                for repo_creation in collection['repositoryContributions']['nodes']:
                    repo_name = repo_creation['repository']['name']
                    repo_stats[repo_name] = repo_stats.get(repo_name, 0) + 1

            # Get restricted count
            restricted_count = collection.get('restrictedContributionsCount', 0)
            
            # Get API totals
            total_commits = collection.get('totalCommitContributions', 0)
            total_issues = collection.get('totalIssueContributions', 0)
            total_prs = collection.get('totalPullRequestContributions', 0)
            total_reviews = collection.get('totalPullRequestReviewContributions', 0)
            total_repos_created = collection.get('totalRepositoryContributions', 0)
            
            api_total_count = total_commits + total_issues + total_prs + total_reviews + total_repos_created
        
        today_str = now_ist.strftime('%Y-%m-%d')
        
        # Calculate streak and today's total contributions dynamically from GitHub API
        current_streak, calendar_count = fetch_streak_from_github(today_str)
        
        # Use the calendar count as the source of truth for "Total Contributions"
        display_count = calendar_count
        
        # Update streak logic
        if display_count > 0:
            # Prepare success email
            repos_html = []
            # Sort repos by count descending (so most active are at top)
            sorted_repos = sorted(repo_stats.items(), key=lambda item: item[1], reverse=True)
            
            for name, count in sorted_repos:
                # Display only the repository name, not the count
                repos_html.append(f'<div class="repo-item"><span class="repo-icon">📂</span> {name}</div>')
            
            if not repos_html and display_count > 0:
                repos_html.append('<div class="repo-item" style="font-style:italic; color:#666;">Contributions in other areas (Issues, PRs, or Private Repos)</div>')

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
                "title": "🎉 Great Job! Contributions Detected",
                "message": f"You've made <strong>{display_count}</strong> contributions today. Keep up the momentum!",
                "stats_section": stats_html,
                "quote": random.choice(MOTIVATIONAL_QUOTES),
                "timestamp": now_ist.strftime('%Y-%m-%d %H:%M:%S IST')
            }
            
            email_html = generate_email_content('email_template.html', context)
            send_email(f"✅ GitHub Daily Update: {display_count} Contributions!", email_html)
            
        else:
            # Prepare reminder email
            stats_html = f"""
            <div class="streak-hero">
                <div class="streak-count-big">{current_streak}</div>
                <div class="streak-subtext warning">⚠️ Don't let it break!</div>
            </div>
            
            <div class="stat-row">
                <span class="stat-label">Contributions Today</span>
                <span class="stat-value" style="color: #d73a49;">0</span>
            </div>
            """
            
            context = {
                "title": "⚠️ Reminder: Keep the Streak Alive!",
                "message": "Warning: You haven't contributed yet today! Push some code to maintain your streak.",
                "stats_section": stats_html,
                "quote": random.choice(MOTIVATIONAL_QUOTES),
                "timestamp": now_ist.strftime('%Y-%m-%d %H:%M:%S IST')
            }
            
            email_html = generate_email_content('email_template.html', context)
            send_email("⚠️ GitHub Daily Reminder: No Contributions Yet!", email_html)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        # Optionally send an error email to yourself
        
if __name__ == "__main__":
    main()
