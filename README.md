# GitHub Daily Commit Reminder 🤖

An automated system that checks your GitHub commits daily at 9 PM IST and sends you an email notification. It motivates you to keep your coding streak alive!

## Features 🌟

- **Daily Checks**: Runs automatically at 9 PM IST via GitHub Actions.
- **Smart Notifications**:
  - ✅ **Success**: Sends a congratulatory email with commit stats and streak count if you've committed today.
  - ⚠️ **Reminder**: Sends a motivational reminder if you haven't committed yet.
- **Streak Tracking**: Persistently tracks your commit streak in `streak_data.json`.
- **Fancy Emails**: Uses a responsive HTML template with GitHub-like styling.
- **Motivational Quotes**: Includes random coding quotes to keep you inspired.

## Setup Instructions 🛠️

### 1. Fork or Clone this Repository
Use this template or clone the repository to your own GitHub account.

### 2. Get GitHub Personal Access Token (PAT)
1. Go to [GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)](https://github.com/settings/tokens).
2. Generate a new token.
3. Select the `repo` and `user` scopes (to read contribution data).
4. Copy the token.

### 3. Get Gmail App Password
1. Go to your Google Account settings.
2. Navigate to **Security** > **2-Step Verification**.
3. Scroll to the bottom and select **App passwords**.
4. Create a new app password for "Mail" and "Mac" (or custom name).
5. Copy the 16-character password.

### 4. Configure GitHub Secrets
Go to your repository's **Settings** > **Secrets and variables** > **Actions** and add the following repository secrets:

| Secret Name | Description |
|-------------|-------------|
| `GH_TOKEN` | Your GitHub Personal Access Token (from Step 2). |
| `GH_USERNAME` | Your GitHub username (e.g., `arvindkumar1422`). |
| `EMAIL_SENDER` | Your Gmail address (e.g., `you@gmail.com`). |
| `EMAIL_PASSWORD` | Your Gmail App Password (from Step 3). |
| `EMAIL_RECIPIENT` | The email address to receive notifications. |

### 5. Enable GitHub Actions
1. Go to the **Actions** tab in your repository.
2. Ensure workflows are enabled.
3. You can manually trigger the workflow to test it by selecting "Daily GitHub Reminder" and clicking "Run workflow".

## Local Development 💻

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create a `.env` file with the variables listed in Step 4.
3. Run the script:
   ```bash
   python main.py
   ```

## How it Works ⚙️

- **`main.py`**: The brain of the operation. It fetches data from GitHub's GraphQL API, calculates streaks, and sends emails via SMTP.
- **`.github/workflows/daily-reminder.yml`**: The scheduler. It runs the Python script every day at 15:30 UTC (9:00 PM IST).
- **`streak_data.json`**: The memory. It stores your current streak and the last date you committed.
- **`email_template.html`**: The face. A beautiful HTML template for the emails.

## License 📄
MIT
