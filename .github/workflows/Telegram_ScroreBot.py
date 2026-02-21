name: Telegram Post-Match Scorecards

on:
  schedule:
    # Triggers exactly at 3:00 PM IST (09:30 UTC)
    - cron: '30 9 * * *'
    # Triggers every 30 minutes from 3:30 PM IST to 6:00 AM IST (10:00 to 00:30 UTC)
    - cron: '0,30 0,10-23 * * *'
  workflow_dispatch: 

jobs:
  post-scores:
    runs-on: ubuntu-latest
    permissions:
      contents: write 

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0 
          ref: main 

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install Pillow requests colorthief

      - name: Run Telegram Score Bot
        run: |
          cd Telegram
          python score_bot.py

      - name: Pull latest changes
        run: |
          git config --global user.name 'github-actions[bot]'
          git config --global user.email 'github-actions[bot]@users.noreply.github.com'
          git stash
          git pull origin main --rebase
          git stash pop || true

      - name: Save memory to prevent duplicates
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "chore: auto-update posted scores [skip ci]"
          file_pattern: "Telegram/posted_scores.txt"
