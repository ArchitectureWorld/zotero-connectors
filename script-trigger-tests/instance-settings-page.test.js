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

test('settings page supports only the fixed ZZH and NSY presets', () => {
  const script = read('src/browserExt/instanceSettings/instance-settings-page.js');
  assert.match(script, /presetForProfile/);
  assert.match(script, /ZZH/);
  assert.match(script, /NSY/);
});
