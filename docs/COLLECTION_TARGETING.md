# Collection-targeted saves

Protocol v3 can place a script-triggered save directly into an existing Zotero Desktop collection.

## Preconditions

1. Zotero Desktop is running.
2. The target collection already exists.
3. The page supports an injected Zotero Connector save session.
4. The browser extension and native host are installed from the same build.

The feature does not create collections and does not use the Zotero Web API.

## CLI example

```powershell
zotero_script_trigger_cli.exe save-url `
  --url "https://example.org/paper" `
  --collection "自动文献收集/建筑数字化技术/第一轮广义收集"
```

`--library-target` defaults to `L1`, which is normally My Library:

```powershell
zotero_script_trigger_cli.exe save-url `
  --url "https://example.org/paper" `
  --collection "项目A/第一轮收集" `
  --library-target "L1"
```

The same collection options are available on `save-active`, `save-tab`, `save-url`, and `save-title`.

## Native request

```json
{
  "id": "request-123",
  "action": "save-url",
  "url": "https://example.org/paper",
  "collectionPath": "自动文献收集/建筑数字化技术/第一轮广义收集",
  "libraryTarget": "L1"
}
```

Collection paths are exact and case-sensitive. `/` separates nesting levels. Empty path segments are rejected.

## Success response

```json
{
  "id": "request-123",
  "success": true,
  "action": "save-url",
  "triggered": true,
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

`collectionApplied=true` means the Connector completed the page save and sent the existing `updateSession` command for that save session.

## Failure behavior

Collection targeting never silently falls back to My Library.

| Code | Meaning |
|---|---|
| `INVALID_COLLECTION_PATH` | The path is blank or contains an empty segment. |
| `INVALID_LIBRARY_TARGET` | The library target is not a tree ID such as `L1`. |
| `TARGET_COLLECTION_NOT_FOUND` | No exact full-path match was found. |
| `TARGET_COLLECTION_AMBIGUOUS` | More than one exact match was found. |
| `COLLECTION_LOOKUP_UNAVAILABLE` | Zotero Desktop collection lookup is unavailable. |
| `COLLECTION_TARGET_UNSUPPORTED` | The page cannot provide an injected save session. |
| `SAVE_NOT_CONFIRMED` | Translator saving did not return saved items. |

## Data model note

The saved item still belongs to My Library at the database level. The operation assigns the item to the requested Zotero collection immediately after the normal Connector save completes, so it does not remain unclassified.