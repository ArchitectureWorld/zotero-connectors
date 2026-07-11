# Zotero Connector Script Trigger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Windows Python-script trigger that invokes the official Zotero Connector save action without depending on browser focus.

**Architecture:** A background extension module connects to a native messaging host. The packaged Python host bridges browser messages to a per-user Windows named pipe used by a CLI. The extension resolves tabs and calls the existing official save entrypoint.

**Tech Stack:** WebExtension JavaScript, Chrome Native Messaging, Python 3 standard library, PowerShell, Node `node:test`, Python `unittest`.

## Global Constraints

- Preserve all official Zotero Connector behavior.
- Never focus or activate browser windows/tabs.
- Support browser foreground, background, covered, and minimized states.
- Report trigger acceptance separately from final Zotero persistence.
- V1 targets Windows Chrome and Edge; source remains MV2/Firefox-compatible.

---

### Task 1: Extension command core

**Files:**
- Create: `src/browserExt/scriptTrigger.js`
- Create: `script-trigger-tests/extension.test.js`

**Interfaces:**
- Consumes: `browser.runtime.connectNative`, `browser.tabs.query`, `browser.tabs.get`, `Zotero.initDeferred.promise`, `Zotero.Connector_Browser.onZoteroButtonElementClick(tab)`
- Produces: `ZoteroScriptTriggerCore.createScriptTrigger(options)`

- [ ] Write failing Node tests for `ping`, `save-active`, `save-tab`, invalid actions, and unsupported URLs.
- [ ] Run `node --test script-trigger-tests/extension.test.js` and verify failure because the module is missing.
- [ ] Implement the minimum command core and native-port adapter.
- [ ] Re-run the Node tests and verify all pass.

### Task 2: Native host and CLI

**Files:**
- Create: `native-host/native_protocol.py`
- Create: `native-host/zotero_script_trigger_host.py`
- Create: `native-host/zotero_script_trigger_cli.py`
- Create: `native-host/tests/test_native_protocol.py`
- Create: `native-host/tests/test_cli.py`

**Interfaces:**
- Consumes: browser native-messaging stdin/stdout and Windows `AF_PIPE`
- Produces: CLI commands `ping`, `save-active`, and `save-tab --tab-id N`

- [ ] Write failing Python tests for framing, malformed frames, config parsing, and request construction.
- [ ] Run `python3 -m unittest discover native-host/tests -v` and verify failure because modules are missing.
- [ ] Implement protocol, host broker, and CLI.
- [ ] Re-run Python tests and verify all pass.

### Task 3: Build integration and installer

**Files:**
- Modify: `src/browserExt/manifest-v3.json`
- Modify: `src/browserExt/background-worker.js`
- Create: `scripts/install-script-trigger.ps1`
- Create: `scripts/uninstall-script-trigger.ps1`
- Modify: `package.json`

**Interfaces:**
- Consumes: unpacked extension ID and Python 3.
- Produces: registered Chrome/Edge native host and packaged host executable.

- [ ] Add `nativeMessaging` permission and load `scriptTrigger.js` in the MV3 background.
- [ ] Add installer that packages the host with PyInstaller, generates a secret/config and native-host manifest, and registers an HKCU Chrome or Edge key.
- [ ] Add uninstall script and `npm run test:script-trigger`.
- [ ] Validate JSON and syntax.

### Task 4: Documentation and verification

**Files:**
- Create: `docs/SCRIPT_TRIGGER.md`

**Interfaces:**
- Produces: complete build, installation, command, troubleshooting, and manual-test instructions.

- [ ] Run Node and Python tests.
- [ ] Run syntax and JSON validation.
- [ ] Review code for focus-changing calls and official-save bypasses.
- [ ] Commit and publish the branch.
