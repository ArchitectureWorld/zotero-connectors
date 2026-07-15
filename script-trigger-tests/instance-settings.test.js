const test = require('node:test');
const assert = require('node:assert/strict');

const {
  applyInstanceSettings,
  normalizeInstanceSettings,
  readInstanceSettings,
} = require('../src/browserExt/instanceSettings.js');

function makeStorage(initial = {}) {
  const values = { ...initial };
  const calls = [];
  return {
    values,
    calls,
    async get(keys) {
      if (keys == null) return { ...values };
      const result = {};
      for (const key of Array.isArray(keys) ? keys : [keys]) {
        if (Object.prototype.hasOwnProperty.call(values, key)) result[key] = values[key];
      }
      return result;
    },
    async set(next) {
      calls.push({ ...next });
      Object.assign(values, next);
    },
  };
}

test('normalizes the fixed ZZH routing identity', () => {
  assert.deepEqual(normalizeInstanceSettings({
    profileId: 'ZZH',
    connectorUrl: 'http://127.0.0.1:23119',
    nativeHostName: 'org.zotero.script_trigger.zzh',
  }), {
    profileId: 'ZZH',
    connectorUrl: 'http://127.0.0.1:23119/',
    nativeHostName: 'org.zotero.script_trigger.zzh',
  });
});

test('normalizes the fixed NSY routing identity', () => {
  assert.deepEqual(normalizeInstanceSettings({
    profileId: 'NSY',
    connectorUrl: 'http://127.0.0.1:23120/',
    nativeHostName: 'org.zotero.script_trigger.nsy',
  }), {
    profileId: 'NSY',
    connectorUrl: 'http://127.0.0.1:23120/',
    nativeHostName: 'org.zotero.script_trigger.nsy',
  });
});

test('rejects incomplete or cross-wired settings', () => {
  assert.throws(() => normalizeInstanceSettings({ profileId: 'ZZH' }), /connector/i);
  assert.throws(() => normalizeInstanceSettings({
    profileId: 'NSY',
    connectorUrl: 'http://127.0.0.1:23119/',
    nativeHostName: 'org.zotero.script_trigger.nsy',
  }), /23120|NSY/i);
  assert.throws(() => normalizeInstanceSettings({
    profileId: 'ZZH',
    connectorUrl: 'http://localhost:23119/',
    nativeHostName: 'org.zotero.script_trigger.zzh',
  }), /127\.0\.0\.1/i);
});

test('persists all bound fields in one storage write', async () => {
  const storage = makeStorage();
  const settings = await applyInstanceSettings(storage, {
    profileId: 'NSY',
    connectorUrl: 'http://127.0.0.1:23120/',
    nativeHostName: 'org.zotero.script_trigger.nsy',
  });

  assert.deepEqual(settings, {
    profileId: 'NSY',
    connectorUrl: 'http://127.0.0.1:23120/',
    nativeHostName: 'org.zotero.script_trigger.nsy',
  });
  assert.deepEqual(storage.calls, [{
    'scriptTrigger.profileId': 'NSY',
    'connector.url': 'http://127.0.0.1:23120/',
    'scriptTrigger.nativeHostName': 'org.zotero.script_trigger.nsy',
  }]);
  assert.deepEqual(await readInstanceSettings(storage), settings);
});
