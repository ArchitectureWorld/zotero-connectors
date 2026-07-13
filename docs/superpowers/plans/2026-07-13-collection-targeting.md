# Collection-Targeted Script Saves Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic saving into an existing Zotero collection selected by full path.

**Architecture:** Extend the current script-trigger protocol rather than adding a desktop plugin. Resolve the flattened Zotero collection tree before saving, run the existing Connector page-save entrypoint, then reuse the existing `updateSession` message to move the completed save session into the resolved target.

**Tech Stack:** JavaScript, Node built-in test runner, Python 3, argparse, existing Zotero Connector messaging.

## Global Constraints

- Do not create collections automatically.
- Do not use the Zotero Web API.
- Missing or invalid collection targets must fail closed.
- Existing requests without collection options must preserve current behavior.
- `libraryTarget` defaults to `L1`.

---

### Task 1: Collection request contract

**Files:**
- Modify: `src/browserExt/scriptTrigger.js`
- Test: `script-trigger-tests/collection-target.test.js`

**Interfaces:**
- Consumes: optional request fields `collectionPath: string`, `libraryTarget?: string`
- Produces: resolved `collectionTarget` with `id`, `name`, `path`, `libraryTarget`, and `filesEditable`

- [ ] Write failing tests for valid, missing, invalid, and unsupported collection targets.
- [ ] Run `node --test script-trigger-tests/collection-target.test.js` and confirm failures are caused by missing behavior.
- [ ] Implement request validation and flattened collection-tree path resolution.
- [ ] Re-run the focused Node test and confirm it passes.

### Task 2: Save-session reassignment

**Files:**
- Modify: `src/browserExt/scriptTrigger.js`
- Test: `script-trigger-tests/collection-target.test.js`

**Interfaces:**
- Consumes: resolved collection target and prepared browser tab
- Produces: completed Connector save followed by `updateSession` for the same page session

- [ ] Add a failing assertion that collection-targeted saves use `saveWithTranslator` and then send `updateSession`.
- [ ] Implement collection-aware save routing and fail closed for uninjectable pages.
- [ ] Verify that ordinary saves still call `onZoteroButtonElementClick` unchanged.
- [ ] Run all `script-trigger-tests/*.test.js`.

### Task 3: CLI transport

**Files:**
- Modify: `native-host/zotero_script_trigger_cli.py`
- Test: `native-host/tests/test_cli_collection.py`

**Interfaces:**
- Consumes: `--collection` and `--library-target`
- Produces: UTF-8 JSON fields `collectionPath` and `libraryTarget`

- [ ] Write failing parser and request-generation tests.
- [ ] Add collection options only to save subcommands.
- [ ] Normalize collection path segments and validate library target syntax.
- [ ] Run `python -m unittest discover native-host/tests -v`.

### Task 4: Protocol documentation and regression verification

**Files:**
- Modify: `README.md`
- Create: `docs/COLLECTION_TARGETING.md`

- [ ] Document protocol version 3, examples, response fields, and failure behavior.
- [ ] Run `node --test script-trigger-tests/*.test.js`.
- [ ] Run `python -m unittest discover native-host/tests -v`.
- [ ] Confirm the branch contains only the scoped collection-targeting changes.