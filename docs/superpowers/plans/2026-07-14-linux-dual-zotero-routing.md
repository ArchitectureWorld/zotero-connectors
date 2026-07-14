# Linux Dual-Zotero Connector Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Linux support for two simultaneously running Chrome profiles and Zotero instances with immutable bindings `9222/ZZH/23119` and `9223/NSY/23120`, while preserving current Windows behavior.

**Architecture:** The extension stores one immutable instance identity in profile-local storage and reports it through protocol v4. Linux Native Messaging uses two host names and two authenticated Unix sockets backed by one shared Python implementation. Manual toolbar saves and Script Trigger saves both consume the same profile-local `connector.url`.

**Tech Stack:** Chrome Manifest V3, JavaScript, Node.js `node:test`, Python 3.10+, Unix domain sockets, Native Messaging, PowerShell packaging retained for Windows.

## Global Constraints

- One shared Connector codebase; no ZZH/NSY source forks.
- ZZH binding: `9222 ↔ ZZH ↔ org.zotero.script_trigger.zzh ↔ http://127.0.0.1:23119/`.
- NSY binding: `9223 ↔ NSY ↔ org.zotero.script_trigger.nsy ↔ http://127.0.0.1:23120/`.
- Linux profile settings are written only through extension-owned storage APIs.
- Linux commands never probe both instances and never fall back to `23119`.
- Windows protocol v3, named-pipe transport, commands, and packaging remain compatible.
- Socket/config permissions are user-only; sockets are never network-exposed.

---

### Task 1: Profile-local instance settings model

**Files:**
- Create: `src/browserExt/instanceSettings.js`
- Create: `script-trigger-tests/instance-settings.test.js`

**Interfaces:**
- Produces: `normalizeInstanceSettings(value)`, `readInstanceSettings(storage)`, `applyInstanceSettings(storage, value)`.
- Storage keys: `scriptTrigger.profileId`, `scriptTrigger.nativeHostName`, `connector.url`.

- [ ] **Step 1: Write failing tests** covering valid ZZH/NSY values, incomplete settings, non-loopback URLs, unsupported profile IDs, and persistence of all three keys in one operation.
- [ ] **Step 2: Run `node --test script-trigger-tests/instance-settings.test.js`** and confirm failure because `instanceSettings.js` does not exist.
- [ ] **Step 3: Implement minimal validation and storage helpers**. Accept only `ZZH` and `NSY`; require `http://127.0.0.1:<port>/`; require host name `org.zotero.script_trigger.<lowercase-id>`.
- [ ] **Step 4: Re-run the focused test and the existing extension tests**.
- [ ] **Step 5: Commit** with `feat: add profile-local Zotero instance settings`.

### Task 2: Extension configuration page

**Files:**
- Create: `src/browserExt/instanceSettings/instance-settings.html`
- Create: `src/browserExt/instanceSettings/instance-settings.js`
- Create: `src/browserExt/instanceSettings/instance-settings.css`
- Modify: `src/browserExt/manifest-v3.json`
- Create: `script-trigger-tests/instance-settings-page.test.js`

**Interfaces:**
- Consumes: `applyInstanceSettings()` and `readInstanceSettings()`.
- Produces: an extension page opened as `instanceSettings/instance-settings.html?instance=ZZH|NSY`.

- [ ] **Step 1: Write a source-contract test** asserting the page contains Profile ID, Zotero URL, Native Host fields, an explicit Apply button, and no direct Chrome profile-file access.
- [ ] **Step 2: Run the test and confirm it fails** because the page is absent.
- [ ] **Step 3: Implement the page** so query parameter `instance=ZZH|NSY` prefills fixed values and Apply writes through `browser.storage.local`; existing values are displayed on load.
- [ ] **Step 4: Add the settings script to the MV3 build source list only as an extension page; do not replace the existing Zotero options page.**
- [ ] **Step 5: Run the focused tests and manifest parsing tests.**
- [ ] **Step 6: Commit** with `feat: add Linux Connector instance settings page`.

### Task 3: Protocol v4 instance identity

**Files:**
- Modify: `src/browserExt/scriptTrigger.js`
- Modify: `src/browserExt/background-worker.js` only if an explicit load order is required
- Modify: `script-trigger-tests/extension.test.js`
- Create: `script-trigger-tests/instance-routing.test.js`

**Interfaces:**
- `createScriptTrigger({ browserAPI, zotero, hostName, instanceIdentity, autoConnect })`.
- Linux identity response fields: `profileId`, `nativeHostName`, `connectorUrl`, `protocolVersion: 4`, capability `instance-routing`.
- Legacy invocation without `instanceIdentity` remains protocol v3.

- [ ] **Step 1: Add failing tests** proving legacy ping remains v3, routed ping is v4, routed host name is used by `connectNative`, incomplete identity is rejected, and a request cannot override identity.
- [ ] **Step 2: Run the tests and confirm expected failures.**
- [ ] **Step 3: Implement instance-aware protocol selection** and immutable identity reporting.
- [ ] **Step 4: Change extension startup** to await initialized profile storage, apply stored `connector.url`, and create Script Trigger with the stored host identity; on Linux incomplete configuration leaves Script Trigger disconnected with `CONNECTOR_INSTANCE_NOT_CONFIGURED`.
- [ ] **Step 5: Run all `script-trigger-tests/*.test.js`.**
- [ ] **Step 6: Commit** with `feat: report immutable Connector instance identity`.

### Task 4: Cross-platform host configuration

**Files:**
- Modify: `native-host/host_config.py`
- Modify: `native-host/tests/test_host_config.py` or create it if absent

**Interfaces:**
- `HostConfig(instance_id, authkey, pipe_name=None, socket_path=None, native_host_name=None, connector_url=None)`.
- `load_config(path)` validates exactly one transport endpoint for the current configuration.

- [ ] **Step 1: Write failing Python tests** for legacy Windows config, Linux socket config, absolute socket path, loopback connector URL, distinct instance keys, and invalid mixed transport.
- [ ] **Step 2: Run `python -m unittest native-host.tests.test_host_config -v`** and confirm failures.
- [ ] **Step 3: Implement the expanded frozen dataclass and validation** without breaking existing Windows JSON.
- [ ] **Step 4: Run focused and existing native-host tests.**
- [ ] **Step 5: Commit** with `feat: support Unix-socket host configuration`.

### Task 5: Linux Unix-socket CLI transport

**Files:**
- Modify: `native-host/zotero_script_trigger_cli.py`
- Modify: `native-host/tests/test_cli.py`
- Create: `native-host/tests/test_cli_unix.py`

**Interfaces:**
- CLI options: `--instance ZZH|NSY`, existing `--config`, existing save subcommands.
- Linux transport: authenticated `multiprocessing.connection.Client(socket_path, family="AF_UNIX", authkey=authkey)`.

- [ ] **Step 1: Add failing tests** for instance config resolution, AF_UNIX selection, no first-responsive probing, missing instance, and preservation of Windows AF_PIPE behavior.
- [ ] **Step 2: Run focused tests and confirm failure.**
- [ ] **Step 3: Implement platform transport selection** and `--instance` configuration lookup under `~/.config/zotero-script-trigger/<lowercase>.json`.
- [ ] **Step 4: Run all CLI tests.**
- [ ] **Step 5: Commit** with `feat: add Linux Script Trigger CLI transport`.

### Task 6: Linux Unix-socket host broker

**Files:**
- Modify: `native-host/zotero_script_trigger_host.py`
- Modify: `native-host/tests/test_host_broker.py`
- Create: `native-host/tests/test_host_broker_unix.py`

**Interfaces:**
- Windows listener remains `AF_PIPE`.
- Linux listener uses one configured `AF_UNIX` path and the configured auth key.
- Startup removes only its own stale socket after proving no live listener owns it.

- [ ] **Step 1: Add failing tests** for AF_UNIX listener creation, `0700` runtime directory, user-only socket/config modes, independent simultaneous brokers, and safe stale-socket handling.
- [ ] **Step 2: Run tests and confirm failure.**
- [ ] **Step 3: Refactor transport creation behind a focused helper** and implement the Linux listener.
- [ ] **Step 4: Run all native-host tests.**
- [ ] **Step 5: Commit** with `feat: add Linux Native Messaging socket broker`.

### Task 7: Linux provisioning assets

**Files:**
- Create: `packaging/linux/install-linux-dual-instance.py`
- Create: `packaging/linux/launch-instance.py`
- Create: `packaging/linux/uninstall-linux-dual-instance.py`
- Create: `packaging/linux/README.md`
- Create: `packaging/tests/linux-dual-instance.test.py`

**Interfaces:**
- Installer input: explicit ZZH and NSY Chrome user-data directories and fixed ports.
- Outputs: two user-level Native Messaging manifests, two config files, two launchers, one shared host/CLI installation, and settings-page URLs.

- [ ] **Step 1: Write failing filesystem tests** using temporary HOME/XDG directories.
- [ ] **Step 2: Run focused tests and confirm missing implementation.**
- [ ] **Step 3: Implement deterministic install/uninstall** with atomic writes, user-only permissions, generated per-instance auth keys, and no Chrome LevelDB/Preferences modification.
- [ ] **Step 4: Verify reinstall preserves identity and uninstall removes only managed files.**
- [ ] **Step 5: Commit** with `feat: provision Linux dual Zotero instances`.

### Task 8: CI, documentation, and acceptance contract

**Files:**
- Create: `.github/workflows/test-linux-instance-routing.yml`
- Modify: `README.md`
- Modify: `docs/AGENT_INTEGRATION.md`
- Modify: `docs/SCRIPT_TRIGGER.md`
- Create: `docs/reviews/2026-07-14-linux-dual-zotero-routing-review.md`

**Interfaces:**
- CI runs Node tests and Python tests on Ubuntu plus existing Windows workflows unchanged.

- [ ] **Step 1: Add workflow/source contract tests** proving protocol v3 remains on legacy mode and Linux routing tests run on Ubuntu.
- [ ] **Step 2: Implement workflow and documentation.**
- [ ] **Step 3: Run repository tests locally where available and push.**
- [ ] **Step 4: Confirm GitHub Actions pass for extension, native-host, Linux routing, and unchanged Windows package workflows.**
- [ ] **Step 5: Write review findings and remaining real-machine acceptance steps.**
- [ ] **Step 6: Commit** with `test: validate Linux dual Zotero routing`.
