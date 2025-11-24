name: Trade Email Scraper

on:
  schedule:
    # Runs at minute 0 past every hour (Adjust as needed)
    - cron: '0 * * * *'
  workflow_dispatch: # Allows you to manually trigger the button to test it

jobs:
  check_trades:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run Trade Bot
        env:
          EMAIL_USER: ${{ secrets.EMAIL_USER }}
          EMAIL_PASS: ${{ secrets.EMAIL_PASS }}
          GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
        run: python trade_bot.py
