# ACLAS — Advanced Coding Lifecycle Analytics System

[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/manthanvs.aclas?label=VS%20Marketplace&logo=visual-studio-code)](https://marketplace.visualstudio.com/items?itemName=manthanvs.aclas)
[![Installs](https://img.shields.io/visual-studio-marketplace/i/manthanvs.aclas)](https://marketplace.visualstudio.com/items?itemName=manthanvs.aclas)

> **Monitor your coding health. Detect developer stress. Understand your workflow.**

ACLAS is a VS Code extension that silently tracks your coding activity and sends rich telemetry heartbeats to your personal ACLAS Django dashboard — giving you deep insights into your productivity, stress levels, and coding patterns.

---

## ✨ Features

- 🫀 **Heartbeat Telemetry** — Sends coding activity data every 30 seconds (lines added, deleted, active/idle time)
- 🧠 **Stress Score Detection** — Detects developer stress signals in real time:
  - Error count & repeated errors
  - Build runs & consecutive build failures
  - File switch frequency
  - Undo actions
  - Terminal error exit codes
- 📊 **Per-Project Analytics** — Tracks metrics per project and programming language
- 💤 **Idle Detection** — Automatically pauses tracking after 15 minutes of inactivity
- 🔒 **Secure Token Storage** — API token stored in VS Code's secure secret storage (never in plain text)
- ⚠️ **Smart Warnings** — Notifies you when you've been idle too long or have repeated build failures

---

## 🚀 Getting Started

### 1. Set Up Your ACLAS Backend

Make sure your ACLAS Django backend is running. You can run it locally:

```bash
cd aclas_backend
python manage.py runserver
```

### 2. Get Your API Token

1. Open your ACLAS Dashboard in the browser (by default at `http://localhost:8000`)
2. Log in to your account
3. Navigate to **Settings** → copy your API Token

### 3. Connect the Extension

1. In VS Code, press `F1` (or `Ctrl+Shift+P`)
2. Type and run: **`ACLAS: Enter API Token`**
3. Paste your token and press Enter

### 4. Start Coding!

The extension activates automatically when VS Code starts. Open any project and start coding — ACLAS will silently track your session and send heartbeats to your dashboard.

---

## ⚙️ Configuration

| Setting | Default | Description |
|---|---|---|
| `aclas.serverEntrypoint` | `http://localhost:8000/api/heartbeats/` | URL to your ACLAS backend heartbeat API |

To change the backend URL:
- Go to **Settings** (`Ctrl+,`) and search for `aclas`
- Or edit your `settings.json` directly

---

## 📡 Telemetry Data Sent

Each heartbeat payload contains:

```json
{
  "timestamp": "2026-04-21T10:00:00Z",
  "project_name": "my-project",
  "language": "python",
  "file": "src/main.py",
  "lines_added": 12,
  "lines_deleted": 3,
  "active_seconds": 28,
  "idle_seconds": 2,
  "errors": 2,
  "repeated_errors": 1,
  "build_runs": 1,
  "build_failures": 0,
  "file_switches": 4,
  "undo_count": 2,
  "terminal_errors": 0
}
```

---

## 🧮 Stress Metrics Explained

| Metric | What It Measures |
|---|---|
| `errors` | Number of active error diagnostics in the editor |
| `repeated_errors` | Errors that appeared in the previous poll (developer is stuck) |
| `build_runs` | Times a VS Code task was started (compile, test, etc.) |
| `build_failures` | Tasks that ended with errors still present |
| `file_switches` | Number of times the active editor tab changed |
| `undo_count` | Heuristic count of undo operations |
| `terminal_errors` | Terminal commands that exited with a non-zero code |

These metrics are combined on the dashboard into a **Stress Score** to help you identify coding sessions where you may need a break.

---

## 🔧 Commands

| Command | Description |
|---|---|
| `ACLAS: Enter API Token` | Set or update your backend API token |
| `ACLAS: Stop Tracking` | Manually pause telemetry for the current session |

---

## 🛡️ Privacy

- All data is sent **only to your own backend** — no third-party servers
- Your API token is stored in VS Code's **SecretStorage** (OS keychain)
- You can stop tracking at any time via the command palette

---

## 📝 License

MIT © Manthan

---

## 🔗 Links

- [Report an Issue](https://github.com/manthanvs/aclas/issues)
- [View on GitHub](https://github.com/manthanvs/aclas)
