# JSONCleaner

A macOS app that redacts long string values from JSON and cURL commands copied to the clipboard.

## Features

- **JSON cleaning**: Recursively replaces string values exceeding a configurable max length
- **cURL cleaning**: Auto-detects cURL commands and redacts long header values, bearer tokens, data payloads, and query parameters
- **Replacement format**: `<first 10 chars>_REDACTED_BECAUSE_TOO_LONG`
- **Auto-copy**: Cleaned output is automatically copied to the clipboard

## Quick Install

Run this in Terminal to download and install the app:

```bash
cd ~/Desktop && curl -L https://github.com/sulavtimsina/JSONCleaner/archive/refs/heads/main.zip -o /tmp/JSONCleaner.zip && unzip -o /tmp/JSONCleaner.zip -d /tmp && cp -R /tmp/JSONCleaner-main/JSONCleaner.app ~/Desktop/ && chmod +x ~/Desktop/JSONCleaner.app/Contents/MacOS/run && rm /tmp/JSONCleaner.zip && rm -rf /tmp/JSONCleaner-main && open ~/Desktop/JSONCleaner.app
```

This downloads the app to your Desktop and launches it.

## Manual Install

1. [Download the repo as ZIP](https://github.com/sulavtimsina/JSONCleaner/archive/refs/heads/main.zip)
2. Unzip and copy `JSONCleaner.app` to your Desktop (or Applications folder)
3. Open Terminal and run: `chmod +x ~/Desktop/JSONCleaner.app/Contents/MacOS/run`
4. Double-click `JSONCleaner.app` to launch

> **Note**: The `chmod` step is required because GitHub does not preserve executable permissions in ZIP downloads.

## Requirements

- macOS 10.15+
- Python 3 with tkinter
