# Zotero Connector Script Trigger

This fork adds a Windows script entrypoint that invokes the existing Zotero Connector toolbar-button action. It does not reimplement translators, snapshots, PDF handling, item selection, or saving.

## Supported behavior

- Browser in foreground: supported.
- Browser behind another application: supported.
- Browser minimized: supported.
- Exact background tab by tab ID: supported.
- Browser completely closed: not supported; the CLI returns a connection error.
- Multi-item pages: the official Zotero item selector may still appear.

A successful CLI response with `"triggered": true` means the official Connector action accepted the command. It does not independently prove that Zotero finished writing the item, because official saving can continue asynchronously or require item selection.

## Build the extension

Use Git Bash or WSL from the repository root:

```bash
git submodule update --init --recursive
npm install
./build.sh -p b -d
```

Load `build/manifestv3` as an unpacked extension in Chrome or Edge.

## Install the Windows native host

1. Open `chrome://extensions` or `edge://extensions`.
2. Enable Developer mode.
3. Find the unpacked Zotero Connector and copy its 32-character extension ID.
4. Open PowerShell in the repository root.
5. Run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-script-trigger.ps1 -ExtensionId YOUR_EXTENSION_ID -Browser Chrome
```

For Edge, use `-Browser Edge`. V1 supports one enabled Chrome/Edge profile instance at a time because the native host owns one per-user named pipe.

The installer packages the Python host as an EXE with PyInstaller, writes a per-user named-pipe secret under `%LOCALAPPDATA%\ZoteroScriptTrigger`, and registers the native host under `HKCU`.

After installation, reload the unpacked extension once.

## Commands

```powershell
$cli = "$env:LOCALAPPDATA\ZoteroScriptTrigger\zotero_script_trigger_cli.py"
py -3 $cli ping
py -3 $cli save-active
py -3 $cli save-tab --tab-id 123
```

`save-active` means the selected tab in the browser's last-focused browser window. It does not bring the browser to the foreground.

## Find a tab ID

Open the extension service-worker console from `chrome://extensions`, then run:

```javascript
chrome.tabs.query({}, tabs => console.table(tabs.map(t => ({ id: t.id, active: t.active, title: t.title, url: t.url }))));
```

Use the desired `id` with `save-tab --tab-id`.

## Troubleshooting

### `Specified native messaging host not found`

Reload the extension after running the installer. Check these registry keys:

```text
HKCU\Software\Google\Chrome\NativeMessagingHosts\org.zotero.script_trigger
HKCU\Software\Microsoft\Edge\NativeMessagingHosts\org.zotero.script_trigger
```

### `Access to the specified native messaging host is forbidden`

The extension ID passed to the installer does not match the currently loaded unpacked extension. Re-run the installer with the current ID, then reload the extension.

### CLI cannot connect to the named pipe

The browser is closed, the extension is disabled, or the extension has not connected to the native host. Start the browser, enable/reload the extension, and run `ping` again.

### Command returns `UNSUPPORTED_URL`

The target is a browser-internal page such as `chrome://extensions`. Open an `http://` or `https://` page.

## Uninstall

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\uninstall-script-trigger.ps1
```
