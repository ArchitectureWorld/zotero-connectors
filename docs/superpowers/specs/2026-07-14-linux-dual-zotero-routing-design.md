# Linux Dual-Zotero Connector Routing Design

Date: 2026-07-14  
Status: approved architecture, implementation not started  
Repository: `ArchitectureWorld/zotero-connectors`

## 1. Objective

Support two Zotero Desktop instances and two independent Chrome profiles running at the same time on one Linux computer.

The fixed bindings are:

```text
ZZH Chrome profile
- Chrome remote debugging: 127.0.0.1:9222
- Connector profile ID: ZZH
- Zotero Connector/API base URL: http://127.0.0.1:23119/

NSY Chrome profile
- Chrome remote debugging: 127.0.0.1:9223
- Connector profile ID: NSY
- Zotero Connector/API base URL: http://127.0.0.1:23120/
```

The same custom Script Trigger Connector source is installed in both Chrome profiles. Each profile stores its own routing configuration. Manual toolbar clicks and program-triggered saves must always reach the Zotero instance assigned to that profile.

Windows behavior remains unchanged. Linux-specific routing must not alter the normal single-instance path on other operating systems.

## 2. Current constraints

The existing Connector already resolves local Zotero requests from the profile-local `connector.url` preference. The default value is `http://127.0.0.1:23119/`.

The current Script Trigger host and CLI are Windows-specific:

- local communication uses Windows named pipes;
- the CLI rejects non-Windows systems;
- the host rejects non-Windows systems;
- the Skill-side Connector client assumes the packaged Windows executable.

The browser extension cannot reliably read Chrome's `--remote-debugging-port` startup argument. Therefore the extension must not attempt to infer `9222` or `9223` by itself.

## 3. Selected architecture

Use four independently bound values as one execution identity:

```text
Chrome debugging endpoint
↔ Connector profile ID
↔ Linux Native Messaging channel
↔ Zotero base URL
```

The two identities are immutable during a browser session:

```text
ZZH = 9222 ↔ ZZH ↔ org.zotero.script_trigger.zzh ↔ 23119
NSY = 9223 ↔ NSY ↔ org.zotero.script_trigger.nsy ↔ 23120
```

No runtime command may switch one running profile from one Zotero instance to the other.

## 4. Browser-profile configuration

Each Chrome profile stores its own extension preferences in profile-local extension storage.

### ZZH profile

```json
{
  "profileId": "ZZH",
  "connectorUrl": "http://127.0.0.1:23119/",
  "nativeHostName": "org.zotero.script_trigger.zzh"
}
```

### NSY profile

```json
{
  "profileId": "NSY",
  "connectorUrl": "http://127.0.0.1:23120/",
  "nativeHostName": "org.zotero.script_trigger.nsy"
}
```

These values are written through an extension-owned Linux instance settings page into `chrome.storage.local`. The installer may open the settings page in each dedicated profile with the intended values prefilled, but it must not edit Chrome's internal preference or LevelDB files directly.

The user or the profile-provisioning automation applies the settings once for each profile. They are not rewritten for each save operation.

The settings page displays all three bound fields together and requires one explicit apply action:

```text
Profile ID
Zotero Connector URL
Native Host name
```

The Connector initialization layer applies `connectorUrl` to the same `connector.url` preference consumed by normal Zotero Connector RPC calls. This guarantees that toolbar-button saves and Script Trigger saves use the same Zotero instance.

## 5. Extension initialization order

The current Script Trigger connects to a default Native Host during background initialization. Linux instance routing requires a deterministic order:

```text
initialize extension preferences
→ read profileId, connectorUrl, nativeHostName
→ reject incomplete or invalid instance settings
→ apply connectorUrl to connector.url
→ create Script Trigger with the configured nativeHostName
→ connect to that host only
```

The extension must not briefly connect to the default host and then switch to another host. A missing Linux profile configuration returns `CONNECTOR_INSTANCE_NOT_CONFIGURED` and leaves Script Trigger disconnected.

Normal Zotero Connector functionality may still initialize, but save requests must use only the configured `connector.url`.

The extension manifest and request layer must allow loopback Connector requests on both `23119` and `23120`. Permission design should cover `http://127.0.0.1/*` rather than one hard-coded port.

## 6. Manual save path

Manual use does not depend on the automation controller or Chrome debugging endpoint.

```text
Toolbar click in ZZH Chrome
→ ZZH profile-local connector.url
→ http://127.0.0.1:23119/
→ ZZH Zotero instance
```

```text
Toolbar click in NSY Chrome
→ NSY profile-local connector.url
→ http://127.0.0.1:23120/
→ NSY Zotero instance
```

A manual save must never consult the other profile's configuration.

## 7. Linux Native Messaging layout

Register two Native Messaging host names:

```text
org.zotero.script_trigger.zzh
org.zotero.script_trigger.nsy
```

Both manifests point to small instance-specific launchers that execute one shared host implementation.

Recommended Google Chrome user-level files:

```text
~/.config/google-chrome/NativeMessagingHosts/
├─ org.zotero.script_trigger.zzh.json
└─ org.zotero.script_trigger.nsy.json

~/.local/lib/zotero-script-trigger/
├─ zotero_script_trigger_host.py
├─ zotero_script_trigger_cli.py
├─ host_config.py
├─ launch-zzh
└─ launch-nsy

~/.config/zotero-script-trigger/
├─ zzh.json
└─ nsy.json

${XDG_RUNTIME_DIR:-$HOME/.local/run}/zotero-script-trigger/
├─ zzh.sock
└─ nsy.sock
```

Chromium-family alternatives may use a different Native Messaging manifest directory, but Google Chrome is the first supported Linux target.

The two launchers supply the instance identity to the shared host implementation. The host creates only its assigned Unix domain socket.

### ZZH host configuration

```json
{
  "instanceId": "ZZH",
  "socketPath": "${XDG_RUNTIME_DIR}/zotero-script-trigger/zzh.sock",
  "nativeHostName": "org.zotero.script_trigger.zzh",
  "connectorUrl": "http://127.0.0.1:23119/",
  "authkey": "<generated-instance-secret>"
}
```

### NSY host configuration

```json
{
  "instanceId": "NSY",
  "socketPath": "${XDG_RUNTIME_DIR}/zotero-script-trigger/nsy.sock",
  "nativeHostName": "org.zotero.script_trigger.nsy",
  "connectorUrl": "http://127.0.0.1:23120/",
  "authkey": "<generated-instance-secret>"
}
```

The real config writer expands the runtime directory to an absolute path. Literal environment-variable expressions are documentation only and are not stored as unresolved paths.

The socket directory and socket files must be owned by the current user. Directory permissions are `0700`, socket/config permissions are user-only, and each instance has a different generated authentication key.

## 8. Linux host and CLI transport

The existing request/response model remains unchanged. Only the local transport differs by platform.

```text
Windows
CLI ↔ authenticated AF_PIPE channel ↔ Native Host ↔ Extension

Linux
CLI ↔ authenticated user-owned AF_UNIX socket ↔ Native Host ↔ Extension
```

The public CLI commands remain compatible:

```text
ping
list-tabs
save-active
save-tab
save-url
save-title
```

Collection targeting remains available when inherited from protocol v3.

The Linux CLI receives an explicit instance selector:

```bash
zotero-script-trigger --instance ZZH ping
zotero-script-trigger --instance NSY save-url --url '<exact-url>'
```

An equivalent explicit configuration path is also supported for tests and advanced use:

```bash
zotero-script-trigger --config ~/.config/zotero-script-trigger/nsy.json ping
```

The CLI must not probe every socket and choose the first responsive instance.

## 9. Connector identity response

The `ping` response is extended so callers can bind a command to the intended browser and Zotero instance.

```json
{
  "success": true,
  "action": "ping",
  "extensionId": "...",
  "extensionVersion": "...",
  "protocolVersion": 4,
  "capabilities": [
    "list-tabs",
    "save-url",
    "save-to-collection",
    "instance-routing"
  ],
  "profileId": "NSY",
  "nativeHostName": "org.zotero.script_trigger.nsy",
  "connectorUrl": "http://127.0.0.1:23120/"
}
```

Protocol v4 denotes instance-routing identity. Existing protocol v2/v3 commands remain structurally compatible.

The response fields come from the extension's applied profile configuration. The host passes them through but does not replace them with its own expected values.

## 10. Automatic execution path

The automation controller selects a Chrome debugging endpoint first. The selected endpoint determines the expected Connector identity.

```text
Connect to 127.0.0.1:9223
→ select NSY routing record
→ call NSY CLI/socket
→ receive Connector ping identity
→ require NSY + 23120 + NSY host name
→ trigger the exact tab in the NSY browser
→ read import results from 23120
```

The extension does not derive its identity from the debugging port. The controller supplies the expectation, while the extension reports its stored identity.

## 11. Mismatch behavior

A command stops before saving when any bound value disagrees.

Stable error code:

```text
BROWSER_ZOTERO_TARGET_MISMATCH
```

Examples:

```text
9223 selected, but profileId=ZZH
9223 selected, but connectorUrl=23119
9222 selected, but nativeHostName is the NSY host
NSY socket selected, but ping reports ZZH
```

There is no fallback to port `23119` and no automatic search for another running Zotero instance.

The error result includes expected and actual routing values, but no authentication keys, credentials, cookies, browser-profile contents, or Zotero data.

## 12. Installation and profile provisioning

Linux packaging adds one installer that provisions both host identities from a declarative mapping.

Example input:

```json
{
  "instances": {
    "ZZH": {
      "chromeDebugPort": 9222,
      "chromeUserDataDir": "/path/to/zzh-profile",
      "connectorUrl": "http://127.0.0.1:23119/"
    },
    "NSY": {
      "chromeDebugPort": 9223,
      "chromeUserDataDir": "/path/to/nsy-profile",
      "connectorUrl": "http://127.0.0.1:23120/"
    }
  }
}
```

The installer must:

1. install one shared Connector build;
2. install two Native Messaging manifests;
3. install two instance launchers and two protected config files;
4. open the ZZH profile's extension settings page with ZZH values prefilled;
5. open the NSY profile's extension settings page with NSY values prefilled;
6. report completion only after each profile's `ping` returns its assigned identity;
7. leave Windows packaging and configuration unchanged;
8. support deterministic reinstallation without swapping profile identities.

Provisioning must use the extension settings interface or extension messaging. It must not manipulate Chrome's internal profile databases.

The actual Chrome profile directories, generated authentication keys, and runtime sockets remain local and are not committed to Git.

## 13. Failure handling

| Condition | Result |
| --- | --- |
| Assigned Zotero port is unavailable | `ZOTERO_INSTANCE_OFFLINE` |
| Assigned Unix socket is unavailable | `SCRIPT_TRIGGER_INSTANCE_OFFLINE` |
| Native Host identity differs | `BROWSER_ZOTERO_TARGET_MISMATCH` |
| Connector URL differs | `BROWSER_ZOTERO_TARGET_MISMATCH` |
| More than one tab matches a non-exact selector | Existing `TAB_AMBIGUOUS` behavior |
| Exact target tab changes before save | Existing `TARGET_CHANGED` behavior |
| Profile setting is missing | `CONNECTOR_INSTANCE_NOT_CONFIGURED` |

Normal toolbar use may display the standard Zotero-offline message when only its assigned Zotero instance is unavailable. It must not attempt the other Zotero port.

## 14. Test design

### Extension tests

- ZZH preferences produce a ping identity containing ZZH and `23119`.
- NSY preferences produce a ping identity containing NSY and `23120`.
- incomplete Linux instance settings leave Script Trigger disconnected.
- startup connects directly to the configured Native Host without touching the other host.
- toolbar save uses the profile-local Connector URL.
- Script Trigger save uses the same profile-local Connector URL.
- a profile cannot be reassigned by an individual save request.
- two simulated extension instances remain isolated.

### Settings-page tests

- profile settings are stored only in extension-owned storage.
- invalid profile IDs, non-loopback URLs, and unknown host names are rejected.
- applying NSY settings cannot modify ZZH profile storage.
- reinstall preserves a previously applied identity unless the same profile is explicitly reprovisioned.

### Host and CLI tests

- ZZH and NSY use different Unix sockets and authentication keys.
- simultaneous hosts route responses only to their own clients.
- socket and config permissions are user-only.
- `--instance ZZH` cannot silently use NSY configuration.
- stale socket cleanup does not remove the other instance's live socket.
- Windows named-pipe tests remain unchanged.

### End-to-end Linux acceptance

Run all four processes simultaneously:

```text
ZZH Chrome on 9222
NSY Chrome on 9223
ZZH Zotero on 23119
NSY Zotero on 23120
```

Then complete:

1. manual save from ZZH Chrome and confirm it appears only in ZZH Zotero;
2. manual save from NSY Chrome and confirm it appears only in NSY Zotero;
3. automatic exact-URL save through 9222 and confirm only 23119 changes;
4. automatic exact-URL save through 9223 and confirm only 23120 changes;
5. stop NSY Zotero and confirm NSY operations fail without touching ZZH;
6. intentionally swap one profile setting and confirm execution stops with `BROWSER_ZOTERO_TARGET_MISMATCH`.

## 15. Compatibility boundary

```text
Linux dual-instance mode
- explicit instance mapping is required
- AF_UNIX transport
- two Native Messaging host names
- profile-local Connector URLs

Windows current mode
- existing package and named-pipe transport
- existing single-instance default
- default Zotero URL remains 23119
```

macOS is outside this implementation scope. The transport interface remains separable so a later macOS Unix-socket implementation does not require changes to extension save logic.

## 16. Cross-repository contract

`ArchitectureWorld/skill-hub` consumes this Connector contract through:

```text
profileId
connectorUrl
nativeHostName
protocolVersion >= 4
capability instance-routing
```

The Skill-side browser routing map owns the `9222/9223` association. This repository owns profile-local Connector identity, local host transport, and correct manual/automatic save delivery.

Implementation order is fixed:

```text
1. Connector profile settings and Linux transport
2. protocol v4 identity response
3. live dual-profile Connector acceptance
4. Skill-side route consumption
```

The Skill-side implementation must not merge before the Connector contract is available on its dependency branch or release.

## 17. Non-goals

This design does not:

- merge the two Zotero libraries;
- synchronize records between ZZH and NSY;
- infer a browser profile from website content;
- infer the debugging port inside the extension;
- switch a profile's Zotero target per request;
- add multi-user or network-exposed sockets;
- change Windows single-instance behavior;
- create a generic service-discovery system.
