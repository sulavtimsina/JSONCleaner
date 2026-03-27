# JSONCleaner

A macOS app that redacts long string values from JSON and cURL commands copied to the clipboard.

## Features

- **JSON cleaning**: Recursively replaces string values exceeding a configurable max length
- **cURL cleaning**: Auto-detects cURL commands and redacts long header values, bearer tokens, data payloads, and query parameters
- **Replacement format**: `<first 10 chars>_REDACTED_BECAUSE_TOO_LONG`
- **Auto-copy**: Cleaned output is automatically copied to the clipboard

## Installation

To build the `.app` bundle manually:

```
JSONCleaner.app/
  Contents/
    Info.plist
    MacOS/
      run          # bash launcher script
    Resources/
      json_cleaner.py
```

1. Create the directory structure above
2. Place the files in their respective locations
3. Make `run` executable: `chmod +x JSONCleaner.app/Contents/MacOS/run`
4. Double-click `JSONCleaner.app` to launch

## Requirements

- macOS 10.15+
- Python 3 with tkinter
