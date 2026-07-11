const test = require('node:test');
const assert = require('node:assert/strict');

const { createScriptTrigger } = require('../src/browserExt/scriptTrigger.js');

function makeHarness({ activeTabs = [], tabsById = {} } = {}) {
  const calls = {
    queries: [],
    gets: [],
    saves: [],
    focusedWindows: 0,
    activatedTabs: 0,
  };

  const browserAPI = {
    runtime: {
      id: 'test-extension-id',
      getManifest: () => ({ version: '1.2.3' }),
      connectNative: () => { throw new Error('not used in command tests'); },
    },
    tabs: {
      query: async (query) => {
        calls.queries.push(query);
        return activeTabs;
      },
      get: async (tabId) => {
        calls.gets.push(tabId);
        if (!tabsById[tabId]) throw new Error(`No tab with id: ${tabId}`);
        return tabsById[tabId];
      },
      update: async () => {
        calls.activatedTabs += 1;
      },
    },
    windows: {
      update: async () => {
        calls.focusedWindows += 1;
      },
    },
  };

  const zotero = {
    initDeferred: { promise: Promise.resolve() },
    Connector_Browser: {
      onZoteroButtonElementClick: async (tab) => {
        calls.saves.push(tab);
      },
    },
    debug: () => {},
    logError: () => {},
  };

  const trigger = createScriptTrigger({
    browserAPI,
    zotero,
    autoConnect: false,
  });

  return { trigger, calls };
}

test('ping returns extension identity without selecting a tab', async () => {
  const { trigger, calls } = makeHarness();

  const result = await trigger.handleRequest({ id: 'p1', action: 'ping' });

  assert.deepEqual(result, {
    id: 'p1',
    success: true,
    action: 'ping',
    extensionId: 'test-extension-id',
    extensionVersion: '1.2.3',
  });
  assert.equal(calls.queries.length, 0);
  assert.equal(calls.saves.length, 0);
});

test('save-active uses the active tab in the last-focused browser window', async () => {
  const tab = { id: 41, windowId: 7, active: true, url: 'https://example.com/paper', title: 'Paper' };
  const { trigger, calls } = makeHarness({ activeTabs: [tab] });

  const result = await trigger.handleRequest({ id: 'a1', action: 'save-active' });

  assert.deepEqual(calls.queries, [{ active: true, lastFocusedWindow: true }]);
  assert.deepEqual(calls.saves, [tab]);
  assert.equal(calls.focusedWindows, 0);
  assert.equal(calls.activatedTabs, 0);
  assert.equal(result.success, true);
  assert.equal(result.triggered, true);
  assert.equal(result.tabId, 41);
  assert.equal(result.url, tab.url);
});

test('save-tab invokes the official action for an exact background tab without activating it', async () => {
  const tab = { id: 88, windowId: 9, active: false, url: 'https://example.org/article', title: 'Article' };
  const { trigger, calls } = makeHarness({ tabsById: { 88: tab } });

  const result = await trigger.handleRequest({ id: 't1', action: 'save-tab', tabId: 88 });

  assert.deepEqual(calls.gets, [88]);
  assert.deepEqual(calls.saves, [tab]);
  assert.equal(calls.focusedWindows, 0);
  assert.equal(calls.activatedTabs, 0);
  assert.equal(result.success, true);
  assert.equal(result.triggered, true);
  assert.equal(result.tabId, 88);
});

test('save-tab rejects missing or invalid tab IDs', async () => {
  const { trigger, calls } = makeHarness();

  const result = await trigger.handleRequest({ id: 'bad-tab', action: 'save-tab', tabId: '88' });

  assert.equal(result.success, false);
  assert.equal(result.error.code, 'INVALID_TAB_ID');
  assert.equal(calls.saves.length, 0);
});

test('save actions reject non-http pages and do not call the official action', async () => {
  const tab = { id: 12, active: true, url: 'chrome://extensions', title: 'Extensions' };
  const { trigger, calls } = makeHarness({ activeTabs: [tab] });

  const result = await trigger.handleRequest({ id: 'u1', action: 'save-active' });

  assert.equal(result.success, false);
  assert.equal(result.error.code, 'UNSUPPORTED_URL');
  assert.equal(calls.saves.length, 0);
});

test('unknown actions return a structured error', async () => {
  const { trigger } = makeHarness();

  const result = await trigger.handleRequest({ id: 'x1', action: 'delete-library' });

  assert.equal(result.success, false);
  assert.equal(result.error.code, 'UNKNOWN_ACTION');
});
