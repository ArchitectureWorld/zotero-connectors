# Linux Dual-Zotero Routing Implementation Review

Date: 2026-07-14  
Branch: `docs/linux-dual-zotero-routing`

## Verdict

The implementation now provides one shared Manifest V3 Connector build with two isolated Linux runtime identities:

```text
9222 ↔ ZZH ↔ org.zotero.script_trigger.zzh ↔ 23119
9223 ↔ NSY ↔ org.zotero.script_trigger.nsy ↔ 23120
```

Automated extension, Native Host, provisioning, build, package-layout, and packaged-installer smoke tests pass. Windows protocol v3 and named-pipe tests remain unchanged and pass in the repository CI.

The PR must remain Draft until both real Chrome profiles and both real Zotero instances complete the manual and automatic cross-instance acceptance cases.

## Implemented boundaries

### Browser profile

- One Connector source and one stable extension ID are used in both Chrome profiles.
- ZZH and NSY store independent values in profile-local extension storage.
- The settings page allows only the two fixed presets.
- The Connector applies `connector.url` before opening its instance-specific Native Messaging channel.
- Manual toolbar saves and Script Trigger saves therefore share the same Zotero target.

### Local transport

- Windows retains authenticated `AF_PIPE` transport.
- Linux uses one authenticated `AF_UNIX` socket per instance.
- The two instances use separate config files, sockets, Native Host names, launchers, and authentication keys.
- The CLI requires an explicit instance and never probes the other socket.

### Protocol

- Legacy mode remains protocol v3.
- Routed Linux mode reports protocol v4 and capability `instance-routing`.
- Ping returns immutable `profileId`, `instanceId`, `connectorUrl`, and `nativeHostName`.
- Save requests cannot override the profile identity.

## Review findings

| Finding | Severity | Resolution |
| --- | --- | --- |
| A standalone extension settings page used `browser.storage` without explicitly loading the Chrome browser-API polyfill. | High | The page now loads `browser-polyfill.js` before the settings API and page controller. A source-order regression test locks this requirement. |
| The first AF_UNIX implementation removed any existing socket path before binding. A second Host start could unlink a live instance socket. | Critical | Existing socket paths are ownership-checked and probed. A live listener returns an already-running error and is never unlinked. |
| A symbolic link at the configured socket path could redirect cleanup outside the managed runtime path. | Critical | Symbolic socket paths are rejected before probing or removal. |
| Test doubles do not create an actual socket file, while production permission code immediately applied `chmod`. | Medium | Socket permission hardening runs only after a real Listener creates the path; production still enforces `0600`. |
| Generated shell wrappers interpolated absolute paths without shell quoting. | High | Paths now use `shlex.quote`; regression coverage installs under directories containing spaces and parses the generated commands. |
| The initial ZIP used Chinese file and directory names. Info-ZIP encoded them as literal `#U...` names. | High | The release archive now uses portable ASCII paths: `install.sh`, `uninstall.sh`, and `browser-extension/`; CI rejects any `#U` archive entry. |
| The first assembled package flattened Linux installer files into a display folder, so the installer could not find the real `launch-instance.py` source path. | Medium | The package now preserves `packaging/linux/` and smoke-tests installation and uninstall directly from the assembled package. |
| Installer code must not alter Chrome profile databases or Preferences. | High | Provisioning writes only Native Host/config/launcher files and outputs extension settings-page URLs. Tests preserve existing `Preferences` content and reject shared profile directories. |

## Security and isolation review

- Connector and Zotero endpoints remain loopback-only.
- Runtime directories are `0700`; config and socket files are user-only.
- Per-instance authentication keys are distinct even when the injected random source is identical in tests.
- Native Messaging manifests restrict `allowed_origins` to the stable Connector extension ID.
- The installer is user-level and never exposes a TCP listener.
- Uninstall removes only managed files and preserves unrelated user files.
- No request-level route switching or automatic fallback exists.

## Automated evidence

The Linux routing workflow covers:

- extension instance settings and settings-page contracts;
- legacy protocol v3 and routed protocol v4 behavior;
- fixed Native Host selection;
- AF_UNIX config, CLI, and Host broker behavior;
- active-socket and symbolic-path protection;
- dual-instance installer and uninstall behavior;
- paths containing spaces;
- Manifest V3 production build;
- stable extension ID;
- packaged installer smoke test;
- portable archive filenames;
- uploaded Linux dual-instance package.

The unchanged repository CI also passes on the same branch head.

## Remaining real-machine acceptance

With all four processes running simultaneously:

```text
ZZH Chrome on 9222
NSY Chrome on 9223
ZZH Zotero on 23119
NSY Zotero on 23120
```

Complete:

1. install the same packaged Connector into both dedicated Chrome profiles;
2. apply ZZH settings in the ZZH profile and NSY settings in the NSY profile;
3. manually save from ZZH and confirm only Zotero 23119 changes;
4. manually save from NSY and confirm only Zotero 23120 changes;
5. run `--instance ZZH ping` and `--instance NSY ping` and inspect their identities;
6. trigger an exact URL through each instance and confirm no cross-library change;
7. stop NSY Zotero and confirm NSY fails without touching ZZH;
8. intentionally cross-wire one profile setting and confirm the operation stops before saving.

Until those cases pass, the implementation is automated-test complete but not production-proven on the target Linux machine.
