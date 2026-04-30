# Changelog

All notable changes to the **ACLAS** extension will be documented here.

## [1.0.0] — 2026-04-21

### 🚀 Initial Release

- **Heartbeat telemetry**: Sends coding activity to your ACLAS Django backend every 30 seconds
- **Stress metric tracking**:
  - Error count & repeated error detection (via VS Code diagnostics API)
  - Build run & build failure loop detection (via VS Code tasks API)
  - File switch frequency tracking
  - Undo operation heuristic counter
  - Terminal error detection (non-zero exit codes & error keyword scanning)
- **Idle detection**: Automatically pauses after 15 minutes of inactivity
- **Smart warnings**: Toast notifications for prolonged idle sessions and repeated build failures
- **Secure token storage**: API token stored in VS Code's SecretStorage (OS keychain integration)
- **Per-project & per-language tracking**: Automatically detects workspace folder name and active language
- **Commands**:
  - `ACLAS: Enter API Token` — set or update your backend authentication token  
  - `ACLAS: Stop Tracking` — manually pause telemetry for the current session
- **Configurable backend URL**: Point the extension to any ACLAS server via `aclas.serverEntrypoint` setting
