# ACLAS — Adaptive Coding Lifecycle Analytics System

<p align="center">
  <img src="aclas-vscode-master/images/logo.png" alt="ACLAS Logo" width="80"/>
</p>

<p align="center">
  <strong>Track. Analyze. Improve.</strong><br/>
  A full-stack developer analytics platform — VS Code extension + Django dashboard.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white"/>
  <img src="https://img.shields.io/badge/TypeScript-5.8-3178c6?style=for-the-badge&logo=typescript&logoColor=white"/>
  <img src="https://img.shields.io/badge/VS%20Code-Extension-007acc?style=for-the-badge&logo=visualstudiocode&logoColor=white"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge"/>
</p>

---

## 📌 What is ACLAS?

**ACLAS** (Adaptive Coding Lifecycle Analytics System) is a self-hosted developer productivity tracker built as a university project. It consists of:

- 🔌 **VS Code Extension** — silently tracks your keystrokes, file activity, lines added/deleted, and active vs idle time
- 🖥️ **Django Backend** — REST API that ingests telemetry heartbeats and stores them securely per user
- 📊 **Analytics Dashboard** — server-rendered UI with real-time charts, session history, and API token management

---

## ✨ Features

### VS Code Plugin
- ⌨️ Real-time keystroke tracking with 30-second heartbeat intervals
- 📁 Project name = **filename.extension** (e.g. `tracker.ts`, `views.py`)
- 💤 Idle detection — skips heartbeats when no typing occurs
- ⏱️ Active vs Idle time tracked per session
- 🔔 Toast warnings after 2 min idle; auto-discontinues after 6 min
- 🛑 `Ctrl+Shift+P` → **ACLAS: Stop Tracking** command
- 🔑 `Ctrl+Shift+P` → **ACLAS: Enter API Token** to connect to your dashboard

### Django Backend
- 🔐 Email + Google OAuth authentication (via `django-allauth`)
- 🧩 Token-based API authentication (Django REST Framework)
- 🗂️ Per-user telemetry storage with full session history
- 👥 Role-based access: Developer / Manager
- 🛡️ CSRF protection, duplicate-account prevention

### Dashboard UI
- 🌑 Synthetix Dark theme — VS Code inspired glassmorphism
- 📈 6 stat cards: Events, Lines Added/Deleted, Active Time, Idle Time, Total Time
- 🍩 Chart.js charts: Top Projects (bar) + Language Distribution (doughnut)
- 🔍 Stats page with live search + language filter
- ⚙️ Settings page with API token display + profile management
- ✨ Cursor glow, parallax orbs, entrance animations, hover lift effects

---

## 🖼️ Screenshots

> _Start the server locally and add your screenshots here_

| Dashboard | Login | Stats |
|---|---|---|
| _(paste screenshot)_ | _(paste screenshot)_ | _(paste screenshot)_ |

---

## 🏗️ Architecture

```
┌─────────────────────┐        Heartbeat POST        ┌──────────────────────┐
│  VS Code Extension  │  ───────────────────────────▶ │   Django REST API    │
│  (aclas-vscode-     │   /api/heartbeats/            │   TokenAuthentication│
│   master/)          │   Authorization: Token <key>  │                      │
└─────────────────────┘                               └──────────┬───────────┘
                                                                 │
                                                          SQLite DB
                                                                 │
                                                      ┌──────────▼───────────┐
                                                      │  Django Templates    │
                                                      │  Dashboard / Stats / │
                                                      │  Settings / Auth     │
                                                      └──────────────────────┘
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- VS Code

---

### 1️⃣ Backend Setup

```bash
cd aclas_backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install django djangorestframework django-allauth

# Run migrations
python manage.py migrate

# Create a superuser (for admin panel)
python manage.py createsuperuser

# Start the server
python manage.py runserver
```

Visit → **http://127.0.0.1:8000/**

---

### 2️⃣ Google OAuth Setup (Optional)

1. Create a project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable the **Google Identity API**
3. Create OAuth credentials → Web App
   - Redirect URI: `http://127.0.0.1:8000/accounts/google/login/callback/`
4. In Django Admin → **Social Applications** → Add Google app with your Client ID + Secret

---

### 3️⃣ VS Code Extension Setup

```bash
cd aclas-vscode-master

# Install dependencies (use cmd.exe on Windows)
npm.cmd install

# Compile
npm.cmd run compile
```

- Open `aclas-vscode-master` in VS Code
- Press **F5** to launch the Extension Development Host
- Press `Ctrl+Shift+P` → **ACLAS: Enter API Token**
- Paste the token from your dashboard (`http://127.0.0.1:8000/`)

---

## 📁 Project Structure

```
ACLAS/
├── aclas_backend/              # Django project
│   ├── aclas/                  # Core settings & URLs
│   ├── analytics/              # Dashboard views, charts, templates
│   │   ├── static/analytics/   # aclas.css + aclas.js (design system)
│   │   └── templates/          # All HTML pages
│   └── telemetry/              # Heartbeat API, models, serializers
│
└── aclas-vscode-master/        # VS Code Extension
    └── src/
        ├── extension.ts        # Entry point, command registration
        ├── tracker.ts          # Core tracking + idle logic
        └── api.ts              # HTTP heartbeat sender
```

---

## 🔌 API Reference

### `POST /api/heartbeats/`

**Headers:**
```
Authorization: Token <your-api-token>
Content-Type: application/json
```

**Body:**
```json
{
  "project_name": "tracker.ts",
  "language": "typescript",
  "lines_added": 12,
  "lines_deleted": 3,
  "active_seconds": 28,
  "idle_seconds": 2
}
```

**Response:** `201 Created`

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend Framework | Django 6 + Django REST Framework |
| Authentication | django-allauth (Email + Google OAuth) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Django Templates + Vanilla JS + Chart.js |
| CSS | Custom design system (Synthetix Dark) |
| VS Code Extension | TypeScript + Webpack |
| HTTP Client (plugin) | got 14 |

---

## 📄 License

© [manthanvs](https://github.com/manthanvs)
