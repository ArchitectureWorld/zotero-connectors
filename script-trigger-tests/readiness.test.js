const test = require('node:test');
const assert = require('node:assert/strict');

const { createScriptTrigger } = require('../src/browserExt/scriptTrigger.js');

test('a discarded background tab is reloaded and translator detection settles before saving', async () => {
  let clock = 0;
  const calls = {
    reloads: [],
    gets: [],
    saves: [],
    focusedWindows: 0,
    activatedTabs: 0,
  };
  const url = 'https://bcras.hbut.edu.cn/s/net/cnki/detail?id=ready';
  const discarded = {
    id: 77,
    windowId: 9,
    active: false,
    discarded: true,
    status: 'unloaded',
    title: '目标论文 - 中国知网',
    url,
  };
  const loading = { ...discarded, discarded: false, status: 'loading' };
  const complete = { ...discarded, discarded: false, status: 'complete' };

  const browserAPI = {
    runtime: {
      id: 'test-extension-id',
      getManifest: () => ({ version: '2.0.0' }),
      connectNative: () => { throw new Error('not used'); },
    },
    tabs: {
      query: async () => [discarded],
      reload: async (tabId) => {
        calls.reloads.push(tabId);
      },
      get: async (tabId) => {
        calls.gets.push(tabId);
        return clock < 100 ? loading : complete;
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
      getTabInfo: () => ({
        url,
        translators: clock >= 200 ? [] : null,
        isPDF: false,
      }),
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
    now: () => clock,
    delay: async (milliseconds) => {
      clock += milliseconds;
    },
    pollInterval: 100,
  });

  const result = await trigger.handleRequest({ id: 'ready-1', action: 'save-url', url });

  assert.equal(result.success, true);
  assert.deepEqual(calls.reloads, [77]);
  assert.ok(calls.gets.length >= 2);
  assert.deepEqual(calls.saves, [complete]);
  assert.equal(calls.focusedWindows, 0);
  assert.equal(calls.activatedTabs, 0);
  assert.ok(clock >= 200);
});

test('exact URL save fails without creating a webpage item when translator detection times out', async () => {
  let clock = 0;
  const saves = [];
  const url = 'https://bcras.hbut.edu.cn/s/net/cnki/detail?id=timeout';
  const tab = {
    id: 78,
    windowId: 9,
    active: false,
    discarded: false,
    status: 'complete',
    title: '尚未识别 - 中国知网',
    url,
  };
  const browserAPI = {
    runtime: {
      id: 'test-extension-id',
      getManifest: () => ({ version: '2.0.0' }),
      connectNative: () => { throw new Error('not used'); },
    },
    tabs: {
      query: async () => [tab],
      get: async () => tab,
    },
  };
  const zotero = {
    initDeferred: { promise: Promise.resolve() },
    Connector_Browser: {
      getTabInfo: () => ({ url, translators: null, isPDF: false, uninjectable: false }),
      onZoteroButtonElementClick: async (target) => saves.push(target),
    },
    debug: () => {},
    logError: () => {},
  };
  const trigger = createScriptTrigger({
    browserAPI,
    zotero,
    autoConnect: false,
    now: () => clock,
    delay: async (milliseconds) => {
      clock += milliseconds;
    },
    pollInterval: 100,
    translatorReadyTimeout: 200,
  });

  const result = await trigger.handleRequest({ id: 'ready-timeout', action: 'save-url', url });

  assert.equal(result.success, false);
  assert.equal(result.error.code, 'TRANSLATOR_TIMEOUT');
  assert.equal(saves.length, 0);
  assert.ok(clock >= 200);
});
