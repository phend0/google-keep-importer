import json
import os
import subprocess
import time
import tempfile
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
# Path to the folder containing your Google Keep JSON notes (from Google Takeout)
NOTES_PATH = os.getenv('KEEP_NOTES_PATH', './notes')

# Port to use for Chrome remote debugging
DEBUG_PORT = 9222

# File to track progress and allow resuming
PROGRESS_FILE = 'keep_progress.json'

# --- BROWSER SELECTORS ---
# These may need updates if Google Keep's UI changes
CREATOR = '.di8rgd-r4nke:not(.RNfche)'
BODY_AREA = f'{CREATOR} .IZ65Hb-TBnied'
TITLE_INPUT = f'{CREATOR} [role="textbox"]'
TIMEOUT = 5000


def find_chrome():
    """Attempt to find the Chrome executable on the system."""
    if os.name == 'nt':  # Windows
        paths = [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
        ]
        for path in paths:
            if os.path.exists(path):
                return path
    elif os.name == 'posix':  # macOS / Linux
        paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/usr/bin/google-chrome',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
        ]
        for path in paths:
            if os.path.exists(path):
                return path
    return None


def load_notes():
    """Load and parse JSON notes from the NOTES_PATH."""
    notes = []
    if not os.path.exists(NOTES_PATH):
        print(f"ERROR: Directory not found: {NOTES_PATH}")
        print("Please ensure your notes are in the './notes' folder or set KEEP_NOTES_PATH.")
        return []

    for filename in sorted(os.listdir(NOTES_PATH)):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(NOTES_PATH, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Skip trashed or archived if desired. Here we just skip trashed.
            if not data.get('isTrashed', False):
                notes.append(data)
        except Exception as e:
            print(f"  Error reading {filename}: {e}")
    return notes


def create_note(page, title, text):
    """Automate the creation of a single note in Google Keep."""
    # Ensure any open editor is closed
    page.keyboard.press('Escape')
    page.wait_for_timeout(150)

    # Open the editor by clicking the body area
    page.locator(BODY_AREA).click(timeout=TIMEOUT)
    page.wait_for_timeout(200)

    if text:
        page.keyboard.type(text)

    if title:
        page.locator(TITLE_INPUT).click(timeout=TIMEOUT)
        page.keyboard.type(title)

    # Escape saves and closes the note
    page.keyboard.press('Escape')
    page.wait_for_timeout(150)


def migrate_notes():
    chrome_path = find_chrome()
    if not chrome_path:
        print("ERROR: Could not find Google Chrome. Please install it or update the script with the correct path.")
        return

    notes = load_notes()
    if not notes:
        return

    print(f"Found {len(notes)} notes to import.\n")

    # Use a temp profile so Chrome launches as a new instance
    temp_profile = os.path.join(tempfile.gettempdir(), 'chrome_keep_import_profile')
    
    # Launch Chrome with remote debugging enabled
    subprocess.Popen([
        chrome_path,
        f'--remote-debugging-port={DEBUG_PORT}',
        f'--user-data-dir={temp_profile}',
        '--no-first-run',
        '--no-default-browser-check',
        'https://keep.google.com',
    ])

    print("=" * 60)
    print("STEP 1: A Chrome window has opened.")
    print("STEP 2: Log in to Google Keep manually.")
    print("STEP 3: Once you see your notes list, return here.")
    print("STEP 4: Press Enter to start the automated import...")
    print("=" * 60)
    input()

    with sync_playwright() as p:
        browser = None
        for _ in range(10):
            try:
                browser = p.chromium.connect_over_cdp(f'http://localhost:{DEBUG_PORT}')
                break
            except Exception:
                time.sleep(1)
        
        if browser is None:
            print("ERROR: Could not connect to Chrome. Make sure Chrome opened successfully.")
            return

        context = browser.contexts[0]
        # Find or open the Keep tab
        keep_pages = [pg for pg in context.pages if 'keep.google.com' in pg.url]
        page = keep_pages[0] if keep_pages else context.new_page()

        if 'keep.google.com' not in page.url:
            page.goto('https://keep.google.com')
            page.wait_for_timeout(2000)

        page.bring_to_front()

        # Load progress (resume from where we left off)
        start_index = 0
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE, 'r') as f:
                    start_index = json.load(f).get('next_index', 0)
                print(f"Resuming from note {start_index + 1}...\n")
            except Exception:
                pass

        imported = 0
        failed = 0
        total = len(notes)

        for i, data in enumerate(notes):
            if i < start_index:
                continue

            title = data.get('title', '')
            text = data.get('textContent', '').strip()

            # Some notes might have list content instead of textContent
            if not text and 'listContent' in data:
                text = "\n".join([f"- {item['text']}" for item in data['listContent']])

            if not title and not text:
                print(f"  [{i+1}/{total}] Skipping empty note")
                with open(PROGRESS_FILE, 'w') as f:
                    json.dump({'next_index': i + 1}, f)
                continue

            try:
                create_note(page, title, text)
                print(f"  [{i+1}/{total}] Created: {title or '(no title)'}")
                imported += 1
            except Exception as e:
                print(f"  [{i+1}/{total}] FAILED: {title or '(no title)'} — {e}")
                failed += 1
                try:
                    page.keyboard.press('Escape')
                    page.wait_for_timeout(150)
                except Exception:
                    pass

            # Save progress after every note
            with open(PROGRESS_FILE, 'w') as f:
                json.dump({'next_index': i + 1}, f)

        print(f"\nFinished! Processed {total} notes.")
        print(f"Success: {imported}, Failed: {failed}")
        
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)


if __name__ == '__main__':
    migrate_notes()
