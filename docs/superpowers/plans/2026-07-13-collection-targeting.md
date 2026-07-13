# Collection-Targeted Script Saves Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic saving into an existing Zotero collection selected by full path while preserving one-click Windows deployment.

**Architecture:** Extend the current script-trigger protocol rather than adding a desktop plugin. Resolve the flattened Zotero collection tree before saving, run the existing Connector page-save entrypoint, then reuse the existing `updateSession` message to move the completed save session into the resolved target. Package the result with a dedicated Chrome for Testing runtime so the user does not manually load an unpacked extension.

**Tech Stack:** JavaScript, Node built-in test runner, Python 3, argparse, PowerShell 5.1, Chrome for Testing, existing Zotero Connector messaging.

## Global Constraints

- Do not create collections automatically.
- Do not use the Zotero Web API.
- Missing or invalid collection targets must fail closed.
- Existing requests without collection options must preserve current behavior.
- `libraryTarget` defaults to `L1`.
- The normal Windows deployment path must be one double-click.
- The installer must not modify or close the user's normal Chrome installation.

---

### Task 1: Collection request contract

**Files:**
- Modify: `src/browserExt/scriptTrigger.js`
- Test: `script-trigger-tests/collection-target.test.js`

**Interfaces:**
- Consumes: optional request fields `collectionPath: string`, `libraryTarget?: string`
- Produces: resolved `collectionTarget` with `id`, `name`, `path`, `libraryTarget`, and `filesEditable`

- [x] Write tests for valid, missing, invalid, and unsupported collection targets.
- [x] Implement request validation and flattened collection-tree path resolution.
- [x] Verify ordinary requests retain the official toolbar-button path.

### Task 2: Save-session reassignment

**Files:**
- Modify: `src/browserExt/scriptTrigger.js`
- Test: `script-trigger-tests/collection-target.test.js`

**Interfaces:**
- Consumes: resolved collection target and prepared browser tab
- Produces: completed Connector save followed by `updateSession` for the same page session

- [x] Verify collection-targeted saves use the existing Connector entrypoints.
- [x] Send `updateSession` only after the page save completes.
- [x] Fail closed for uninjectable pages and unconfirmed translator saves.

### Task 3: CLI transport

**Files:**
- Modify: `native-host/zotero_script_trigger_cli.py`
- Test: `native-host/tests/test_cli_collection.py`

**Interfaces:**
- Consumes: `--collection` and `--library-target`
- Produces: UTF-8 JSON fields `collectionPath` and `libraryTarget`

- [x] Add collection options only to save subcommands.
- [x] Normalize collection path segments and validate library target syntax.
- [x] Cover parser and JSON request generation.

### Task 4: One-click Windows deployment

**Files:**
- Create: `packaging/0-一键安装并启动.bat`
- Create: `packaging/install-all.ps1`
- Create: `packaging/launch-automation-browser.ps1`
- Modify: `packaging/install-packaged.ps1`
- Modify: `packaging/uninstall-packaged.ps1`
- Test: `packaging/tests/one-click-install-regression.ps1`

**Interfaces:**
- Consumes: packaged native executables, built extension, bundled Chrome for Testing runtime
- Produces: `%LOCALAPPDATA%\ZoteroScriptTrigger`, persistent browser profile, shortcuts, and verified protocol-v3 runtime

- [x] Add a single normal installation entrypoint.
- [x] Copy all runtime files to a stable installed directory.
- [x] Generate a fresh authenticated named-pipe identifier on every install.
- [x] Create Desktop and Start Menu launch shortcuts.
- [x] Launch a dedicated browser profile with the installed extension.
- [x] Poll `ping` until protocol v3 and `save-to-collection` are confirmed.
- [x] Make reinstall stop only the dedicated bundled browser.
- [x] Make uninstall remove browser, profile, shortcuts, registry entries, and runtime files.

### Task 5: Release artifact and documentation

**Files:**
- Create: `.github/workflows/build-one-click-package.yml`
- Create: `docs/COLLECTION_TARGETING.md`
- Create: `docs/ONE_CLICK_DEPLOYMENT.md`
- Modify: `docs/SCRIPT_TRIGGER.md`
- Modify: `docs/AGENT_INTEGRATION.md`
- Modify: `packaging/使用说明.txt`

- [x] Build and test the extension before packaging.
- [x] Resolve and bundle stable Chrome for Testing win64 during packaging.
- [x] Package native host and CLI as standalone executables.
- [x] Verify Windows PowerShell 5.1 parsing and deployment-contract tests.
- [x] Publish `Zotero-Script-Trigger-OneClick-v3.zip` as a workflow artifact.
- [x] Document exact commands, paths, failure behavior, reinstallation, and uninstall behavior.

### Task 6: Final verification

- [ ] Confirm the protocol-v3 test workflow passes remotely.
- [ ] Confirm the one-click package workflow builds and uploads the Windows ZIP.
- [ ] Install the generated ZIP on a real Windows workstation.
- [ ] Confirm one double-click installs, launches, and passes protocol self-test.
- [ ] Confirm a real paper saves into an existing nested Zotero collection.
- [ ] Confirm reinstall preserves the dedicated browser profile and refreshes runtime files.
- [ ] Confirm uninstall removes only the dedicated automation environment.