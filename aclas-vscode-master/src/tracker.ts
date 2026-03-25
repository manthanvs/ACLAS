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
        vscode.workspace.onDidChangeTextDocument(this.onTextChange, this);
        vscode.window.onDidChangeActiveTextEditor(this.onEditorChange, this);
        vscode.window.onDidChangeTextEditorSelection(this.onActivity, this);
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
        this.onActivity();
    }

    private onTextChange(e: vscode.TextDocumentChangeEvent) {
        if (e.document.uri.scheme !== 'file') return;
        let added = 0;
        let deleted = 0;
        for (const change of e.contentChanges) {
            const lines = (change.text.match(/\n/g) || []).length;
            added += lines > 0 ? lines : (change.text.trim().length > 0 ? 1 : 0);
            deleted += change.range.end.line - change.range.start.line;
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
            const fileName = editor.document.fileName.split(/[\\/]/).pop() || 'Unknown';
            this.currentProject = fileName;
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

        // No keystrokes — handle idle escalation
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
        };

        // Reset all counters
        this.linesAdded = 0;
        this.linesDeleted = 0;
        this.activeSeconds = 0;
        this.idleSeconds = 0;

        await sendHeartbeat(payload, this.token);
    }

    public dispose() {
        this.stopHeartbeatTimer();
        if (this.idleTimer) clearTimeout(this.idleTimer);
    }
}
