/*
 * External script trigger for Zotero Connector.
 *
 * This module intentionally does not implement saving itself. It resolves a
 * target tab and calls Zotero.Connector_Browser.onZoteroButtonElementClick(),
 * which is the same entrypoint used by the official toolbar button.
 */
(function(root, factory) {
	const api = factory();
	if (typeof module === 'object' && module.exports) {
		module.exports = api;
	}
	if (root) {
		root.ZoteroScriptTriggerCore = api;
	}
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
	'use strict';

	const DEFAULT_HOST_NAME = 'org.zotero.script_trigger';
	const DEFAULT_RECONNECT_DELAY = 5000;
	const MAX_RECONNECT_DELAY = 60000;
	const SUPPORTED_ACTIONS = new Set(['ping', 'save-active', 'save-tab']);

	class ScriptTriggerError extends Error {
		constructor(code, message) {
			super(message);
			this.name = 'ScriptTriggerError';
			this.code = code;
		}
	}

	function makeErrorResponse(request, error) {
		return {
			id: request && request.id,
			success: false,
			action: request && request.action,
			error: {
				code: error && error.code ? error.code : 'INTERNAL_ERROR',
				message: error && error.message ? error.message : String(error),
			},
		};
	}

	function validateRequest(request) {
		if (!request || typeof request !== 'object' || Array.isArray(request)) {
			throw new ScriptTriggerError('INVALID_REQUEST', 'Request must be a JSON object');
		}
		if (typeof request.action !== 'string' || !SUPPORTED_ACTIONS.has(request.action)) {
			throw new ScriptTriggerError('UNKNOWN_ACTION', `Unsupported action: ${request.action}`);
		}
		if (request.action === 'save-tab'
			&& (!Number.isInteger(request.tabId) || request.tabId < 0)) {
			throw new ScriptTriggerError('INVALID_TAB_ID', 'save-tab requires a non-negative integer tabId');
		}
	}

	function validateTargetTab(tab) {
		if (!tab || !Number.isInteger(tab.id)) {
			throw new ScriptTriggerError('TAB_NOT_FOUND', 'No matching browser tab was found');
		}
		const url = tab.url || tab.pendingUrl || '';
		if (!/^https?:\/\//i.test(url)) {
			throw new ScriptTriggerError('UNSUPPORTED_URL', `Cannot save unsupported URL: ${url || '(empty)'}`);
		}
		return tab;
	}

	function createScriptTrigger(options) {
		options = options || {};
		const browserAPI = options.browserAPI;
		const zotero = options.zotero;
		const hostName = options.hostName || DEFAULT_HOST_NAME;
		const schedule = options.schedule || ((fn, delay) => setTimeout(fn, delay));
		const autoConnect = options.autoConnect !== false;

		if (!browserAPI || !browserAPI.runtime || !browserAPI.tabs) {
			throw new Error('browserAPI with runtime and tabs is required');
		}
		if (!zotero || !zotero.initDeferred || !zotero.Connector_Browser) {
			throw new Error('Initialized Zotero background API is required');
		}

		let port = null;
		let reconnectDelay = DEFAULT_RECONNECT_DELAY;
		let reconnectScheduled = false;
		let stopped = false;

		async function resolveTab(request) {
			if (request.action === 'save-tab') {
				try {
					return validateTargetTab(await browserAPI.tabs.get(request.tabId));
				} catch (error) {
					if (error instanceof ScriptTriggerError) throw error;
					throw new ScriptTriggerError('TAB_NOT_FOUND', error.message || `No tab with id ${request.tabId}`);
				}
			}

			const tabs = await browserAPI.tabs.query({
				active: true,
				lastFocusedWindow: true,
			});
			return validateTargetTab(tabs && tabs[0]);
		}

		async function handleRequest(request) {
			try {
				validateRequest(request);
				await zotero.initDeferred.promise;

				if (request.action === 'ping') {
					const manifest = browserAPI.runtime.getManifest
						? browserAPI.runtime.getManifest()
						: {};
					return {
						id: request.id,
						success: true,
						action: request.action,
						extensionId: browserAPI.runtime.id,
						extensionVersion: manifest.version,
					};
				}

				const tab = await resolveTab(request);
				await zotero.Connector_Browser.onZoteroButtonElementClick(tab);
				return {
					id: request.id,
					success: true,
					action: request.action,
					triggered: true,
					tabId: tab.id,
					windowId: tab.windowId,
					title: tab.title || '',
					url: tab.url || tab.pendingUrl || '',
				};
			} catch (error) {
				if (zotero.logError && !(error instanceof ScriptTriggerError)) {
					zotero.logError(error);
				}
				return makeErrorResponse(request, error);
			}
		}

		function scheduleReconnect() {
			if (stopped || reconnectScheduled) return;
			reconnectScheduled = true;
			const delay = reconnectDelay;
			reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY);
			schedule(() => {
				reconnectScheduled = false;
				connect();
			}, delay);
		}

		function connect() {
			if (stopped || port) return;
			try {
				port = browserAPI.runtime.connectNative(hostName);
				reconnectDelay = DEFAULT_RECONNECT_DELAY;
				port.onMessage.addListener(async (request) => {
					const response = await handleRequest(request);
					try {
						port && port.postMessage(response);
					} catch (error) {
						if (zotero.debug) zotero.debug(`Script trigger response failed: ${error.message}`);
					}
				});
				port.onDisconnect.addListener(() => {
					const runtimeError = browserAPI.runtime.lastError;
					if (runtimeError && zotero.debug) {
						zotero.debug(`Script trigger native host disconnected: ${runtimeError.message}`);
					}
					port = null;
					scheduleReconnect();
				});
			} catch (error) {
				port = null;
				if (zotero.debug) zotero.debug(`Script trigger native host unavailable: ${error.message}`);
				scheduleReconnect();
			}
		}

		function stop() {
			stopped = true;
			if (port) {
				try { port.disconnect(); } catch (_) {}
				port = null;
			}
		}

		const api = {
			connect,
			handleRequest,
			resolveTab,
			stop,
		};

		if (autoConnect) {
			connect();
		}
		return api;
	}

	return {
		DEFAULT_HOST_NAME,
		ScriptTriggerError,
		createScriptTrigger,
	};
});

// In the extension background context this file is loaded before background.js.
// Defer initialization until the current script turn finishes so background.js
// can create Zotero.Connector_Browser first.
if (typeof browser !== 'undefined' && typeof Zotero !== 'undefined') {
	setTimeout(() => {
		try {
			if (!Zotero.Connector_Browser || Zotero.ScriptTrigger) return;
			Zotero.ScriptTrigger = ZoteroScriptTriggerCore.createScriptTrigger({
				browserAPI: browser,
				zotero: Zotero,
			});
		} catch (error) {
			if (Zotero.logError) Zotero.logError(error);
		}
	}, 0);
}
