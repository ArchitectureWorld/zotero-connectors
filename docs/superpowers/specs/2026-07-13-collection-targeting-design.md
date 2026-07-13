# Collection-Targeted Script Saves Design

## Goal

Allow the external script-trigger interface to save a page through the existing Zotero Connector workflow and then place the resulting item directly into an existing Zotero collection selected by full collection path.

## Scope

- The collection is created manually in Zotero Desktop.
- Automation supplies `collectionPath` and optionally `libraryTarget`.
- The Connector resolves the path through Zotero Desktop's existing `getSelectedCollection` response.
- A missing, invalid, ambiguous, or unsupported target fails closed before the item is saved.
- Existing save commands without collection options retain their current behavior.
- This first version does not create collections and does not use the Zotero Web API.
- Windows deployment must remain one-click for the end user.

## Request Contract

Every save action may include:

```json
{
  "collectionPath": "自动文献收集/建筑数字化技术/第一轮广义收集",
  "libraryTarget": "L1"
}
```

`libraryTarget` defaults to `L1`. `/` is the path separator, so empty path segments are invalid.

## Save Architecture

1. The CLI adds `--collection` and `--library-target` to all save commands.
2. The browser extension asks Zotero Desktop for the editable collection tree using `getSelectedCollection`.
3. It reconstructs full collection paths from the returned flattened `level` sequence.
4. For collection-targeted requests, it invokes the existing `saveWithTranslator` or `saveAsWebpage` Connector entrypoint and waits for that page save to finish.
5. It sends the existing `updateSession` message to the translating page. `Zotero.PageSaving.onUpdateSession()` then calls Zotero Desktop's existing `/connector/updateSession` endpoint for the current save session.
6. The response reports the resolved target and whether the collection update was applied.

## One-click Deployment Architecture

The release package must expose one normal entrypoint:

```text
0-一键安装并启动.bat
```

That entrypoint must complete the following without requiring the user to open Chrome extension settings:

1. Install the packaged native host and CLI into `%LOCALAPPDATA%\ZoteroScriptTrigger`.
2. Register Native Messaging for the current Windows user.
3. Copy the extension to a stable installed path.
4. Copy a bundled Chrome for Testing runtime to a stable installed path.
5. Create a persistent dedicated browser profile.
6. Create Desktop and Start Menu launch shortcuts.
7. Start the bundled browser with the installed extension.
8. Poll `ping` until protocol version 3 and capability `save-to-collection` are confirmed.
9. Exit non-zero and preserve a visible error when any stage fails.

Reinstallation must stop only the dedicated bundled browser, generate a fresh local pipe identifier, replace installed files, restart the browser, and rerun verification. It must not terminate or modify the user's normal Chrome process or profile.

## Failure Rules

- `INVALID_COLLECTION_PATH`: blank path or empty path segment.
- `INVALID_LIBRARY_TARGET`: target is not a Zotero library tree ID such as `L1`.
- `TARGET_COLLECTION_NOT_FOUND`: no exact full-path match.
- `TARGET_COLLECTION_AMBIGUOUS`: more than one exact match.
- `COLLECTION_TARGET_UNSUPPORTED`: the page cannot provide an injected Connector save session.
- `SAVE_NOT_CONFIRMED`: translator save did not return saved items.

No collection-related error may silently fall back to My Library.

## Compatibility

- Protocol version increases from 2 to 3.
- `ping` advertises `save-to-collection`.
- Native-host framing and named-pipe transport remain unchanged.
- Existing requests that omit `collectionPath` remain compatible.
- The old multi-step installer remains available only as a diagnostic fallback.

## Verification

- Node tests cover full-path resolution, successful session update, missing targets, invalid paths, and unsupported pages.
- Python tests cover CLI argument parsing and JSON request generation.
- PowerShell regression tests cover the one-click installer contract and Windows PowerShell 5.1 parsing.
- GitHub Actions must build a Windows ZIP that includes the extension, native executables, bundled browser runtime, one-click installer, launcher, and uninstall path.
- The existing script-trigger regression suites must remain green.