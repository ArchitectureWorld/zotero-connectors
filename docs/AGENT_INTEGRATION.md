# Agent integration contract

## Scope

The script trigger is a local transport into the existing Zotero Connector save workflow. Ordinary requests call the official toolbar-button entrypoint. Collection-targeted requests resolve an existing Zotero Desktop collection, complete the normal page save, and then use the existing `updateSession` message for that same save session.

The integration does not create collections and does not replace Zotero persistence verification.

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

Collection-aware integrations must require:

```json
{
  "success": true,
  "protocolVersion": 3,
  "capabilities": ["list-tabs", "save-url", "save-to-collection"]
}
```

Reject the collection integration when:

- the executable is missing;
- the named pipe is unavailable;
- `success` is not true;
- `protocolVersion` is below 3;
- `save-url` or `save-to-collection` is absent.

Consumers that do not use collection targeting may continue to accept the older ordinary-save capability contract.

## Deterministic collection save

Preferred command:

```powershell
zotero_script_trigger_cli.exe save-url `
  --url "<exact HTTP(S) URL>" `
  --collection "<full collection path>" `
  --library-target "L1"
```

`--library-target` is optional and defaults to `L1`. `--collection` starts at the first collection below the selected library root; do not include “My Library” in the path.

Before saving, the extension:

1. resolves exactly one matching browser tab;
2. reloads it in the background when Chrome marked it discarded;
3. waits for page completion;
4. waits for Zotero translator detection;
5. confirms an exact requested URL did not change during reload;
6. requests Zotero Desktop’s editable collection tree;
7. resolves one exact full-path match in the selected library;
8. fails before saving when the target is missing, invalid, or unsupported.

After resolution, the extension completes the normal Connector page save and sends the existing `updateSession` message to the same page save session.

Successful response:

```json
{
  "success": true,
  "action": "save-url",
  "triggered": true,
  "translatorReady": true,
  "tabId": 123,
  "windowId": 9,
  "title": "Article title",
  "url": "<exact HTTP(S) URL>",
  "collectionApplied": true,
  "collectionTarget": {
    "id": "C128",
    "name": "第一轮广义收集",
    "path": "自动文献收集/建筑数字化技术/第一轮广义收集",
    "libraryTarget": "L1",
    "filesEditable": true
  }
}
```

The caller must require:

1. `success === true`;
2. `triggered === true`;
3. `translatorReady === true`;
4. returned `url` exactly equals the requested URL;
5. `collectionApplied === true`;
6. `collectionTarget.path` exactly equals the requested normalized path;
7. `collectionTarget.libraryTarget` equals the requested or default library target.

A mismatch is a target-selection failure even when the transport command completed.

## Ordinary deterministic save

Without `--collection`, the current behavior remains:

```powershell
zotero_script_trigger_cli.exe save-url --url "<exact HTTP(S) URL>"
```

For this form, `triggered=true` means the official Connector action accepted the command. The caller must independently verify persistence.

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
    "code": "TARGET_COLLECTION_NOT_FOUND",
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
| `INVALID_COLLECTION_PATH` | Blank path or an empty `/` path segment. |
| `INVALID_LIBRARY_TARGET` | Library target is not a tree ID such as `L1`. |
| `COLLECTION_PATH_REQUIRED` | A library target was supplied without a collection path. |
| `TARGET_COLLECTION_NOT_FOUND` | No exact collection-path match was found. |
| `TARGET_COLLECTION_AMBIGUOUS` | More than one exact path match was found. |
| `COLLECTION_LOOKUP_UNAVAILABLE` | Zotero Desktop collection lookup is unavailable. |
| `COLLECTION_UPDATE_UNAVAILABLE` | Connector save-session messaging is unavailable. |
| `COLLECTION_TARGET_UNSUPPORTED` | The target page cannot provide an injected Connector save session. |
| `SAVE_NOT_CONFIRMED` | Translator saving did not return saved items. |
| `INTERNAL_ERROR` | Unexpected extension failure. |

CLI/transport errors may additionally include connection errors, timeout errors, or malformed response errors in the caller’s wrapper.

## Completion verification

A collection-aware importer must:

1. snapshot matching Zotero item keys before triggering;
2. stop rather than create a duplicate when attachment state cannot be checked reliably;
3. skip a pre-existing item that already has matching metadata and the required attachment;
4. trigger the exact URL and collection path;
5. require the collection-aware response contract above;
6. poll Zotero until metadata, collection membership, and attachments settle;
7. continue polling when metadata appears before its child attachment;
8. return `metadata_only` only after the deadline;
9. never create a duplicate complete item.

## Security and focus behavior

- Communication is local: authenticated Windows named pipe plus Chrome Native Messaging.
- The host manifest allowlists the packaged extension ID.
- No local TCP listener is opened.
- The extension does not call browser focus/activation APIs.
- Reloading a discarded tab does not activate or focus it.
- The native host does not synthesize keyboard or mouse input.
- URL/title substring matching and collection matching fail closed when ambiguous.

## Known limits

- Windows only for the packaged native host and CLI.
- One enabled Chrome/Edge profile instance per Windows user in the current package.
- Browser and Zotero Desktop must be running.
- The target collection must already exist.
- Collection names containing `/` cannot be represented by the current path syntax.
- Multi-item translator pages may display the official selection UI.
- Final metadata, collection membership, and attachment state should still be verified from Zotero.