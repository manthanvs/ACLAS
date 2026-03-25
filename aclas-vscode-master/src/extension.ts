import * as vscode from "vscode";
import { AclasTracker } from "./tracker";

let tracker: AclasTracker;

export async function activate(context: vscode.ExtensionContext) {
	console.log("ACLAS Tracker is now active!");

	tracker = new AclasTracker(context.secrets);
	await tracker.initialize();

	// Command: Enter API Token
	const tokenCmd = vscode.commands.registerCommand(
		"aclas.getToken",
		async () => {
			const token = await vscode.window.showInputBox({
				prompt: "Enter your ACLAS API Token from your Django Dashboard",
				password: true,
			});
			if (token) {
				await tracker.setToken(token);
				vscode.window.showInformationMessage(
					"ACLAS Token Saved Successfully!",
				);
			}
		},
	);

	// Command: Stop ACLAS Tracking
	const stopCmd = vscode.commands.registerCommand(
		"aclas.stopTracking",
		() => {
			tracker.stop();
		},
	);

	context.subscriptions.push(tokenCmd, stopCmd);
}

export function deactivate() {
	if (tracker) {
		tracker.dispose();
	}
}
