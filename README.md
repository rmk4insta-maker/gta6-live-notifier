# GTA 6 Live Stream GitHub Notifier

Zero-cost, 24/7 cloud streamer monitor powered by GitHub Actions. Every 5 minutes, it checks whether **IShowSpeed** or **Kai Cenat** are live and notifies your Telegram immediately.

---

## Files in this repository

- `watcher.py`: Fast Python script querying YouTube & Twitch public endpoints for live status.
- `state.json`: State file tracking live transitions (`False` ↔ `True`).
- `.github/workflows/live_alert.yml`: GitHub Actions cron workflow running every 5 minutes.

---

## 3-Minute Setup on GitHub

1. **Create a new GitHub Repository** (e.g. `gta6-stream-notifier`).
2. **Push the contents of this folder** to your new repo:
   ```bash
   cd github_notifier
   git init
   git add .
   git commit -m "Initial commit: 24/7 stream watcher"
   git branch -M main
   git remote add origin https://github.com/<YOUR_USERNAME>/gta6-stream-notifier.git
   git push -u origin main
   ```
3. **Add Telegram Secrets**:
   - Go to **Settings > Secrets and variables > Actions > New repository secret**.
   - Add:
     - `TELEGRAM_BOT_TOKEN`: Your Telegram Bot token from @BotFather.
     - `TELEGRAM_CHAT_ID`: Your numerical Telegram user/group ID or channel username (e.g. `123456789` or `@mychannel`).
4. **Enable Workflow Permissions**:
   - Go to **Settings > Actions > General > Workflow permissions**.
   - Select **Read and write permissions** (allows the workflow to commit `state.json`).
5. **Test**:
   - Go to the **Actions** tab on GitHub, click **Live Stream Watcher & Telegram Alert**, and click **Run workflow**.
