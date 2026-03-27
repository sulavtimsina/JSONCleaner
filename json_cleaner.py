#!/usr/bin/env python3
import json
import shlex
import subprocess
import tkinter as tk
from tkinter import scrolledtext
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


DEFAULT_MAX_LENGTH = 50


def make_replacement(original):
    """Produce a redacted placeholder preserving the first 10 chars of the original."""
    prefix = original[:10]
    return f"{prefix}_REDACTED_BECAUSE_TOO_LONG"


def get_clipboard():
    result = subprocess.run(["pbpaste"], capture_output=True, text=True)
    return result.stdout


def set_clipboard(text):
    process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
    process.communicate(text.encode("utf-8"))


def is_curl_command(text):
    """Return True if text looks like a curl command."""
    stripped = text.lstrip()
    return stripped.startswith("curl ")


def redact_if_long(value, max_length):
    """Return (possibly redacted value, 1 if redacted else 0)."""
    if len(value) > max_length:
        return make_replacement(value), 1
    return value, 0


def clean_header_value(header, max_length):
    """Redact the value portion of a header ('Key: Value') if too long."""
    parts = header.split(":", 1)
    if len(parts) == 2:
        key, val = parts[0], parts[1].lstrip()
        redacted, count = redact_if_long(val, max_length)
        return f"{key}: {redacted}", count
    return redact_if_long(header, max_length)


def clean_url(url, max_length):
    """Redact long query parameter values in a URL."""
    count = 0
    parsed = urlparse(url)
    if not parsed.query:
        return redact_if_long(url, max_length)
    params = parse_qs(parsed.query, keep_blank_values=True)
    cleaned_params = {}
    for key, values in params.items():
        cleaned_values = []
        for v in values:
            redacted, c = redact_if_long(v, max_length)
            cleaned_values.append(redacted)
            count += c
        cleaned_params[key] = cleaned_values
    new_query = urlencode(cleaned_params, doseq=True)
    cleaned_url = urlunparse(parsed._replace(query=new_query))
    return cleaned_url, count


def clean_curl_command(text, max_length):
    """Parse and clean a curl command, redacting long values."""
    replaced_count = 0
    try:
        tokens = shlex.split(text)
    except ValueError:
        return text, 0

    # Normalize tokens: some tools (e.g. Charles Proxy) embed newlines inside
    # quoted arguments like '\n-H', '\n--data-raw'. Strip whitespace so flags
    # are recognised correctly.
    tokens = [t.strip() for t in tokens]
    # Remove empty tokens that may result from stripping
    tokens = [t for t in tokens if t]

    cleaned_tokens = []
    i = 0
    data_flags = {"-d", "--data", "--data-raw", "--data-binary", "--data-urlencode"}
    header_flags = {"-H", "--header"}

    while i < len(tokens):
        token = tokens[i]

        if token in data_flags and i + 1 < len(tokens):
            cleaned_tokens.append(token)
            i += 1
            value = tokens[i]
            # Try parsing as JSON
            try:
                parsed = json.loads(value)
                cleaned, count = clean_json_value(parsed, max_length)
                replaced_count += count
                cleaned_tokens.append(json.dumps(cleaned, ensure_ascii=False))
            except (json.JSONDecodeError, TypeError):
                redacted, count = redact_if_long(value, max_length)
                replaced_count += count
                cleaned_tokens.append(redacted)

        elif token in header_flags and i + 1 < len(tokens):
            cleaned_tokens.append(token)
            i += 1
            cleaned_header, count = clean_header_value(tokens[i], max_length)
            replaced_count += count
            cleaned_tokens.append(cleaned_header)

        elif not token.startswith("-") and token != "curl" and ("://" in token or token.startswith("http")):
            cleaned_url, count = clean_url(token, max_length)
            replaced_count += count
            cleaned_tokens.append(cleaned_url)

        elif token.startswith("-") and "=" in token:
            # Handle --flag=value style
            flag, value = token.split("=", 1)
            redacted, count = redact_if_long(value, max_length)
            replaced_count += count
            cleaned_tokens.append(f"{flag}={redacted}")

        else:
            cleaned_tokens.append(token)

        i += 1

    # Reassemble with proper quoting
    parts = []
    for t in cleaned_tokens:
        if t == "curl" or t.startswith("-"):
            parts.append(t)
        else:
            parts.append(shlex.quote(t))
    return " ".join(parts), replaced_count


def clean_json_value(obj, max_length):
    """Recursively replace string values longer than max_length."""
    replaced_count = 0
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            cleaned, count = clean_json_value(v, max_length)
            new_dict[k] = cleaned
            replaced_count += count
        return new_dict, replaced_count
    elif isinstance(obj, list):
        new_list = []
        for item in obj:
            cleaned, count = clean_json_value(item, max_length)
            new_list.append(cleaned)
            replaced_count += count
        return new_list, replaced_count
    elif isinstance(obj, str) and len(obj) > max_length:
        return make_replacement(obj), 1
    else:
        return obj, 0


class JSONCleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JSON Cleaner")
        self.root.geometry("700x520")
        self.root.resizable(True, True)
        self.root.configure(bg="#2b2b2b")

        # Header
        header = tk.Label(
            root,
            text="JSON String Cleaner",
            font=("Helvetica", 18, "bold"),
            bg="#2b2b2b",
            fg="#ffffff",
        )
        header.pack(pady=(15, 5))

        # Max length setting row
        setting_frame = tk.Frame(root, bg="#2b2b2b")
        setting_frame.pack(pady=(5, 10))

        tk.Label(
            setting_frame,
            text="Max allowed string length:",
            font=("Helvetica", 12),
            bg="#2b2b2b",
            fg="#aaaaaa",
        ).pack(side="left", padx=(0, 5))

        self.max_length_var = tk.StringVar(value=str(DEFAULT_MAX_LENGTH))
        self.max_length_entry = tk.Entry(
            setting_frame,
            textvariable=self.max_length_var,
            font=("Menlo", 13),
            width=5,
            bg="#1e1e1e",
            fg="#ffffff",
            insertbackground="white",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#555555",
            highlightcolor="#007ACC",
            justify="center",
        )
        self.max_length_entry.pack(side="left", padx=(0, 5))

        tk.Label(
            setting_frame,
            text="chars",
            font=("Helvetica", 12),
            bg="#2b2b2b",
            fg="#aaaaaa",
        ).pack(side="left")

        # Buttons frame
        btn_frame = tk.Frame(root, bg="#2b2b2b")
        btn_frame.pack(pady=5)

        self.paste_btn = tk.Button(
            btn_frame,
            text="Paste & Clean",
            font=("Helvetica", 14, "bold"),
            bg="#4CAF50",
            fg="white",
            activebackground="#45a049",
            activeforeground="white",
            relief="flat",
            padx=30,
            pady=8,
            command=self.paste_and_clean,
        )
        self.paste_btn.pack(side="left", padx=5)

        self.copy_btn = tk.Button(
            btn_frame,
            text="Copy Result",
            font=("Helvetica", 14),
            bg="#2196F3",
            fg="white",
            activebackground="#1976D2",
            activeforeground="white",
            relief="flat",
            padx=30,
            pady=8,
            command=self.copy_result,
            state="disabled",
        )
        self.copy_btn.pack(side="left", padx=5)

        self.clear_btn = tk.Button(
            btn_frame,
            text="Clear",
            font=("Helvetica", 14),
            bg="#757575",
            fg="white",
            activebackground="#616161",
            activeforeground="white",
            relief="flat",
            padx=30,
            pady=8,
            command=self.clear_result,
        )
        self.clear_btn.pack(side="left", padx=5)

        # Text area
        text_frame = tk.Frame(root, bg="#2b2b2b")
        text_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.text_area = scrolledtext.ScrolledText(
            text_frame,
            wrap="word",
            font=("Menlo", 12),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white",
            selectbackground="#264f78",
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#555555",
        )
        self.text_area.pack(fill="both", expand=True)
        self.text_area.insert("1.0", "Click 'Paste & Clean' to process JSON or cURL from clipboard...")
        self.text_area.configure(state="disabled")

        # Status bar
        self.status_frame = tk.Frame(root, bg="#007ACC", height=30)
        self.status_frame.pack(fill="x", side="bottom")
        self.status_frame.pack_propagate(False)

        self.status_label = tk.Label(
            self.status_frame,
            text="Ready - Copy JSON or cURL to clipboard and click 'Paste & Clean'",
            font=("Helvetica", 11),
            bg="#007ACC",
            fg="white",
            anchor="w",
            padx=10,
        )
        self.status_label.pack(fill="both", expand=True)

        self.cleaned_json = None

    def set_status(self, message, color):
        self.status_frame.configure(bg=color)
        self.status_label.configure(text=message, bg=color)

    def get_max_length(self):
        try:
            val = int(self.max_length_var.get().strip())
            if val < 1:
                return None
            return val
        except ValueError:
            return None

    def paste_and_clean(self):
        max_len = self.get_max_length()
        if max_len is None:
            self.set_status("Invalid max length - enter a positive number", "#f44336")
            self.max_length_entry.focus_set()
            return

        clipboard_text = get_clipboard().strip()

        if not clipboard_text:
            self.set_status("Clipboard is empty", "#f44336")
            self.show_text("Clipboard is empty. Copy some JSON or cURL first.")
            self.copy_btn.configure(state="disabled")
            return

        if is_curl_command(clipboard_text):
            self.set_status("Detected: cURL command. Processing...", "#FF9800")
            cleaned_result, replaced_count = clean_curl_command(clipboard_text, max_len)
            self.cleaned_json = cleaned_result
            set_clipboard(self.cleaned_json)
            self.show_text(self.cleaned_json)
            self.copy_btn.configure(state="normal")
            kind = "cURL"
        else:
            # Try to parse JSON
            try:
                parsed = json.loads(clipboard_text)
            except json.JSONDecodeError as e:
                self.set_status(f"Not valid JSON or cURL: {e}", "#f44336")
                self.show_text(f"Clipboard does not contain valid JSON or a cURL command.\n\n{e}\n\nRaw content:\n{clipboard_text[:2000]}")
                self.copy_btn.configure(state="disabled")
                return

            self.set_status("Detected: JSON. Processing...", "#FF9800")
            cleaned, replaced_count = clean_json_value(parsed, max_len)
            self.cleaned_json = json.dumps(cleaned, indent=2, ensure_ascii=False)
            set_clipboard(self.cleaned_json)
            self.show_text(self.cleaned_json)
            self.copy_btn.configure(state="normal")
            kind = "JSON"

        if replaced_count > 0:
            self.set_status(
                f"Detected: {kind} - Replaced {replaced_count} string(s) longer than {max_len} chars. Copied to clipboard.",
                "#4CAF50",
            )
        else:
            self.set_status(
                f"Detected: {kind} - No strings > {max_len} chars found. Copied to clipboard.",
                "#4CAF50",
            )

    def copy_result(self):
        if self.cleaned_json:
            set_clipboard(self.cleaned_json)
            self.set_status("Result copied to clipboard!", "#4CAF50")

    def clear_result(self):
        self.cleaned_json = None
        self.show_text("Click 'Paste & Clean' to process JSON or cURL from clipboard...")
        self.copy_btn.configure(state="disabled")
        self.set_status("Ready - Copy JSON or cURL to clipboard and click 'Paste & Clean'", "#007ACC")

    def show_text(self, text):
        self.text_area.configure(state="normal")
        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", text)
        self.text_area.configure(state="disabled")


if __name__ == "__main__":
    # On macOS, bring the tkinter window to the front when launched as .app
    import platform
    if platform.system() == "Darwin":
        import os
        os.system(
            """/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' 2>/dev/null &"""
        )

    root = tk.Tk()

    # Force the window to appear on top
    root.lift()
    root.attributes("-topmost", True)
    root.after(100, lambda: root.attributes("-topmost", False))
    root.update_idletasks()

    # Bring to front on macOS
    root.createcommand("tk::mac::ReopenApplication", root.lift)

    app = JSONCleanerApp(root)
    root.mainloop()
