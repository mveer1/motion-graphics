"""Path of the Chrome/Chromium binary Playwright should drive. Override with env CHROME=/path/to/chrome.
None => Playwright's own bundled chromium (run `playwright install chromium` once)."""
import os
EXE = os.environ.get('CHROME') or ('/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None)
