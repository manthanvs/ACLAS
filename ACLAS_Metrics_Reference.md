# ACLAS — Metrics Reference Guide

> **Based on actual source code analysis of:**
> - [`aclas-vscode-master/src/tracker.ts`](file:///c:/Users/MANTHAN/Downloads/ACLAS%20Project/aclas-vscode-master/src/tracker.ts)
> - [`aclas_backend/telemetry/models.py`](file:///c:/Users/MANTHAN/Downloads/ACLAS%20Project/aclas_backend/telemetry/models.py)

---

## How the System Works

The VS Code extension fires a **heartbeat every 30 seconds** while you are actively coding. Each heartbeat is a JSON payload sent to the Django backend API at `POST /api/heartbeats/`. The backend stores it as one `TelemetryEvent` row per heartbeat. All counters reset to zero after each send.

```
[VS Code Extension]  ──heartbeat every 30s──▶  [Django API]  ──▶  [SQLite DB]
    tracker.ts                                  /api/heartbeats/     TelemetryEvent
```

---

## Metric-by-Metric Breakdown

---

### 🕐 `timestamp`

| Property | Value |
|----------|-------|
| **Set by** | VS Code extension (client-side) |
| **When** | At the moment the heartbeat POST is sent |
| **Source code** | `timestamp: new Date().toISOString()` in `tracker.ts` |

**Explanation:**  
This is the client-side time — it tells you *when you were coding*, not when the server received it. Set as an ISO 8601 string (e.g. `2026-05-25T04:30:00.000Z`) by the extension at the instant of transmission.

---

### 📥 `received_at`

| Property | Value |
|----------|-------|
| **Set by** | Django server (auto) |
| **When** | When the database row is created |
| **Source code** | `received_at = models.DateTimeField(auto_now_add=True)` in `models.py` |

**Explanation:**  
Automatically stamped by the server when it saves the heartbeat to the database. The gap between `timestamp` and `received_at` reveals network latency or processing delay. You cannot set this manually — Django controls it entirely.

---

### ➕ `lines_added`

| Property | Value |
|----------|-------|
| **Set by** | VS Code extension |
| **Trigger** | Every text document change event |
| **Source code** | `onTextChange()` in `tracker.ts` |
| **Resets** | After every 30-second heartbeat |

**How it counts:**

```typescript
const insertedNewlines = (change.text.match(/\n/g) || []).length;
added += insertedNewlines > 0
    ? insertedNewlines                          // multi-line paste/enter
    : (change.text.trim().length > 0 ? 1 : 0); // single-line typing
```

| Action | Count |
|--------|-------|
| Press **Enter** | +1 |
| Paste 5-line block | +5 |
| Type characters on same line | +1 per change event |
| Paste single-line text | +1 |
| Delete only (nothing inserted) | 0 |

> ⚠️ This is not "lines of code written." It counts **line-change events** per 30-second interval — more accurately a proxy for typing intensity.

---

### ➖ `lines_deleted`

| Property | Value |
|----------|-------|
| **Set by** | VS Code extension |
| **Trigger** | Every text document change event |
| **Source code** | `onTextChange()` in `tracker.ts` |
| **Resets** | After every 30-second heartbeat |

**How it counts (two paths):**

```typescript
const linesInRange = change.range.end.line - change.range.start.line;

if (linesInRange > 0) {
    // Multi-line selection deleted
    deleted += linesInRange - insertedNewlines;   // net lines removed
} else if (change.rangeLength > 0 && change.text.length < change.rangeLength) {
    // Same-line character deletion (Backspace, Delete, Ctrl+Backspace)
    deleted += 1;
}
```

| Action | Counted? |
|--------|----------|
| Select 3 lines → Delete | ✅ +3 (net) |
| **Backspace** at end of line (merges lines) | ✅ +1 |
| **Backspace** within a single line | ✅ +1 |
| **Delete** key within a single line | ✅ +1 |
| **Ctrl+Backspace** (delete word) | ✅ +1 |
| Paste over selected text | ✅ net lines |

> 💡 **Is Backspace counted?** Yes — after our fix. Before, same-line deletions always gave 0, which caused heartbeats to be skipped (ACLAS thought you were idle). Now every deletion registers, ensuring continuous tracking.

> **Critical note:** If `linesAdded == 0` AND `linesDeleted == 0` for a full 30-second interval, ACLAS treats you as **idle** and skips the heartbeat. This is why the deletion fix matters — it prevents active deletion work from being miscounted as idle time.

---

### ⏱️ `active_seconds`

| Property | Value |
|----------|-------|
| **Set by** | VS Code extension |
| **Unit** | Seconds |
| **Source code** | `sendEvent()` in `tracker.ts` |
| **Resets** | After every 30-second heartbeat |

**How it counts:**

```typescript
const elapsedSeconds = Math.round((now - this.lastTickTime) / 1000);
if (this.linesAdded > 0 || this.linesDeleted > 0) {
    this.activeSeconds += elapsedSeconds;  // classify as active
} else {
    this.idleSeconds += elapsedSeconds;    // classify as idle
}
```

The 30-second window is classified as **active** only if any lines were added or deleted during it. This is an **all-or-nothing** classification per interval — if you typed at second 1 and did nothing for seconds 2–30, the whole 30s still goes to `active_seconds`.

---

### 💤 `idle_seconds`

Same accumulator logic as `active_seconds`, but receives the elapsed time when no edits occurred. If you scroll, click, switch focus to another app, or simply pause — that time goes here.

**Idle escalation:**
- After **4 consecutive idle intervals** (~2 min) → Warning toast shown
- After **12 consecutive idle intervals** (~6 min) → Tracker auto-discontinues

---

### 🔴 `errors`

| Property | Value |
|----------|-------|
| **Set by** | VS Code extension |
| **Trigger** | Every 5 seconds (throttled diagnostics poll) |
| **Source code** | `pollDiagnostics()` in `tracker.ts` |
| **Type** | Snapshot (not cumulative) |

**How it counts:**

```typescript
vscode.languages.getDiagnostics();   // gets ALL diagnostics in workspace
// counts only: d.severity === DiagnosticSeverity.Error
this.stressMetrics.errors = errorCount;  // REPLACES (not adds)
```

| Source | Counted? |
|--------|----------|
| TypeScript/ESLint red squiggles | ✅ Yes |
| Pylance Python errors | ✅ Yes |
| Java compilation errors | ✅ Yes |
| **Warnings** (yellow squiggles) | ❌ No |
| **Hints/Info** | ❌ No |
| Runtime exceptions (console) | ❌ No |

> This is a **snapshot** of how many errors exist right now across all open files in the workspace — it replaces the previous count rather than adding to it.

---

### 🔁 `repeated_errors`

| Property | Value |
|----------|-------|
| **Set by** | VS Code extension |
| **Trigger** | Every 5-second diagnostics poll |
| **Source code** | `pollDiagnostics()` in `tracker.ts` |

**How it counts:**

```typescript
// Compares current error messages to the previous poll's messages
if (this.previousErrorMessages.has(msg)) {
    this.stressMetrics.repeatedErrors++;  // same error still there
}
```

If the **exact same error message** appears in both the current 5-second poll and the previous poll, it's considered "repeated." This is the primary **frustration indicator** — it grows while you're stuck on the same error.

| Scenario | Result |
|----------|--------|
| Fix an error → new error appears | Not counted (different message) |
| Same "undefined is not a function" for 10s | +2 (seen in 2 consecutive polls) |
| Fix all errors | Goes to 0 |

---

### 🔨 `build_runs`

| Property | Value |
|----------|-------|
| **Set by** | VS Code extension |
| **Trigger** | `vscode.tasks.onDidStartTask` |
| **Source code** | `setupListeners()` in `tracker.ts` |

**What triggers it:**

```typescript
vscode.tasks.onDidStartTask(() => {
    this.stressMetrics.buildRuns++;
})
```

| Action | Counted? |
|--------|----------|
| VS Code Task starts (via `tasks.json`) | ✅ Yes |
| `npm run build` through Tasks panel | ✅ Yes |
| `python manage.py runserver` as a Task | ✅ Yes |
| **Typing a command manually in terminal** | ❌ No |
| **Pressing F5** (debugger) | ❌ No — that's a debug session |
| External terminal (Windows Terminal, cmd) | ❌ No |

> Only VS Code's own **Tasks system** triggers this counter.

---

### 💥 `build_failures`

| Property | Value |
|----------|-------|
| **Set by** | VS Code extension |
| **Trigger** | When a VS Code Task ends AND errors exist |
| **Source code** | `checkBuildFailureLoop()` in `tracker.ts` |

**How it counts:**

```typescript
vscode.tasks.onDidEndTask(() => {
    // After task finishes, check if workspace still has errors
    if (any DiagnosticSeverity.Error exists) {
        this.stressMetrics.buildFailures++;
    }
})
```

A build is considered **failed** if VS Code Task finishes AND there are still error diagnostics in the workspace afterwards. 3+ consecutive failures triggers a warning toast.

---

### 🔄 `file_switches`

| Property | Value |
|----------|-------|
| **Set by** | VS Code extension |
| **Trigger** | `vscode.window.onDidChangeActiveTextEditor` |
| **Source code** | `onEditorChange()` in `tracker.ts` |

**What triggers it:**

```typescript
vscode.window.onDidChangeActiveTextEditor(editor => {
    this.stressMetrics.fileSwitches++;
})
```

| Action | Counted? |
|--------|----------|
| Click a different file tab in VS Code | ✅ Yes |
| Open a new file | ✅ Yes |
| Click other split-editor panel | ✅ Yes |
| Close a file (another becomes active) | ✅ Yes |
| **Switch from VS Code → Browser** | ❌ No |
| **Switch from VS Code → Antigravity IDE** | ❌ No |
| **Alt+Tab between applications** | ❌ No |
| **VS Code → Windows Terminal** | ❌ No |

> **Answer to your question:** Only **tab-to-tab within VS Code**. Application-level switches (VS Code ↔ browser, VS Code ↔ anything else) are **OS-level events** — the VS Code API has no visibility into those.

---

### ↩️ `undo_count`

| Property | Value |
|----------|-------|
| **Set by** | VS Code extension |
| **Trigger** | Text change where new text is shorter than replaced text |
| **Source code** | `onTextChange()` in `tracker.ts` |
| **Method** | Heuristic (no direct Ctrl+Z API in VS Code) |

**How it counts:**

```typescript
if (change.rangeLength > 0 && change.text.length < change.rangeLength) {
    this.stressMetrics.undoCount++;
}
```

VS Code does **not expose a "user pressed Ctrl+Z" event**. Instead, ACLAS uses a heuristic: if existing text was replaced with something shorter (or nothing), it looks like an undo/deletion.

| Action | Counted? |
|--------|----------|
| `Ctrl+Z` (undo) | ✅ Usually — restores shorter/empty content |
| Backspace (1 char) | ✅ Yes — `rangeLength=1`, inserted `length=0` |
| Delete key | ✅ Yes |
| Select text and type shorter replacement | ✅ Yes |
| Select text and type **longer** replacement | ❌ No |
| `Ctrl+Y` / Redo (inserts text back) | ❌ No — text gets longer |

> ⚠️ This is a **heuristic, not exact**. It overlaps with `lines_deleted` because Backspace also matches both conditions. The stress value comes from its *frequency* — a high undo count signals rework and frustration regardless of exact source.

---

### 💻 `terminal_errors`

| Property | Value |
|----------|-------|
| **Set by** | VS Code extension |
| **Trigger** | Two methods (exit code + keyword scan) |
| **Source code** | `onTerminalExecutionEnd()` + `onTerminalExecutionStart()` in `tracker.ts` |
| **Terminal scope** | VS Code integrated terminal only |

**Method 1 — Exit code detection:**
```typescript
vscode.window.onDidEndTerminalShellExecution(e => {
    if (e.exitCode !== undefined && e.exitCode !== 0) {
        this.stressMetrics.terminalErrors++;
    }
})
```

**Method 2 — Output keyword scan:**
```typescript
const TERMINAL_ERROR_PATTERN = /\b(error|failed|exception|fatal|traceback)\b/i
// Scans terminal output stream as command runs
```

| Trigger | Counted? |
|---------|----------|
| Command exits with non-zero code (`node app.js` crashes) | ✅ Method 1 |
| Terminal output contains "error", "failed", "exception", "fatal", "traceback" | ✅ Method 2 |
| Successful `git push` (exit 0) | ❌ |
| `npm install` deprecation warnings | ❌ (not a keyword match) |
| **External terminal (Windows Terminal, cmd.exe)** | ❌ No — only VS Code integrated terminal |

---

## Summary Table

| Metric | Set By | Frequency | Resets After Send? |
|--------|--------|-----------|-------------------|
| `timestamp` | Extension | Each heartbeat | — |
| `received_at` | Django server | Each heartbeat | — |
| `lines_added` | Extension | Per keystroke | ✅ Yes |
| `lines_deleted` | Extension | Per keystroke | ✅ Yes |
| `active_seconds` | Extension | Per 30s window | ✅ Yes |
| `idle_seconds` | Extension | Per 30s window | ✅ Yes |
| `errors` | Extension | Every 5s poll | ✅ Yes (snapshot replaced) |
| `repeated_errors` | Extension | Every 5s poll | ✅ Yes |
| `build_runs` | Extension | On task start | ✅ Yes |
| `build_failures` | Extension | On task end | ✅ Yes |
| `file_switches` | Extension | On editor tab change | ✅ Yes |
| `undo_count` | Extension | Per keystroke (heuristic) | ✅ Yes |
| `terminal_errors` | Extension | On terminal command | ✅ Yes |

---

## Stress Score Formula

Calculated as a `@property` on the Django model — not stored in the DB, computed on read:

```python
raw = (
    errors          * 3 +
    repeated_errors * 5 +   # highest weight — persistent frustration
    build_failures  * 4 +
    file_switches   * 1 +   # lowest weight — normal navigation
    undo_count      * 2 +
    terminal_errors * 3
)
stress_score = min(100, raw)
```

| Score Range | Label | Colour |
|-------------|-------|--------|
| 0 | No stress signals | Grey `—` |
| 1 – 30 | Low | 🟢 Teal |
| 31 – 60 | Medium | 🟡 Yellow |
| 61 – 100 | High | 🔴 Red |

---

*Document generated from ACLAS source code — `tracker.ts` + `models.py`*  
*Last updated: 2026-05-25*
