const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const read = relative => fs.readFileSync(path.join(ROOT, relative), 'utf8');

test('instance settings page exposes one explicit apply action for all bound fields', () => {
  const html = read('src/browserExt/instanceSettings/instance-settings.html');
  const script = read('src/browserExt/instanceSettings/instance-settings-page.js');

  assert.match(html, /Profile ID/i);
  assert.match(html, /Zotero Connector URL/i);
  assert.match(html, /Native Host/i);
  assert.match(html, /id="apply"/);
  assert.match(script, /applyInstanceSettings/);
  assert.match(script, /browser\.storage\.local/);
  assert.doesNotMatch(script, /LevelDB|Preferences\b|Local State/);
});

test('settings page loads the browser API polyfill before its own scripts', () => {
  const html = read('src/browserExt/instanceSettings/instance-settings.html');
  const polyfill = html.indexOf('../browser-polyfill.js');
  const settings = html.indexOf('../instanceSettings.js');
  const page = html.indexOf('instance-settings-page.js');
  assert.ok(polyfill >= 0, 'browser-polyfill.js is missing');
  assert.ok(polyfill < settings, 'polyfill must load before instanceSettings.js');
  assert.ok(settings < page, 'settings API must load before page controller');
});

test('settings page supports only the fixed ZZH and NSY presets', () => {
  const script = read('src/browserExt/instanceSettings/instance-settings-page.js');
  assert.match(script, /presetForProfile/);
  assert.match(script, /ZZH/);
  assert.match(script, /NSY/);
});
