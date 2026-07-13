# Zotero Connectors

[![Build Status](https://travis-ci.org/zotero/zotero-connectors.svg?branch=master)](https://travis-ci.org/zotero/zotero-connectors)

## ArchitectureWorld script-trigger fork

The `feature/script-trigger` line preserves the official Zotero Connector save path and adds a Windows-local command interface for external agents and scripts. The collection-targeting upgrade is developed on `feature/script-trigger-collection-target`.

Key properties:

- Chrome may be foreground, background, covered, or minimized.
- No browser focus, tab activation, keyboard simulation, or mouse simulation is used.
- Protocol v3 supports deterministic exact-URL targeting through `save-url --url`.
- Save commands can resolve an existing Zotero collection by full path with `--collection` and fail closed when it is missing.
- The packaged CLI is installed at `%LOCALAPPDATA%\ZoteroScriptTrigger\zotero_script_trigger_cli.exe`.
- `triggered=true` means the official Connector action accepted the request; `collectionApplied=true` additionally confirms that the save session was reassigned to the resolved collection.

User installation and commands: `docs/SCRIPT_TRIGGER.md`  
Agent integration contract: `docs/AGENT_INTEGRATION.md`  
Collection-targeting contract: `docs/COLLECTION_TARGETING.md`

## Building

1. `git clone --recursive https://github.com/zotero/zotero-connectors.git`
1. `cd zotero-connectors`
1. `npm install`
1. `./build.sh -d`

The connectors are built in `build/`.

## Running from the build directory

### Chrome

1. Go to chrome://extensions/
1. Enable "Developer Mode".
1. Click "Load unpacked extension…" and select the `build/manifestv3` directory.

### Firefox

1. Go to about:debugging
1. Click "Load Temporary Add-on" and select the `build/firefox/manifest.json` file.

### Safari

See https://github.com/zotero/safari-app-extension 

## Automatic rebuilding

1. `cd` to project root
1. `npm install`
1. `build.sh -d`
1. `gulp watch`

As files are changed, the connectors will be rebuilt automatically. You will need to manually reload the extension
in the browser being developed for.

## Requirements for packaging extensions from the command line

* Copy `config.sh-sample` to `config.sh` and modify as necessary

# Developing

An overview of the Zotero Connector architecture.

## Technologies

##### Chrome/Firefox Browser Extension Framework

The extension uses the WebExtension API cross-browser technology. See [Chrome Extension docs](https://developer.chrome.com/extensions)
and [Firefox Extension docs](https://developer.mozilla.org/en-US/Add-ons/WebExtensions/Content_scripts) for more information.

##### Safari Extension Framework

For Safari specifics see https://github.com/zotero/safari-app-extension

##### Zotero Translator Framework

The Connectors use the [Zotero translate architecture](https://github.com/zotero/translate), to support page translation.
A basic understanding of how translation works is highly useful in understanding the codebase.

## Components