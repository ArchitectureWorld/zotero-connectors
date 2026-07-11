# Zotero Connector Script Trigger Review

Date: 2026-07-11  
Branch: `feature/script-trigger`

## Verdict

The fork keeps Zotero's official save implementation and adds a narrowly scoped local command transport. Protocol v2 is suitable for agent integration because it can target one exact browser tab by URL without focusing Chrome or simulating input.

The feature remains a trigger, not a persistence API. Stable consumers must independently verify the resulting Zotero item and attachments.

## Architecture reviewed

```text
Agent / CLI
  -> authenticated per-user Windows named pipe
  -> packaged native messaging host
  -> Chrome Native Messaging
  -> MV3 extension service worker
  -> exact tab resolution and readiness checks
  -> Zotero.Connector_Browser.onZoteroButtonElementClick(tab)
  -> official translator / PDF / snapshot / selection behavior
```

## Findings and resolutions

| Finding | Severity | Resolution |
| --- | --- | --- |
| Active-tab-only targeting could save the wrong page in an agent workflow. | High | Added protocol v2 `save-url --url`, `save-tab`, `list-tabs`, and fail-closed matching. |
| URL/title substring matching could be ambiguous. | High | Zero matches return `TAB_NOT_FOUND`; multiple matches return `TAB_AMBIGUOUS`. |
| A discarded/loading background tab could be saved before page readiness. | High | Reload discarded tabs without activation and wait for bounded page completion. |
| Triggering before translator detection could create an incorrect webpage item. | High | Wait for translator detection; `TRANSLATOR_TIMEOUT` fails before the official save call. |
| A background reload could redirect an exact target to another page. | High | Recheck the full URL immediately before saving; `TARGET_CHANGED` fails without triggering. |
| A successful trigger could be mistaken for completed persistence. | High | Documentation and response contract explicitly separate `triggered=true` from Zotero completion. |
| Windows PowerShell 5.1 misread UTF-8 scripts without BOM. | High | Packaging rewrites helper scripts as UTF-8 with BOM and parses every script using Windows PowerShell 5.1. |
| Chrome launcher treated a single path as a scalar and indexed its first character. | Medium | Launcher now selects the first full path with `Select-Object -First 1`; regression coverage was added. |
| Rebuilt unpacked extensions could receive changing IDs. | Medium | Package uses a fixed development public key and verifies the expected extension ID during CI. |
| Source and packaged CLI capability drift was possible. | Medium | CI runs source tests, builds both EXEs, and verifies packaged CLI help includes protocol-v2 commands. |

## Official behavior preservation

The added module does not implement translators, item extraction, attachment downloading, snapshots, multiple-item selection, collection selection, or Zotero communication. The final call remains:

```javascript
Zotero.Connector_Browser.onZoteroButtonElementClick(tab)
```

This preserves the existing toolbar-button path and its official fallback behavior. Readiness checks happen before that call and never replace Zotero's save implementation.

## Focus and security audit

The new trigger path contains no calls that:

- focus a browser window;
- activate a browser tab;
- invoke `SetForegroundWindow`;
- invoke `SendInput`;
- synthesize keyboard or mouse events;
- expose a local TCP port.

Reloading a discarded tab uses the browser tab reload API without activation. The native host is allowlisted to the packaged extension ID. Pipe clients authenticate with a randomly generated per-user key stored under `%LOCALAPPDATA%\ZoteroScriptTrigger`.

## Protocol v2 acceptance contract

A compatible `ping` must return:

```json
{
  "success": true,
  "protocolVersion": 2,
  "capabilities": ["list-tabs", "save-url"]
}
```

A deterministic save must use:

```powershell
zotero_script_trigger_cli.exe save-url --url "<exact URL>"
```

A successful response includes `triggered=true`, `translatorReady=true`, and the exact requested URL. The consumer must still verify Zotero persistence separately.

## Test coverage

Automated coverage includes:

- native messaging framing and malformed data;
- CLI command/request construction;
- protocol identity and capability discovery;
- HTTP(S)-only tab listing;
- exact tab ID and exact URL selection;
- ambiguous-selector rejection;
- discarded-tab background reload and page readiness;
- translator-readiness success and timeout rejection;
- target URL change rejection after reload;
- official save-entrypoint invocation;
- absence of focus/activation calls in the command path;
- Windows PowerShell 5.1 parsing;
- stable extension ID verification;
- Windows EXE/package assembly and packaged command discovery.

## Manual evidence

The user successfully installed and exercised the earlier packaged build in Windows Chrome with Zotero, including foreground/background operation. Protocol-v2 exact-URL targeting and the later readiness checks require one final V3 package check on the user's machine before the PR should leave draft state.

## Known limits

- The packaged host currently targets Windows.
- One enabled Chrome/Edge profile instance should own the per-user pipe.
- The browser process must be running.
- Multiple-item pages may still require the official Zotero selector UI.
- `triggered=true` is not final persistence evidence.

## Merge recommendation

Keep PR #1 as draft until:

1. all CI and package workflows pass;
2. the V3 package reports protocol v2 with `save-url`;
3. one exact CNKI detail URL is triggered and independently verified in Zotero with expected metadata and PDF.
