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

The installer writes these values once for each dedicated profile. They are not rewritten for each save operation.

The Connector initialization layer applies `connectorUrl` to the same preference consumed by normal Zotero Connector RPC calls. This guarantees that toolbar-button saves and Script Trigger saves use the same Zotero instance.

## 5. Manual save path

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

## 6. Linux Native Messaging layout

Register two Native Messaging host names:

```text
org.zotero.script_trigger.zzh
org.zotero.script_trigger.nsy
```

Both manifests may point to small instance-specific launchers that execute one shared host implementation.

Recommended user-level files:

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

${XDG_RUNTIME_DIR:-~/.local/run}/zotero-script-trigger/
├─ zzh.sock
└─ nsy.sock
```

The two launchers supply the instance identity to the shared host implementation. The host creates only its assigned Unix domain socket.

### ZZH host configuration

```json
{
  "instanceId": "ZZH",
  "socketPath": "${XDG_RUNTIME_DIR}/zotero-script-trigger/zzh.sock",
  "nativeHostName": "org.zotero.script_trigger.zzh",
  "connectorUrl": "http://127.0.0.1:23119/"
}
```

### NSY host configuration

```json
{
  "instanceId": "NSY",
  "socketPath": "${XDG_RUNTIME_DIR}/zotero-script-trigger/nsy.sock",
  "nativeHostName": "org.zotero.script_trigger.nsy",
  "connectorUrl": "http://127.0.0.1:23120/"
}
```

The socket directory and socket files must be owned by the current user and must not be writable by other users.

## 7. Linux host and CLI transport

The existing request/response model remains unchanged. Only the local transport differs by platform.

```text
Windows
CLI ↔ authenticated AF_PIPE channel ↔ Native Host ↔ Extension

Linux
CLI ↔ user-owned AF_UNIX socket ↔ Native Host ↔ Extension
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

## 8. Connector identity response

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

## 9. Automatic execution path

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

## 10. Mismatch behavior

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

The error result includes expected and actual routing values, but no credentials, cookies, browser-profile contents, or Zotero data.

## 11. Installation and profile provisioning

Linux packaging adds one installer that provisions both identities from a declarative mapping.

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
3. install two instance launchers and two config files;
4. configure the ZZH profile with ZZH settings;
5. configure the NSY profile with NSY settings;
6. leave Windows packaging and configuration unchanged;
7. support deterministic reinstallation without swapping profile identities.

The actual Chrome profile directories remain external configuration and are not committed to Git.

## 12. Failure handling

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

## 13. Test design

### Extension tests

- ZZH preferences produce a ping identity containing ZZH and `23119`.
- NSY preferences produce a ping identity containing NSY and `23120`.
- toolbar save uses the profile-local Connector URL.
- Script Trigger save uses the same profile-local Connector URL.
- a profile cannot be reassigned by an individual save request.
- two simulated extension instances remain isolated.

### Host and CLI tests

- ZZH and NSY use different Unix sockets.
- simultaneous hosts route responses only to their own clients.
- socket permissions are user-only.
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

## 14. Compatibility boundary

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

macOS is outside this implementation scope. The transport interface should remain separable so a later macOS Unix-socket implementation does not require changes to extension save logic.

## 15. Cross-repository contract

`ArchitectureWorld/skill-hub` consumes this Connector contract through:

```text
profileId
connectorUrl
nativeHostName
protocolVersion >= 4
capability instance-routing
```

The Skill-side browser routing map owns the `9222/9223` association. This repository owns profile-local Connector identity, local host transport, and correct manual/automatic save delivery.

## 16. Non-goals

This design does not:

- merge the two Zotero libraries;
- synchronize records between ZZH and NSY;
- infer a browser profile from website content;
- infer the debugging port inside the extension;
- switch a profile's Zotero target per request;
- add multi-user or network-exposed sockets;
- change Windows single-instance behavior;
- create a generic service-discovery system.
