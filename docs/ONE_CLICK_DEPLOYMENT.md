# One-click local deployment

## User contract

The normal Windows installation path is a single file:

```text
0-一键安装并启动.bat
```

The user does not install Python or Node.js, does not open `chrome://extensions`, and does not select an unpacked extension directory.

## Installed components

The package installs all runtime components below:

```text
%LOCALAPPDATA%\ZoteroScriptTrigger\
├─ zotero_script_trigger_host.exe
├─ zotero_script_trigger_cli.exe
├─ org.zotero.script_trigger.json
├─ config.json
├─ extension\
├─ browser\chrome-win64\
├─ browser-profile\
├─ launch-automation-browser.ps1
├─ installation-state.json
└─ browser-state.json
```

The installer also creates:

```text
Desktop\Zotero 自动化浏览器.lnk
Start Menu\Programs\Zotero Script Trigger\Zotero 自动化浏览器.lnk
```

## Why a bundled automation browser is used

Windows Chrome does not provide a supported silent local-CRX installation flow for ordinary user profiles. The one-click package therefore includes a pinned Chrome for Testing runtime and starts it with the unpacked Connector from the installed directory.

This keeps deployment deterministic and avoids:

- developer-mode clicks;
- manually selecting the extension directory;
- depending on the user's existing Chrome profile;
- interfering with the user's normal Chrome process;
- extension path breakage after deleting the downloaded ZIP.

## Installation sequence

`install-all.ps1` performs the following transaction:

1. Validate that the package contains the extension, browser runtime, native host, and CLI.
2. Stop only a previously installed dedicated automation-browser process.
3. Generate a fresh authenticated named-pipe configuration.
4. Register the Native Messaging host for Chrome and Edge under the current user.
5. Copy the extension and browser runtime into `%LOCALAPPDATA%`.
6. Create desktop and Start Menu shortcuts.
7. Launch the dedicated browser with:
   - a persistent dedicated profile;
   - the installed unpacked extension;
   - no first-run or default-browser prompts.
8. Poll the installed CLI until `ping` confirms protocol version 3 and capability `save-to-collection`.
9. Write `installation-state.json` only after self-test succeeds.

The installer exits non-zero if any stage fails.

## Browser profile and login state

The dedicated profile is stored at:

```text
%LOCALAPPDATA%\ZoteroScriptTrigger\browser-profile
```

Authentication cookies for CNKI, university proxy pages, and other trusted sources persist there. Account login is intentionally not copied from the user's normal Chrome profile because copying an active profile is unsafe and unreliable.

## Reinstallation

Re-running `0-一键安装并启动.bat` is supported. It closes only the bundled automation browser, replaces installed runtime files, creates a fresh local communication channel, restarts the browser, and reruns protocol verification.

## Uninstallation

`5-卸载.bat` removes:

- the dedicated browser process;
- Native Messaging registry entries;
- the installed extension and browser runtime;
- the dedicated browser profile;
- desktop and Start Menu shortcuts;
- installation state and communication configuration.

It does not alter the user's normal Chrome installation or profile.

## Build artifact

GitHub Actions publishes:

```text
Zotero-Script-Trigger-OneClick-v3.zip
```

The artifact includes a stable Chrome for Testing win64 build resolved during packaging, the protocol-v3 extension, packaged native executables, installer scripts, and regression-checked PowerShell files.