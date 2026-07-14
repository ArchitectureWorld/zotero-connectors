(function() {
	'use strict';

	const settingsAPI = globalThis.ZoteroScriptTriggerSettings;
	const profile = document.getElementById('profileId');
	const connectorUrl = document.getElementById('connectorUrl');
	const nativeHostName = document.getElementById('nativeHostName');
	const apply = document.getElementById('apply');
	const status = document.getElementById('status');

	function show(message, kind = '') {
		status.textContent = message;
		status.dataset.kind = kind;
	}

	function renderPreset(profileId) {
		const preset = settingsAPI.presetForProfile(profileId);
		profile.value = preset.profileId;
		connectorUrl.value = preset.connectorUrl;
		nativeHostName.value = preset.nativeHostName;
		return preset;
	}

	async function initialize() {
		if (!settingsAPI || !browser || !browser.storage || !browser.storage.local) {
			throw new Error('Connector 实例设置接口不可用');
		}
		const requested = new URLSearchParams(location.search).get('instance');
		let current = null;
		try {
			current = await settingsAPI.readInstanceSettings(browser.storage.local);
		}
		catch (error) {
			show(`现有设置无效：${error.message}`, 'error');
		}
		if (requested === 'ZZH' || requested === 'NSY') {
			renderPreset(requested);
		}
		else if (current) {
			renderPreset(current.profileId);
		}
		else {
			renderPreset('ZZH');
		}
	}

	profile.addEventListener('change', () => {
		renderPreset(profile.value);
		show('尚未应用', 'pending');
	});

	apply.addEventListener('click', async () => {
		apply.disabled = true;
		try {
			const preset = renderPreset(profile.value);
			await settingsAPI.applyInstanceSettings(browser.storage.local, preset);
			show(`已绑定 ${preset.profileId} → ${preset.connectorUrl}，正在重载 Connector…`, 'success');
			setTimeout(() => browser.runtime.reload(), 250);
		}
		catch (error) {
			show(error.message || String(error), 'error');
			apply.disabled = false;
		}
	});

	initialize().catch(error => {
		show(error.message || String(error), 'error');
		apply.disabled = true;
	});
})();
