import got from 'got';
import * as vscode from 'vscode';

export async function sendHeartbeat(payload: any, token: string) {
    const config = vscode.workspace.getConfiguration('aclas');
    const endpoint = config.get<string>('serverEntrypoint', 'http://localhost:8000/api/heartbeats/');
    
    try {
        await got.post(endpoint, {
            json: payload,
            headers: {
                'Authorization': `Token ${token}`
            },
            timeout: {
                request: 5000
            }
        });
        console.log("ACLAS: Heartbeat sent successfully");
    } catch (e: any) {
        console.error("ACLAS: Failed to send heartbeat", e.message);
    }
}
