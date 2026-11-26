# ISBN checker script

Checks ISBNs in a Google Sheet against Open Library and Google Books, fills in book metadata, and updates a status dashboard.

## Setup

1. Install Python 3 and dependencies: `python -m pip install -r requirements.txt`.
2. Place a Google service account key in `credentials.json` beside the script, or set `GOOGLE_APPLICATION_CREDENTIALS` to its path. The credential file is ignored by Git.
3. Share the Google Sheet named **ISBN SEARCH** with the service account's `client_email`. The script uses the **ISBN_CHECKER** worksheet.
4. Optionally set `GOOGLE_BOOKS_API_KEY` for Google Books requests. Without it, the script makes requests without an API key.
5. Run `python isbn_async_processor.py`. Stop it with Ctrl+C.

The script reads ISBNs from column A, uses column H for processing status, writes results to columns B–H, and maintains a dashboard in K2:L19. It checks for new rows every five seconds.
