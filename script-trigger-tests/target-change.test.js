const test = require('node:test');
const assert = require('node:assert/strict');

const { createScriptTrigger } = require('../src/browserExt/scriptTrigger.js');

test('exact URL save fails before official save if reload redirects the tab', async () => {
  let clock = 0;
  const saves = [];
  const requestedURL = 'https://bcras.hbut.edu.cn/s/net/cnki/detail?id=original';
  const redirectedURL = 'https://bcras.hbut.edu.cn/s/net/cnki/login';
  const initial = {
    id: 81,
    windowId: 10,
    active: false,
    discarded: true,
    status: 'unloaded',
    title: '目标论文',
    url: requestedURL,
  };
  const redirected = {
    ...initial,
    discarded: false,
    status: 'complete',
    title: '登录',
    url: redirectedURL,
  };

  const browserAPI = {
    runtime: {
      id: 'test-extension-id',
      getManifest: () => ({ version: '2.0.0' }),
      connectNative: () => { throw new Error('not used'); },
    },
    tabs: {
      query: async () => [initial],
      reload: async () => {},
      get: async () => redirected,
    },
  };
  const zotero = {
    initDeferred: { promise: Promise.resolve() },
    Connector_Browser: {
      getTabInfo: () => ({ url: redirectedURL, translators: [], isPDF: false }),
      onZoteroButtonElementClick: async (tab) => saves.push(tab),
    },
    debug: () => {},
    logError: () => {},
  };
  const trigger = createScriptTrigger({
    browserAPI,
    zotero,
    autoConnect: false,
    now: () => clock,
    delay: async (milliseconds) => { clock += milliseconds; },
  });

  const result = await trigger.handleRequest({
    id: 'redirected-target',
    action: 'save-url',
    url: requestedURL,
  });

  assert.equal(result.success, false);
  assert.equal(result.error.code, 'TARGET_CHANGED');
  assert.equal(saves.length, 0);
});
