const test = require('node:test');
const assert = require('node:assert/strict');

const { createScriptTrigger } = require('../src/browserExt/scriptTrigger.js');

function makeHarness({ activeTabs = [], allTabs = [], tabsById = {} } = {}) {
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
        return query && query.active ? activeTabs : allTabs;
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

test('ping returns a versioned capability contract without selecting a tab', async () => {
  const { trigger, calls } = makeHarness();

  const result = await trigger.handleRequest({ id: 'p1', action: 'ping' });

  assert.equal(result.id, 'p1');
  assert.equal(result.success, true);
  assert.equal(result.action, 'ping');
  assert.equal(result.extensionId, 'test-extension-id');
  assert.equal(result.extensionVersion, '1.2.3');
  assert.equal(result.protocolVersion, 2);
  assert.deepEqual(result.capabilities, [
    'list-tabs',
    'save-active',
    'save-tab',
    'save-url',
    'save-title',
  ]);
  assert.equal(calls.queries.length, 0);
  assert.equal(calls.saves.length, 0);
});

test('list-tabs returns only saveable HTTP(S) tabs', async () => {
  const tabs = [
    { id: 1, windowId: 1, active: true, url: 'https://kns.cnki.net/detail', title: 'CNKI' },
    { id: 2, windowId: 1, active: false, url: 'chrome://extensions', title: 'Extensions' },
    { id: 3, windowId: 2, active: false, url: 'http://example.org', title: 'Example' },
  ];
  const { trigger, calls } = makeHarness({ allTabs: tabs });

  const result = await trigger.handleRequest({ id: 'l1', action: 'list-tabs' });

  assert.equal(result.success, true);
  assert.deepEqual(result.tabs.map(tab => tab.id), [1, 3]);
  assert.deepEqual(calls.queries, [{}]);
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

test('save-url selects one exact URL without focusing or activating it', async () => {
  const target = {
    id: 91,
    windowId: 11,
    active: false,
    url: 'https://bcras.hbut.edu.cn/s/net/cnki/detail?id=123',
    title: '目标论文 - 中国知网',
  };
  const { trigger, calls } = makeHarness({
    allTabs: [
      { id: 90, windowId: 11, active: true, url: 'https://example.org', title: 'Other' },
      target,
    ],
  });

  const result = await trigger.handleRequest({
    id: 'url-1',
    action: 'save-url',
    url: target.url,
  });

  assert.deepEqual(calls.queries, [{}]);
  assert.deepEqual(calls.saves, [target]);
  assert.equal(calls.focusedWindows, 0);
  assert.equal(calls.activatedTabs, 0);
  assert.equal(result.tabId, target.id);
  assert.equal(result.url, target.url);
});

test('save-url fails closed when a substring matches multiple tabs', async () => {
  const { trigger, calls } = makeHarness({
    allTabs: [
      { id: 1, url: 'https://kns.cnki.net/a', title: 'A' },
      { id: 2, url: 'https://kns.cnki.net/b', title: 'B' },
    ],
  });

  const result = await trigger.handleRequest({
    id: 'url-ambiguous',
    action: 'save-url',
    urlContains: 'kns.cnki.net',
  });

  assert.equal(result.success, false);
  assert.equal(result.error.code, 'TAB_AMBIGUOUS');
  assert.equal(calls.saves.length, 0);
});

test('save-title selects one tab by a non-empty title fragment', async () => {
  const target = { id: 22, url: 'https://example.org/paper', title: 'BIM论文 - 中国知网' };
  const { trigger, calls } = makeHarness({ allTabs: [target] });

  const result = await trigger.handleRequest({
    id: 'title-1',
    action: 'save-title',
    titleContains: 'BIM论文',
  });

  assert.equal(result.success, true);
  assert.deepEqual(calls.saves, [target]);
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

test('native port forwards a request and posts the structured response', async () => {
  let messageListener;
  const posted = [];
  const port = {
    onMessage: { addListener: listener => { messageListener = listener; } },
    onDisconnect: { addListener: () => {} },
    postMessage: message => posted.push(message),
    disconnect: () => {},
  };
  const browserAPI = {
    runtime: {
      id: 'connected-extension',
      getManifest: () => ({ version: '9.9.9' }),
      connectNative: host => {
        assert.equal(host, 'org.zotero.script_trigger');
        return port;
      },
    },
    tabs: { query: async () => [], get: async () => null },
  };
  const zotero = {
    initDeferred: { promise: Promise.resolve() },
    Connector_Browser: { onZoteroButtonElementClick: async () => {} },
    debug: () => {},
    logError: () => {},
  };

  createScriptTrigger({ browserAPI, zotero });
  await messageListener({ id: 'port-1', action: 'ping' });

  assert.equal(posted.length, 1);
  assert.equal(posted[0].id, 'port-1');
  assert.equal(posted[0].success, true);
  assert.equal(posted[0].extensionId, 'connected-extension');
});
