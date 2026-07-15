const test = require('node:test');
const assert = require('node:assert/strict');

const { createScriptTrigger } = require('../src/browserExt/scriptTrigger.js');

function makeHarness({ instanceIdentity, autoConnect = false } = {}) {
  let connectedHost = null;
  const port = {
    onMessage: { addListener() {} },
    onDisconnect: { addListener() {} },
    postMessage() {},
    disconnect() {},
  };
  const browserAPI = {
    runtime: {
      id: 'instance-extension',
      getManifest: () => ({ version: '4.0.0' }),
      connectNative(host) {
        connectedHost = host;
        return port;
      },
    },
    tabs: { query: async () => [], get: async () => null },
  };
  const zotero = {
    initDeferred: { promise: Promise.resolve() },
    Connector_Browser: { onZoteroButtonElementClick: async () => {} },
    debug() {},
    logError() {},
  };
  const trigger = createScriptTrigger({
    browserAPI,
    zotero,
    autoConnect,
    instanceIdentity,
    hostName: instanceIdentity && instanceIdentity.nativeHostName,
  });
  return { trigger, getConnectedHost: () => connectedHost };
}

test('legacy trigger keeps protocol v3 without instance identity', async () => {
  const { trigger } = makeHarness();
  const result = await trigger.handleRequest({ id: 'legacy', action: 'ping' });
  assert.equal(result.protocolVersion, 3);
  assert.equal(result.capabilities.includes('instance-routing'), false);
  assert.equal('profileId' in result, false);
});

test('routed trigger reports immutable protocol v4 identity', async () => {
  const identity = {
    profileId: 'NSY',
    instanceId: 'NSY',
    connectorUrl: 'http://127.0.0.1:23120/',
    nativeHostName: 'org.zotero.script_trigger.nsy',
  };
  const { trigger } = makeHarness({ instanceIdentity: identity });
  const result = await trigger.handleRequest({
    id: 'routed',
    action: 'ping',
    profileId: 'ZZH',
    connectorUrl: 'http://127.0.0.1:23119/',
  });

  assert.equal(result.protocolVersion, 4);
  assert.equal(result.capabilities.includes('instance-routing'), true);
  assert.equal(result.profileId, 'NSY');
  assert.equal(result.instanceId, 'NSY');
  assert.equal(result.connectorUrl, 'http://127.0.0.1:23120/');
  assert.equal(result.nativeHostName, 'org.zotero.script_trigger.nsy');
});

test('routed trigger connects only to the configured native host', () => {
  const identity = {
    profileId: 'ZZH',
    instanceId: 'ZZH',
    connectorUrl: 'http://127.0.0.1:23119/',
    nativeHostName: 'org.zotero.script_trigger.zzh',
  };
  const { getConnectedHost } = makeHarness({ instanceIdentity: identity, autoConnect: true });
  assert.equal(getConnectedHost(), 'org.zotero.script_trigger.zzh');
});

test('incomplete routed identity fails before connecting', () => {
  assert.throws(() => makeHarness({
    instanceIdentity: {
      profileId: 'NSY',
      connectorUrl: 'http://127.0.0.1:23120/',
    },
    autoConnect: true,
  }), /nativeHostName|instance/i);
});
