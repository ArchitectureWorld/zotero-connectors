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

Successful acceptance:

```json
{
  "success": true,
  "action": "save-url",
  "triggered": true,
  "tabId": 123,
  "windowId": 9,
  "title": "Article title",
  "url": "<exact HTTP(S) URL>"
}
```

The caller must require:

1. `success === true`;
2. `triggered === true`;
3. returned `url` exactly equals the requested URL.

A mismatch is a target-selection failure, even when `success` is true.

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
| `TAB_NOT_FOUND` | No saveable tab matched. |
| `TAB_AMBIGUOUS` | More than one tab matched. |
| `UNSUPPORTED_URL` | Target is not HTTP(S). |
| `INTERNAL_ERROR` | Unexpected extension failure. |

CLI/transport errors may additionally include `CLI_NOT_INSTALLED`, connection errors, timeout errors, or malformed response errors in the caller's wrapper.

## Completion verification

A trigger response is only phase one. A stable importer must:

1. snapshot matching Zotero item keys before triggering;
2. skip a pre-existing item that already has matching metadata and a PDF;
3. trigger the exact URL;
4. poll Zotero until metadata and attachments settle;
5. continue polling when metadata appears before its PDF child;
6. return `metadata_only` only after the deadline;
7. never create a duplicate complete item.

## Security and focus behavior

- Communication is local: authenticated Windows named pipe plus Chrome Native Messaging.
- The host manifest allowlists the packaged extension ID.
- No local TCP listener is opened.
- The extension does not call browser focus/activation APIs.
- The native host does not synthesize keyboard or mouse input.
- URL/title substring matching fails closed when ambiguous.

## Known limits

- Windows only for the packaged native host and CLI.
- One enabled Chrome/Edge profile instance per Windows user in the current package.
- Browser must be running.
- Multi-item translator pages may display the official selection UI.
- The Connector action may return before Zotero persistence completes.
