const test = require('node:test');
const assert = require('node:assert/strict');

const { createScriptTrigger } = require('../src/browserExt/scriptTrigger.js');

function makeHarness({ targets, tabInfo } = {}) {
  const tab = {
    id: 91,
    windowId: 11,
    active: false,
    status: 'complete',
    url: 'https://example.org/paper',
    title: 'Paper',
  };
  const calls = { connector: [], translator: [], updates: [], clicks: [] };
  const browserAPI = {
    runtime: {
      id: 'test-extension-id',
      getManifest: () => ({ version: '3.0.0' }),
      connectNative: () => { throw new Error('not used'); },
    },
    tabs: {
      query: async () => [tab],
      get: async () => tab,
    },
  };
  const zotero = {
    initDeferred: { promise: Promise.resolve() },
    Connector: {
      callMethod: async (method, data) => {
        calls.connector.push({ method, data });
        return {
          libraryID: 1,
          libraryName: 'My Library',
          targets: targets || [
            { id: 'L1', name: 'My Library', level: 0, filesEditable: true },
            { id: 'C10', name: '自动文献收集', level: 1, filesEditable: true },
            { id: 'C11', name: '建筑数字化技术', level: 2, filesEditable: true },
            { id: 'C12', name: '第一轮广义收集', level: 3, filesEditable: true },
          ],
        };
      },
      isOnline: true,
      prefs: { automaticSnapshots: true },
    },
    Prefs: { get: () => true },
    Messaging: {
      sendMessage: async (name, data, targetTab, frameId) => {
        calls.updates.push({ name, data, tab: targetTab, frameId });
        return true;
      },
    },
    Connector_Browser: {
      getTabInfo: () => tabInfo || {
        url: tab.url,
        translators: [{ translatorID: 'translator-1' }],
        isPDF: false,
        uninjectable: false,
      },
      saveWithTranslator: async (targetTab, index, options) => {
        calls.translator.push({ tab: targetTab, index, options });
        return [{ id: 1, title: 'Paper' }];
      },
      saveAsWebpage: async () => ({ ok: true }),
      onZoteroButtonElementClick: async (targetTab) => calls.clicks.push(targetTab),
    },
    debug: () => {},
    logError: () => {},
  };
  const trigger = createScriptTrigger({ browserAPI, zotero, autoConnect: false });
  return { trigger, calls, tab };
}

test('save-url resolves a full collection path and updates the completed save session', async () => {
  const { trigger, calls, tab } = makeHarness();

  const result = await trigger.handleRequest({
    id: 'collection-1',
    action: 'save-url',
    url: tab.url,
    collectionPath: '自动文献收集/建筑数字化技术/第一轮广义收集',
  });

  assert.equal(result.success, true);
  assert.equal(result.collectionApplied, true);
  assert.deepEqual(result.collectionTarget, {
    id: 'C12',
    name: '第一轮广义收集',
    path: '自动文献收集/建筑数字化技术/第一轮广义收集',
    libraryTarget: 'L1',
    filesEditable: true,
  });
  assert.deepEqual(calls.connector, [{
    method: 'getSelectedCollection',
    data: { switchToReadableLibrary: true },
  }]);
  assert.equal(calls.clicks.length, 0);
  assert.equal(calls.translator.length, 1);
  assert.deepEqual(calls.translator[0].options, { fallbackOnFailure: true });
  assert.deepEqual(calls.updates, [{
    name: 'updateSession',
    data: {
      target: 'C12',
      tags: [],
      note: '',
      resaveAttachments: false,
      removeAttachments: false,
    },
    tab,
    frameId: null,
  }]);
});

test('collection targeting fails closed when the path does not exist', async () => {
  const { trigger, calls, tab } = makeHarness();

  const result = await trigger.handleRequest({
    id: 'collection-missing',
    action: 'save-url',
    url: tab.url,
    collectionPath: '不存在/子集合',
  });

  assert.equal(result.success, false);
  assert.equal(result.error.code, 'TARGET_COLLECTION_NOT_FOUND');
  assert.equal(calls.translator.length, 0);
  assert.equal(calls.clicks.length, 0);
  assert.equal(calls.updates.length, 0);
});

test('collection targeting rejects empty path segments before lookup', async () => {
  const { trigger, calls, tab } = makeHarness();

  const result = await trigger.handleRequest({
    id: 'collection-invalid',
    action: 'save-url',
    url: tab.url,
    collectionPath: '自动文献收集//第一轮广义收集',
  });

  assert.equal(result.success, false);
  assert.equal(result.error.code, 'INVALID_COLLECTION_PATH');
  assert.equal(calls.connector.length, 0);
  assert.equal(calls.translator.length, 0);
});

test('collection targeting rejects uninjectable pages instead of saving to the wrong place', async () => {
  const { trigger, calls, tab } = makeHarness({
    tabInfo: {
      url: 'https://example.org/paper',
      translators: [],
      isPDF: false,
      uninjectable: true,
    },
  });

  const result = await trigger.handleRequest({
    id: 'collection-uninjectable',
    action: 'save-url',
    url: tab.url,
    collectionPath: '自动文献收集/建筑数字化技术/第一轮广义收集',
  });

  assert.equal(result.success, false);
  assert.equal(result.error.code, 'COLLECTION_TARGET_UNSUPPORTED');
  assert.equal(calls.updates.length, 0);
});
