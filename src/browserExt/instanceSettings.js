/*
 * Profile-local Linux Zotero instance settings.
 *
 * The same Connector build is installed into both dedicated Chrome profiles.
 * Each profile stores exactly one immutable routing identity in browser.storage.local.
 */
(function(root, factory) {
	const api = factory();
	if (typeof module === 'object' && module.exports) {
		module.exports = api;
	}
	if (root) {
		root.ZoteroScriptTriggerSettings = api;
	}
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
	'use strict';

	const STORAGE_KEYS = Object.freeze({
		profileId: 'scriptTrigger.profileId',
		connectorUrl: 'connector.url',
		nativeHostName: 'scriptTrigger.nativeHostName',
	});

	const ROUTES = Object.freeze({
		ZZH: Object.freeze({
			profileId: 'ZZH',
			connectorUrl: 'http://127.0.0.1:23119/',
			nativeHostName: 'org.zotero.script_trigger.zzh',
		}),
		NSY: Object.freeze({
			profileId: 'NSY',
			connectorUrl: 'http://127.0.0.1:23120/',
			nativeHostName: 'org.zotero.script_trigger.nsy',
		}),
	});

	class InstanceSettingsError extends Error {
		constructor(code, message) {
			super(message);
			this.name = 'InstanceSettingsError';
			this.code = code;
		}
	}

	function requireStorage(storage) {
		if (!storage || typeof storage.get !== 'function' || typeof storage.set !== 'function') {
			throw new InstanceSettingsError(
				'INSTANCE_STORAGE_UNAVAILABLE',
				'browser.storage.local compatible storage is required',
			);
		}
		return storage;
	}

	function normalizeProfileId(value) {
		const profileId = String(value || '').trim().toUpperCase();
		if (!Object.prototype.hasOwnProperty.call(ROUTES, profileId)) {
			throw new InstanceSettingsError(
				'INVALID_CONNECTOR_PROFILE',
				'Profile ID must be ZZH or NSY',
			);
		}
		return profileId;
	}

	function normalizeConnectorUrl(value) {
		let url;
		try {
			url = new URL(String(value || '').trim());
		}
		catch (_) {
			throw new InstanceSettingsError(
				'INVALID_CONNECTOR_URL',
				'Connector URL must be an HTTP URL on 127.0.0.1',
			);
		}
		if (url.protocol !== 'http:'
			|| url.hostname !== '127.0.0.1'
			|| !url.port
			|| (url.pathname && url.pathname !== '/')
			|| url.search
			|| url.hash
			|| url.username
			|| url.password) {
			throw new InstanceSettingsError(
				'INVALID_CONNECTOR_URL',
				'Connector URL must be http://127.0.0.1:<port>/ with no path, query, or fragment',
			);
		}
		return `http://127.0.0.1:${url.port}/`;
	}

	function normalizeInstanceSettings(value) {
		if (!value || typeof value !== 'object' || Array.isArray(value)) {
			throw new InstanceSettingsError(
				'CONNECTOR_INSTANCE_NOT_CONFIGURED',
				'Connector instance settings are required',
			);
		}
		const profileId = normalizeProfileId(value.profileId);
		const expected = ROUTES[profileId];
		const connectorUrl = normalizeConnectorUrl(value.connectorUrl);
		const nativeHostName = String(value.nativeHostName || '').trim();

		if (connectorUrl !== expected.connectorUrl) {
			throw new InstanceSettingsError(
				'BROWSER_ZOTERO_TARGET_MISMATCH',
				`${profileId} must use ${expected.connectorUrl}`,
			);
		}
		if (nativeHostName !== expected.nativeHostName) {
			throw new InstanceSettingsError(
				'BROWSER_ZOTERO_TARGET_MISMATCH',
				`${profileId} must use Native Host ${expected.nativeHostName}`,
			);
		}

		return Object.freeze({
			profileId,
			connectorUrl,
			nativeHostName,
		});
	}

	function presetForProfile(profileId) {
		const normalized = normalizeProfileId(profileId);
		return { ...ROUTES[normalized] };
	}

	async function readInstanceSettings(storage) {
		const local = requireStorage(storage);
		const values = await local.get(Object.values(STORAGE_KEYS));
		const candidate = {
			profileId: values[STORAGE_KEYS.profileId],
			connectorUrl: values[STORAGE_KEYS.connectorUrl],
			nativeHostName: values[STORAGE_KEYS.nativeHostName],
		};
		const present = Object.values(candidate).filter(value => value !== undefined && value !== null && value !== '');
		if (present.length === 0) return null;
		return normalizeInstanceSettings(candidate);
	}

	async function applyInstanceSettings(storage, value) {
		const local = requireStorage(storage);
		const settings = normalizeInstanceSettings(value);
		await local.set({
			[STORAGE_KEYS.profileId]: settings.profileId,
			[STORAGE_KEYS.connectorUrl]: settings.connectorUrl,
			[STORAGE_KEYS.nativeHostName]: settings.nativeHostName,
		});
		return settings;
	}

	return {
		STORAGE_KEYS,
		ROUTES,
		InstanceSettingsError,
		applyInstanceSettings,
		normalizeInstanceSettings,
		presetForProfile,
		readInstanceSettings,
	};
});
