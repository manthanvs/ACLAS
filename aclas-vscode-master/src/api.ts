import * as vscode from 'vscode';

/** Returns true when the server accepted the heartbeat. */
export async function sendHeartbeat(payload: unknown, token: string): Promise<boolean> {
    const endpoint = vscode.workspace.getConfiguration('aclas')
        .get<string>('serverEntrypoint', 'http://localhost:8000/api/heartbeats/');
    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Authorization': `Token ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: AbortSignal.timeout(5000),
        });
        if (!res.ok) { console.error(`ACLAS: heartbeat rejected (${res.status})`); }
        return res.ok;
    } catch (e: any) {
        console.error("ACLAS: Failed to send heartbeat", e.message);
        return false;
    }
}
