# Zotero Connector Script Trigger

This fork adds a Windows-local command interface that invokes the existing Zotero Connector save workflow. It does not reimplement translators, snapshots, PDF handling, item selection, or Zotero persistence.

## Behavior

- Chrome may be foreground, covered, background, or minimized.
- No browser window or tab is focused or activated by the trigger.
- Exact background targeting is supported by tab ID or exact URL.
- URL/title substring targeting fails when multiple tabs match.
- Save commands may target an existing Zotero collection by exact full path.
- A missing or invalid collection fails closed; it never silently falls back to My Library.
- Browser completely closed is not supported; the CLI returns a connection error.
- Multiple-item pages still use the official Zotero item selector.

For ordinary saves, `"triggered": true` means the official Connector action accepted the command. Saving may continue asynchronously, so callers must verify Zotero persistence separately.

For collection-targeted saves, `"collectionApplied": true` means the page save completed and the existing Zotero save session received the target-collection update. Callers should still verify the final Zotero item and attachment state.

## One-click Windows package

The normal end-user installation path is:

```text
0-一键安装并启动.bat
```

The package includes:

```text
浏览器插件/
browser/chrome-win64/
app/zotero_script_trigger_host.exe
app/zotero_script_trigger_cli.exe
0-一键安装并启动.bat
1-安装本地助手.bat
2-加载浏览器插件.bat
3-测试连接.bat
4-保存当前网页.bat
5-卸载.bat
```

The one-click installer:

1. installs the native host and CLI under `%LOCALAPPDATA%\ZoteroScriptTrigger`;
2. copies the extension and bundled automation browser into the installed directory;
3. creates a persistent dedicated browser profile;
4. creates Desktop and Start Menu shortcuts;
5. launches the automation browser with the extension already loaded;
6. waits for protocol version 3 and capability `save-to-collection` before reporting success.

The user does not open `chrome://extensions` and does not manually select the extension folder. The old numbered installation steps remain only as a diagnostic fallback.

The installed CLI is:

```text
%LOCALAPPDATA%\ZoteroScriptTrigger\zotero_script_trigger_cli.exe
```

The dedicated browser profile is:

```text
%LOCALAPPDATA%\ZoteroScriptTrigger\browser-profile
```

Website login state persists in that profile. See `docs/ONE_CLICK_DEPLOYMENT.md` for the full deployment and uninstall contract.

## Protocol v3

Run:

```powershell
$cli = "$env:LOCALAPPDATA\ZoteroScriptTrigger\zotero_script_trigger_cli.exe"
& $cli ping
```

A compatible response includes:

```json
{
  "success": true,
  "protocolVersion": 3,
  "capabilities": [
    "list-tabs",
    "save-active",
    "save-tab",
    "save-url",
    "save-title",
    "save-to-collection"
  ]
}
```

Agent integrations that need collection targeting must require protocol version 3 plus capabilities `save-url` and `save-to-collection`.

## Commands

```powershell
& $cli ping
& $cli list-tabs
& $cli save-active
& $cli save-tab --tab-id 123
& $cli save-url --url "https://exact.example/article"
& $cli save-url --contains "detail?id=123"
& $cli save-title --contains "论文标题"
```

Target selection rules:

- `save-tab` selects one exact tab ID.
- `save-url --url` requires an exact URL match.
- `save-url --contains` and `save-title --contains` require exactly one match.
- Zero matches return `TAB_NOT_FOUND`.
- Multiple matches return `TAB_AMBIGUOUS`.
- Browser-internal and non-HTTP(S) pages return `UNSUPPORTED_URL`.

For deterministic automation, prefer an exact URL obtained from the browser session. Do not use `save-active` when the target must be unambiguous.

## Save to an existing collection

Create the collection manually in Zotero Desktop, then pass its path relative to the library root:

```powershell
& $cli save-url `
  --url "https://exact.example/article" `
  --collection "自动文献收集/建筑数字化技术/第一轮广义收集"
```

The default library target is `L1` (normally My Library). To specify it explicitly:

```powershell
& $cli save-url `
  --url "https://exact.example/article" `
  --collection "项目A/第一轮收集" `
  --library-target "L1"
```

Collection paths are exact and case-sensitive. `/` separates collection levels. This version does not create collections automatically.

See `docs/COLLECTION_TARGETING.md` for the JSON contract, response fields, and stable collection error codes.

## Source build

Use Git Bash or WSL from the repository root:

```bash
git submodule update --init --recursive
npm install
./build.sh -p b -d
```

Load `build/manifestv3` as an unpacked extension in Chrome or Edge only for development. End users should use the one-click package.

For source installation of the native host:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-script-trigger.ps1 -ExtensionId YOUR_EXTENSION_ID -Browser Chrome
```

The current package supports one enabled automation-browser profile instance per Windows user because the native host owns one per-install authenticated named pipe.

## Agent integration sequence

1. Run `ping`; require protocol v3 plus `save-url` and `save-to-collection` when collection targeting is needed.
2. Obtain the exact URL of the already-open target page.
3. Run `save-url --url <exact-url> --collection <full-path>`.
4. Require the returned URL to equal the requested URL.
5. Require `collectionApplied === true` and verify the returned collection path.
6. Independently poll Zotero for the expected metadata, collection membership, and attachments.

See `docs/AGENT_INTEGRATION.md` for the machine contract.

## Troubleshooting

### One-click self-test did not pass

Keep the installer window open and record its last returned error. Confirm Zotero Desktop is installed, then rerun `0-一键安装并启动.bat`. Reinstallation is supported and only closes the dedicated bundled browser.

### Native host not found or forbidden

Reload the dedicated automation browser after installation and confirm the extension ID matches the host manifest. Registry locations:

```text
HKCU\Software\Google\Chrome\NativeMessagingHosts\org.zotero.script_trigger
HKCU\Software\Microsoft\Edge\NativeMessagingHosts\org.zotero.script_trigger
```

### CLI cannot connect to the named pipe

Launch the Desktop shortcut `Zotero 自动化浏览器`, then rerun the command.

### `TARGET_COLLECTION_NOT_FOUND`

Confirm the collection already exists in Zotero Desktop and pass the complete path from the first collection below the library root.

### `TAB_AMBIGUOUS`

Use `list-tabs`, then pass an exact URL or tab ID.

### PowerShell red syntax errors

Use a current package. Packaging converts helper scripts to UTF-8 with BOM and verifies them with Windows PowerShell 5.1.

## Uninstall

Use `5-卸载.bat`. It closes the dedicated automation browser and removes the installed browser, extension, profile, shortcuts, native-host registration, CLI, and local configuration. It does not modify the user's normal Chrome installation or profile.