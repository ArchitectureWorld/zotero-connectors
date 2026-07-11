# Zotero Connector Script Trigger

This fork adds a Windows-local command interface that invokes the existing Zotero Connector toolbar-button action. It does not reimplement translators, snapshots, PDF handling, item selection, or Zotero saving.

## Behavior

- Chrome may be foreground, covered, background, or minimized.
- No browser window or tab is focused or activated by the trigger.
- Exact background targeting is supported by tab ID or exact URL.
- URL/title substring targeting fails when multiple tabs match.
- Browser completely closed is not supported; the CLI returns a connection error.
- Multiple-item pages still use the official Zotero item selector.

A response with `"triggered": true` means the official Connector action accepted the command. Saving may continue asynchronously, and this response is not proof that Zotero persisted metadata or an attachment.

## Beginner package

GitHub Actions produces a Windows ZIP containing:

```text
浏览器插件/
app/zotero_script_trigger_host.exe
app/zotero_script_trigger_cli.exe
1-安装本地助手.bat
2-加载浏览器插件.bat
3-测试连接.bat
4-保存当前网页.bat
5-卸载.bat
```

The installed CLI is:

```text
%LOCALAPPDATA%\ZoteroScriptTrigger\zotero_script_trigger_cli.exe
```

The unpacked extension uses a fixed development key, so its extension ID remains stable across package rebuilds.

## Protocol v2

Run:

```powershell
$cli = "$env:LOCALAPPDATA\ZoteroScriptTrigger\zotero_script_trigger_cli.exe"
& $cli ping
```

A compatible response includes:

```json
{
  "success": true,
  "protocolVersion": 2,
  "capabilities": [
    "list-tabs",
    "save-active",
    "save-tab",
    "save-url",
    "save-title"
  ]
}
```

Agent integrations must require protocol version 2 and capability `save-url`.

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

For automation, prefer an exact URL obtained from the browser session. Do not use `save-active` when the result must be deterministic.

## Source build

Use Git Bash or WSL from the repository root:

```bash
git submodule update --init --recursive
npm install
./build.sh -p b -d
```

Load `build/manifestv3` as an unpacked extension in Chrome or Edge.

For source installation of the native host:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-script-trigger.ps1 -ExtensionId YOUR_EXTENSION_ID -Browser Chrome
```

V1/V2 packaging supports one enabled Chrome/Edge profile instance per Windows user because the native host owns one per-user named pipe.

## Agent integration sequence

1. Run `ping`; require protocol v2 and `save-url`.
2. Obtain the exact URL of the already-open target page.
3. Run `save-url --url <exact-url>`.
4. Confirm the returned URL equals the requested URL.
5. Independently poll Zotero for the expected metadata and attachment.

See `docs/AGENT_INTEGRATION.md` for the machine contract.

## Troubleshooting

### Native host not found or forbidden

Reload the extension after installation and confirm the extension ID matches the host manifest. Registry locations:

```text
HKCU\Software\Google\Chrome\NativeMessagingHosts\org.zotero.script_trigger
HKCU\Software\Microsoft\Edge\NativeMessagingHosts\org.zotero.script_trigger
```

### CLI cannot connect to the named pipe

Chrome/Edge is closed, the extension is disabled, the extension has not been reloaded after installation, or another enabled browser/profile owns the per-user pipe.

### `TAB_AMBIGUOUS`

Use `list-tabs`, then pass an exact URL or tab ID.

### PowerShell red syntax errors

Use a current package. Packaging converts helper scripts to UTF-8 with BOM and verifies them with Windows PowerShell 5.1.

## Uninstall

Use `5-卸载.bat` from the package or:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\uninstall-script-trigger.ps1
```
