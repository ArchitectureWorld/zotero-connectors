# Zotero Connector External Script Trigger Design

## Goal

Add a script-callable trigger to the official Zotero Connector fork while preserving all existing Zotero Connector behavior. The browser may be foreground, background, covered, or minimized; no focus or keyboard/mouse simulation is allowed.

## Scope

V1 supports Windows with Chromium Manifest V3 builds (Chrome and Edge) and keeps Firefox/MV2 build compatibility. Commands are `ping`, `save-active`, and `save-tab`. Saving uses `Zotero.Connector_Browser.onZoteroButtonElementClick(tab)` so translators, PDF handling, snapshots, selection UI, and fallback behavior remain official.

## Architecture

1. `scriptTrigger.js` runs in the extension background context and maintains a `runtime.connectNative()` port to `org.zotero.script_trigger`.
2. A packaged Python native host is launched by the browser and exposes a per-user Windows named pipe.
3. The Python CLI connects to the named pipe, sends a JSON command, and receives a structured response.
4. The extension resolves the requested tab without activating or focusing it and invokes the official Zotero save action.

## Behavioral Contract

- `save-active` selects the active tab in the browser's last-focused browser window using `tabs.query({active: true, lastFocusedWindow: true})`.
- `save-tab` uses the exact `tabId` and does not activate it.
- Only `http:` and `https:` tabs are accepted.
- Responses report `triggered: true`, not confirmed persistence, because the official save action may continue asynchronously or require item selection.
- No calls to `windows.update({focused: true})`, `tabs.update({active: true})`, Win32 focus APIs, keyboard automation, or mouse automation are introduced.

## Error Handling

Errors are returned as `{success:false,id,error:{code,message}}`. Native-host disconnects use bounded exponential reconnect. CLI timeouts and missing browser/host conditions return non-zero exit codes.

## Testing

- Node built-in tests cover command validation, active-tab selection, explicit-tab selection, official-action invocation, and no-focus semantics.
- Python unittest covers native-message framing, request creation, configuration parsing, and malformed data.
- JSON manifests and Python/JavaScript syntax are validated.
- Manual verification confirms foreground, background, covered, minimized, exact-tab, and official-button regression scenarios.
