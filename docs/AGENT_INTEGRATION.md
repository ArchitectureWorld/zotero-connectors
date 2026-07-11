# Agent integration contract

## Scope

The script trigger is a local transport into the official Zotero Connector save action. It selects a Chrome/Edge tab and calls `Zotero.Connector_Browser.onZoteroButtonElementClick(tab)`.

It does **not** confirm that Zotero finished writing an item. Consumers must verify persistence separately.

## Installed executable

```text
%LOCALAPPDATA%\ZoteroScriptTrigger\zotero_script_trigger_cli.exe
```

Override for companion programs:

```text
ZOTERO_SCRIPT_TRIGGER_CLI=<absolute executable path>
```

## Compatibility check

Command:

```powershell
zotero_script_trigger_cli.exe ping
```

Required fields:

```json
{
  "success": true,
  "protocolVersion": 2,
  "capabilities": ["list-tabs", "save-url"]
}
```

Reject the integration when:

- the executable is missing;
- the named pipe is unavailable;
- `success` is not true;
- `protocolVersion` is below 2;
- `save-url` is absent.

## Deterministic save

Preferred command:

```powershell
zotero_script_trigger_cli.exe save-url --url "<exact HTTP(S) URL>"
```

Before the official save action, the extension:

1. resolves exactly one matching tab;
2. reloads it in the background when Chrome marked it discarded;
3. waits for page completion;
4. waits for Zotero translator detection;
5. confirms an exact requested URL did not change during reload.

Successful acceptance:

```json
{
  "success": true,
  "action": "save-url",
  "triggered": true,
  "translatorReady": true,
  "tabId": 123,
  "windowId": 9,
  "title": "Article title",
  "url": "<exact HTTP(S) URL>"
}
```

The caller must require:

1. `success === true`;
2. `triggered === true`;
3. `translatorReady === true`;
4. returned `url` exactly equals the requested URL.

A mismatch is a target-selection failure even when a transport command completed.

## Tab discovery

```powershell
zotero_script_trigger_cli.exe list-tabs
```

The response contains saveable HTTP(S) tabs only:

```json
{
  "success": true,
  "action": "list-tabs",
  "tabs": [
    {
      "id": 123,
      "windowId": 9,
      "active": false,
      "discarded": false,
      "status": "complete",
      "title": "Article title",
      "url": "https://example.org/article"
    }
  ]
}
```

Use this for diagnostics. Production automation should pass an exact URL obtained from the browser session.

## Error model

Extension errors use:

```json
{
  "success": false,
  "action": "save-url",
  "error": {
    "code": "TAB_NOT_FOUND",
    "message": "..."
  }
}
```

Stable codes:

| Code | Meaning |
| --- | --- |
| `UNKNOWN_ACTION` | Unsupported protocol action. |
| `INVALID_TAB_ID` | Missing or invalid exact tab ID. |
| `INVALID_URL_SELECTOR` | `save-url` received zero or two selectors. |
| `INVALID_TITLE_SELECTOR` | Empty title fragment. |
| `TAB_NOT_FOUND` | No saveable tab matched or the tab disappeared. |
| `TAB_AMBIGUOUS` | More than one tab matched. |
| `UNSUPPORTED_URL` | Target is not HTTP(S). |
| `TAB_RELOAD_UNAVAILABLE` | A discarded tab could not be reloaded. |
| `TAB_LOAD_TIMEOUT` | The tab did not finish loading within the bounded wait. |
| `TRANSLATOR_TIMEOUT` | Zotero translator detection never settled; no save was triggered. |
| `TARGET_CHANGED` | An exact target URL changed during background reload; no save was triggered. |
| `INTERNAL_ERROR` | Unexpected extension failure. |

CLI/transport errors may additionally include `CLI_NOT_INSTALLED`, connection errors, timeout errors, or malformed response errors in the caller's wrapper.

## Completion verification

A trigger response is only phase one. A stable importer must:

1. snapshot matching Zotero item keys before triggering;
2. stop rather than create a duplicate when attachment state cannot be checked reliably;
3. skip a pre-existing item that already has matching metadata and a PDF;
4. trigger the exact URL;
5. poll Zotero until metadata and attachments settle;
6. continue polling when metadata appears before its PDF child;
7. return `metadata_only` only after the deadline;
8. never create a duplicate complete item.

## Security and focus behavior

- Communication is local: authenticated Windows named pipe plus Chrome Native Messaging.
- The host manifest allowlists the packaged extension ID.
- No local TCP listener is opened.
- The extension does not call browser focus/activation APIs.
- Reloading a discarded tab does not activate or focus it.
- The native host does not synthesize keyboard or mouse input.
- URL/title substring matching fails closed when ambiguous.

## Known limits

- Windows only for the packaged native host and CLI.
- One enabled Chrome/Edge profile instance per Windows user in the current package.
- Browser must be running.
- Multi-item translator pages may display the official selection UI.
- The Connector action may return before Zotero persistence completes.
