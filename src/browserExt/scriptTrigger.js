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
	const DEFAULT_POLL_INTERVAL = 100;
	const DEFAULT_PAGE_READY_TIMEOUT = 15000;
	const DEFAULT_TRANSLATOR_READY_TIMEOUT = 10000;
	const PROTOCOL_VERSION = 2;
	const CAPABILITIES = Object.freeze([
		'list-tabs',
		'save-active',
		'save-tab',
		'save-url',
		'save-title',
	]);
	const SUPPORTED_ACTIONS = new Set(['ping', ...CAPABILITIES]);

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

	function requireNonEmptyString(value, code, message) {
		if (typeof value !== 'string' || !value.trim()) {
			throw new ScriptTriggerError(code, message);
		}
		return value.trim();
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
		if (request.action === 'save-url') {
			const hasExact = typeof request.url === 'string' && !!request.url.trim();
			const hasContains = typeof request.urlContains === 'string' && !!request.urlContains.trim();
			if (hasExact === hasContains) {
				throw new ScriptTriggerError(
					'INVALID_URL_SELECTOR',
					'save-url requires exactly one non-empty url or urlContains selector',
				);
			}
		}
		if (request.action === 'save-title') {
			requireNonEmptyString(
				request.titleContains,
				'INVALID_TITLE_SELECTOR',
				'save-title requires a non-empty titleContains selector',
			);
		}
	}

	function isSaveableTab(tab) {
		const url = tab && (tab.url || tab.pendingUrl || '');
		return !!tab && Number.isInteger(tab.id) && /^https?:\/\//i.test(url);
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

	function publicTab(tab) {
		return {
			id: tab.id,
			windowId: tab.windowId,
			active: !!tab.active,
			discarded: !!tab.discarded,
			status: tab.status || '',
			title: tab.title || '',
			url: tab.url || tab.pendingUrl || '',
		};
	}

	function selectOneTab(tabs, predicate, selectorDescription) {
		const matches = (tabs || []).filter(isSaveableTab).filter(predicate);
		if (matches.length === 0) {
			throw new ScriptTriggerError('TAB_NOT_FOUND', `No browser tab matched ${selectorDescription}`);
		}
		if (matches.length > 1) {
			throw new ScriptTriggerError(
				'TAB_AMBIGUOUS',
				`Multiple browser tabs matched ${selectorDescription}; use an exact URL or tab ID`,
			);
		}
		return matches[0];
	}

	function createScriptTrigger(options) {
		options = options || {};
		const browserAPI = options.browserAPI;
		const zotero = options.zotero;
		const hostName = options.hostName || DEFAULT_HOST_NAME;
		const schedule = options.schedule || ((fn, timeout) => setTimeout(fn, timeout));
		const autoConnect = options.autoConnect !== false;
		const now = options.now || (() => Date.now());
		const delay = options.delay || ((milliseconds) => {
			if (zotero.Promise && typeof zotero.Promise.delay === 'function') {
				return zotero.Promise.delay(milliseconds);
			}
			return new Promise(resolve => setTimeout(resolve, milliseconds));
		});
		const pollInterval = options.pollInterval || DEFAULT_POLL_INTERVAL;
		const pageReadyTimeout = options.pageReadyTimeout || DEFAULT_PAGE_READY_TIMEOUT;
		const translatorReadyTimeout = options.translatorReadyTimeout || DEFAULT_TRANSLATOR_READY_TIMEOUT;

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

		async function waitUntil(check, timeout) {
			const deadline = now() + timeout;
			while (true) {
				const value = await check();
				if (value) return value;
				if (now() >= deadline) return null;
				await delay(pollInterval);
			}
		}

		async function getTab(tabId) {
			try {
				return validateTargetTab(await browserAPI.tabs.get(tabId));
			} catch (error) {
				if (error instanceof ScriptTriggerError) throw error;
				throw new ScriptTriggerError('TAB_NOT_FOUND', error.message || `No tab with id ${tabId}`);
			}
		}

		async function waitForPageReady(tab) {
			let current = validateTargetTab(tab);
			const needsReload = !!current.discarded;
			const needsWait = needsReload || (current.status && current.status !== 'complete');

			if (needsReload) {
				if (typeof browserAPI.tabs.reload !== 'function') {
					throw new ScriptTriggerError('TAB_RELOAD_UNAVAILABLE', 'Browser tab reload API is unavailable');
				}
				await browserAPI.tabs.reload(current.id);
			}

			if (!needsWait) return current;

			const ready = await waitUntil(async () => {
				const refreshed = await getTab(current.id);
				if (refreshed.discarded) return null;
				if (refreshed.status && refreshed.status !== 'complete') return null;
				return refreshed;
			}, pageReadyTimeout);

			if (!ready) {
				throw new ScriptTriggerError(
					'TAB_LOAD_TIMEOUT',
					`Timed out waiting for tab ${current.id} to finish loading`,
				);
			}
			return ready;
		}

		async function waitForTranslatorDetection(tab) {
			if (typeof zotero.Connector_Browser.getTabInfo !== 'function') return true;
			const expectedURL = tab.url || tab.pendingUrl || '';
			const detected = await waitUntil(() => {
				const tabInfo = zotero.Connector_Browser.getTabInfo(tab.id);
				if (!tabInfo) return null;
				if (tabInfo.url && tabInfo.url !== expectedURL) return null;
				if (tabInfo.translators !== null || tabInfo.isPDF || tabInfo.uninjectable) {
					return true;
				}
				return null;
			}, translatorReadyTimeout);
			if (!detected && zotero.debug) {
				zotero.debug(`Script trigger: translator detection timed out for ${expectedURL}`);
			}
			return !!detected;
		}

		async function prepareTargetTab(tab) {
			const readyTab = await waitForPageReady(tab);
			const translatorReady = await waitForTranslatorDetection(readyTab);
			return { tab: readyTab, translatorReady };
		}

		async function listTabs() {
			const tabs = await browserAPI.tabs.query({});
			return (tabs || []).filter(isSaveableTab).map(publicTab);
		}

		async function resolveTab(request) {
			if (request.action === 'save-tab') {
				return getTab(request.tabId);
			}

			if (request.action === 'save-url') {
				const tabs = await browserAPI.tabs.query({});
				if (typeof request.url === 'string' && request.url.trim()) {
					const exactURL = request.url.trim();
					return selectOneTab(
						tabs,
						tab => (tab.url || tab.pendingUrl || '') === exactURL,
						`exact URL ${exactURL}`,
					);
				}
				const fragment = request.urlContains.trim();
				return selectOneTab(
					tabs,
					tab => (tab.url || tab.pendingUrl || '').includes(fragment),
					`URL fragment ${fragment}`,
				);
			}

			if (request.action === 'save-title') {
				const tabs = await browserAPI.tabs.query({});
				const fragment = request.titleContains.trim().toLocaleLowerCase();
				return selectOneTab(
					tabs,
					tab => (tab.title || '').toLocaleLowerCase().includes(fragment),
					`title fragment ${request.titleContains.trim()}`,
				);
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
						protocolVersion: PROTOCOL_VERSION,
						capabilities: Array.from(CAPABILITIES),
					};
				}

				if (request.action === 'list-tabs') {
					return {
						id: request.id,
						success: true,
						action: request.action,
						tabs: await listTabs(),
					};
				}

				const resolvedTab = await resolveTab(request);
				const prepared = await prepareTargetTab(resolvedTab);
				const tab = prepared.tab;
				await zotero.Connector_Browser.onZoteroButtonElementClick(tab);
				return {
					id: request.id,
					success: true,
					action: request.action,
					triggered: true,
					translatorReady: prepared.translatorReady,
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
			const timeout = reconnectDelay;
			reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY);
			schedule(() => {
				reconnectScheduled = false;
				connect();
			}, timeout);
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
			listTabs,
			prepareTargetTab,
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
		PROTOCOL_VERSION,
		CAPABILITIES,
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
