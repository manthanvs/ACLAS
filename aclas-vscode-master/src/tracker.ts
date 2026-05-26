import * as vscode from 'vscode';
import { sendHeartbeat } from './api';

export class AclasTracker {
    private token: string = '';
    private idleTimer: NodeJS.Timeout | null = null;
    private heartbeatTimer: NodeJS.Timeout | null = null;
    private isActive: boolean = false;
    private isStopped: boolean = false;  // manual stop flag

    private linesAdded: number = 0;
    private linesDeleted: number = 0;
    private currentProject: string = '';
    private currentLanguage: string = '';
    private currentFile: string = '';

    // Time tracking (per 30-second interval)
    private activeSeconds: number = 0;
    private idleSeconds: number = 0;
    private lastTickTime: number = Date.now();

    // Idle skip counter for toast warnings
    private consecutiveIdleSkips: number = 0;
    private readonly IDLE_WARN_THRESHOLD = 4;   // toast at 4 skips (2 min)
    private readonly IDLE_STOP_THRESHOLD = 12;  // discontinue at 12 skips (6 min)

    private IDLE_TIMEOUT_MS = 15 * 60 * 1000;  // 15 mins
    private HEARTBEAT_INTERVAL_MS = 30 * 1000;  // 30 seconds

    // ── Stress Metrics ───────────────────────────────────────────────
    private stressMetrics = {
        errors: 0,
        repeatedErrors: 0,
        buildRuns: 0,
        buildFailures: 0,
        fileSwitches: 0,
        undoCount: 0,
        terminalErrors: 0,
    };

    // Diagnostics helpers (throttled to avoid per-keystroke overhead)
    private diagnosticsTimer: NodeJS.Timeout | null = null;
    private readonly DIAGNOSTICS_POLL_MS = 5_000;  // 5 seconds
    private previousErrorMessages: Set<string> = new Set();

    // Build-failure-loop detection
    private lastBuildHadErrors: boolean = false;
    private consecutiveBuildFailures: number = 0;

    // Disposable subscriptions created outside the constructor
    private disposables: vscode.Disposable[] = [];

    constructor(private secrets: vscode.SecretStorage) {}

    public async initialize() {
        this.token = await this.secrets.get('aclas.token') || '';
        this.setupListeners();
    }

    public async setToken(token: string) {
        this.token = token;
        await this.secrets.store('aclas.token', token);
    }

    /** Manual stop via command palette */
    public stop() {
        this.isStopped = true;
        this.stopHeartbeatTimer();
        if (this.idleTimer) clearTimeout(this.idleTimer);
        vscode.window.showInformationMessage('ACLAS Tracking is deactivated now.');
        console.log('ACLAS: Tracking manually deactivated.');
    }

    private setupListeners() {
        // ── Existing listeners ────────────────────────────────────────
        vscode.workspace.onDidChangeTextDocument(this.onTextChange, this);
        vscode.window.onDidChangeActiveTextEditor(this.onEditorChange, this);
        vscode.window.onDidChangeTextEditorSelection(this.onActivity, this);

        // ── TASK 1 & 2: Diagnostics & repeated-error tracking ────────
        this.disposables.push(
            vscode.languages.onDidChangeDiagnostics(() => this.scheduleDiagnosticsPoll()),
        );

        // ── TASK 3 & 4: Build / Run & build-failure-loop tracking ────
        this.disposables.push(
            vscode.tasks.onDidStartTask(() => {
                if (this.isStopped) return;
                this.stressMetrics.buildRuns++;
                console.log(`ACLAS: Build/Run detected (total: ${this.stressMetrics.buildRuns})`);
            }),
            vscode.tasks.onDidEndTask(() => {
                if (this.isStopped) return;
                this.checkBuildFailureLoop();
            }),
        );

        // ── TASK 7: Terminal error detection ────────────────────────
        this.disposables.push(
            vscode.window.onDidEndTerminalShellExecution(e => this.onTerminalExecutionEnd(e)),
            vscode.window.onDidStartTerminalShellExecution(e => this.onTerminalExecutionStart(e)),
        );
    }

    private onActivity() {
        if (this.isStopped) return;
        this.isActive = true;
        this.consecutiveIdleSkips = 0;  // reset warn counter on any activity
        this.resetIdleTimer();
        this.startHeartbeatTimer();
        this.updateContext();
    }

    private onEditorChange(editor: vscode.TextEditor | undefined) {
        // ── TASK 5: File-switching counter ────────────────────────────
        if (!this.isStopped && editor) {
            this.stressMetrics.fileSwitches++;
        }
        this.onActivity();
    }

    private onTextChange(e: vscode.TextDocumentChangeEvent) {
        if (e.document.uri.scheme !== 'file') return;
        let added = 0;
        let deleted = 0;
        let hasAnyDeletion = false;
        for (const change of e.contentChanges) {
            const insertedNewlines = (change.text.match(/\n/g) || []).length;
            added += insertedNewlines > 0 ? insertedNewlines : (change.text.trim().length > 0 ? 1 : 0);

            // Count multi-line range deletions (newlines removed)
            const linesInRange = change.range.end.line - change.range.start.line;
            if (linesInRange > 0) {
                // Net lines removed = lines spanned by the old range minus lines in new text
                deleted += linesInRange - insertedNewlines;
            } else if (change.rangeLength > 0 && change.text.length < change.rangeLength) {
                // Same-line deletion: Backspace, Delete, Ctrl+D, etc.
                // Count every such event as 1 deletion unit so heartbeats aren't skipped
                deleted += 1;
                hasAnyDeletion = true;
            }

            // ── TASK 6: Undo heuristic ───────────────────────────────
            // An undo typically replaces text with shorter/empty text in the same range
            if (change.rangeLength > 0 && change.text.length < change.rangeLength) {
                this.stressMetrics.undoCount++;
            }
        }
        this.linesAdded += added;
        this.linesDeleted += deleted;
        this.onActivity();
    }

    private updateContext() {
        const editor = vscode.window.activeTextEditor;
        if (editor && editor.document.uri.scheme === 'file') {
            this.currentLanguage = editor.document.languageId;
            this.currentFile = vscode.workspace.asRelativePath(editor.document.uri);

            // Use the workspace folder name as project (e.g. "my-app"),
            // falling back to the active filename if no workspace is open.
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (workspaceFolders && workspaceFolders.length > 0) {
                this.currentProject = workspaceFolders[0].name;
            } else {
                this.currentProject = editor.document.fileName.split(/[\\/]/).pop() || 'Unknown';
            }
        }
    }

    private resetIdleTimer() {
        if (this.idleTimer) clearTimeout(this.idleTimer);
        this.idleTimer = setTimeout(() => {
            this.isActive = false;
            this.stopHeartbeatTimer();
            console.log('ACLAS: User is idle. Stopped tracking.');
        }, this.IDLE_TIMEOUT_MS);
    }

    private startHeartbeatTimer() {
        if (!this.heartbeatTimer) {
            this.heartbeatTimer = setInterval(() => this.sendEvent(), this.HEARTBEAT_INTERVAL_MS);
        }
    }

    private stopHeartbeatTimer() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }

    private async sendEvent() {
        if (this.isStopped) return;

        // Accumulate time since last tick
        const now = Date.now();
        const elapsedSeconds = Math.round((now - this.lastTickTime) / 1000);
        this.lastTickTime = now;

        if (this.linesAdded > 0 || this.linesDeleted > 0) {
            this.activeSeconds += elapsedSeconds;
        } else {
            this.idleSeconds += elapsedSeconds;
        }

        if (!this.isActive || !this.token || !this.currentProject) return;

        // No keystrokes AND no deletions — handle idle escalation
        // Note: linesDeleted > 0 now also catches same-line backspace/delete activity
        if (this.linesAdded === 0 && this.linesDeleted === 0) {
            this.consecutiveIdleSkips++;
            console.log(`ACLAS: No keystrokes since last tick, skipping heartbeat. (${this.consecutiveIdleSkips})`);

            if (this.consecutiveIdleSkips === this.IDLE_WARN_THRESHOLD) {
                vscode.window.showWarningMessage(
                    "Don't stay idle, let's go, let's start typing!!!"
                );
            }

            if (this.consecutiveIdleSkips >= this.IDLE_STOP_THRESHOLD) {
                // Send a final heartbeat with half the accumulated idle time
                const finalIdleSecs = Math.round(this.idleSeconds / 2);
                const payload = {
                    timestamp: new Date().toISOString(),
                    project_name: this.currentProject,
                    language: this.currentLanguage,
                    file: this.currentFile,
                    lines_added: 0,
                    lines_deleted: 0,
                    active_seconds: 0,
                    idle_seconds: finalIdleSecs,
                };
                await sendHeartbeat(payload, this.token);

                // Discontinue the tracker
                this.stopHeartbeatTimer();
                this.isActive = false;
                this.consecutiveIdleSkips = 0;
                this.idleSeconds = 0;
                vscode.window.showErrorMessage('ACLAS Tracker is discontinued!');
                console.log('ACLAS: Tracker discontinued after prolonged inactivity.');
            }
            return;
        }

        // Reset idle counter on real activity
        this.consecutiveIdleSkips = 0;

        const payload = {
            timestamp: new Date().toISOString(),
            project_name: this.currentProject,
            language: this.currentLanguage,
            file: this.currentFile,
            lines_added: this.linesAdded,
            lines_deleted: this.linesDeleted,
            active_seconds: this.activeSeconds,
            idle_seconds: this.idleSeconds,
            // ── Stress metrics ───────────────────────────────────────
            errors: this.stressMetrics.errors,
            repeated_errors: this.stressMetrics.repeatedErrors,
            build_runs: this.stressMetrics.buildRuns,
            build_failures: this.stressMetrics.buildFailures,
            file_switches: this.stressMetrics.fileSwitches,
            undo_count: this.stressMetrics.undoCount,
            terminal_errors: this.stressMetrics.terminalErrors,
        };

        // Reset all counters
        this.linesAdded = 0;
        this.linesDeleted = 0;
        this.activeSeconds = 0;
        this.idleSeconds = 0;
        this.resetStressMetrics();

        await sendHeartbeat(payload, this.token);
    }

    public dispose() {
        this.stopHeartbeatTimer();
        if (this.idleTimer) clearTimeout(this.idleTimer);
        if (this.diagnosticsTimer) clearTimeout(this.diagnosticsTimer);
        this.disposables.forEach(d => d.dispose());
    }

    // ── Stress-metric helpers ────────────────────────────────────────

    /** Reset per-interval stress counters (called after each heartbeat) */
    private resetStressMetrics() {
        this.stressMetrics.errors = 0;
        this.stressMetrics.repeatedErrors = 0;
        this.stressMetrics.buildRuns = 0;
        this.stressMetrics.buildFailures = 0;
        this.stressMetrics.fileSwitches = 0;
        this.stressMetrics.undoCount = 0;
        this.stressMetrics.terminalErrors = 0;
    }

    // ── TASK 1 & 2: Diagnostics (throttled to 5 s) ──────────────────

    /** Schedule a diagnostics poll; coalesces rapid-fire events */
    private scheduleDiagnosticsPoll() {
        if (this.isStopped || this.diagnosticsTimer) return;
        this.diagnosticsTimer = setTimeout(() => {
            this.diagnosticsTimer = null;
            this.pollDiagnostics();
        }, this.DIAGNOSTICS_POLL_MS);
    }

    /** Count current errors & detect repeated error messages */
    private pollDiagnostics() {
        const allDiagnostics = vscode.languages.getDiagnostics();
        const currentMessages = new Set<string>();
        let errorCount = 0;

        for (const [, diagnostics] of allDiagnostics) {
            for (const d of diagnostics) {
                if (d.severity === vscode.DiagnosticSeverity.Error) {
                    errorCount++;
                    const msg = d.message;
                    currentMessages.add(msg);

                    // TASK 2: repeated error — same message seen in previous poll
                    if (this.previousErrorMessages.has(msg)) {
                        this.stressMetrics.repeatedErrors++;
                    }
                }
            }
        }

        this.stressMetrics.errors = errorCount;
        this.previousErrorMessages = currentMessages;
    }

    // ── TASK 4: Build-failure-loop detection ─────────────────────────

    /** Called after a task ends; checks if errors are present → failure loop */
    private checkBuildFailureLoop() {
        const allDiagnostics = vscode.languages.getDiagnostics();
        let hasErrors = false;

        for (const [, diagnostics] of allDiagnostics) {
            if (diagnostics.some(d => d.severity === vscode.DiagnosticSeverity.Error)) {
                hasErrors = true;
                break;
            }
        }

        if (hasErrors) {
            this.consecutiveBuildFailures++;
            this.stressMetrics.buildFailures++;
            console.log(`ACLAS: Build ended with errors (consecutive: ${this.consecutiveBuildFailures})`);

            if (this.consecutiveBuildFailures >= 3) {
                vscode.window.showWarningMessage(
                    `ACLAS: You've had ${this.consecutiveBuildFailures} consecutive build failures. Consider taking a break!`,
                );
            }
        } else {
            this.consecutiveBuildFailures = 0;
        }

        this.lastBuildHadErrors = hasErrors;
    }

    // ── TASK 7: Terminal error detection ─────────────────────────────

    private static readonly TERMINAL_ERROR_PATTERN = /\b(error|failed|exception|fatal|traceback)\b/i;

    /** Non-zero exit code → terminal error */
    private onTerminalExecutionEnd(e: vscode.TerminalShellExecutionEndEvent) {
        if (this.isStopped) return;
        if (e.exitCode !== undefined && e.exitCode !== 0) {
            this.stressMetrics.terminalErrors++;
            console.log(`ACLAS: Terminal command failed with exit code ${e.exitCode} (total: ${this.stressMetrics.terminalErrors})`);
        }
    }

    /** Scan terminal output stream for error keywords */
    private async onTerminalExecutionStart(e: vscode.TerminalShellExecutionStartEvent) {
        if (this.isStopped) return;
        try {
            for await (const data of e.execution.read()) {
                if (AclasTracker.TERMINAL_ERROR_PATTERN.test(data)) {
                    this.stressMetrics.terminalErrors++;
                    console.log(`ACLAS: Terminal error keyword detected (total: ${this.stressMetrics.terminalErrors})`);
                    break;  // count once per command execution, not per line
                }
            }
        } catch {
            // Stream may be closed before fully read – safe to ignore
        }
    }
}
