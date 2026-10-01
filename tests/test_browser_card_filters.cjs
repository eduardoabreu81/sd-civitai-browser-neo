// Exercise the shipped Browser filters without loading Forge or its DOM.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../javascript/civitai-html.js'), 'utf8');
const filters = source.slice(source.indexOf('function _browserCardElements('), source.indexOf('// Toggle description visibility'));

function card({ direct = false, installed = false, local = false } = {}) {
    return {
        style: { display: '' },
        getAttribute: () => 'banned_author',
        classList: { contains: (name) => installed && name === 'civmodelcardinstalled' },
        closest: (selector) => {
            if (selector === '#local_list_html') return local ? {} : null;
            if (selector === '[data-direct-url="true"]') return direct ? {} : null;
            return null;
        },
    };
}

function apply(cards) {
    const context = vm.createContext({ document: { querySelectorAll: () => cards } });
    vm.runInContext(filters, context);
    vm.runInContext("hideInstalled(true); initBannedCreators('banned_author', true);", context);
}

test('direct URL card survives installed and banned-creator toggles', () => {
    const direct = card({ direct: true, installed: true });
    apply([direct]);
    assert.equal(direct.style.display, '');
});

test('listing cards still obey the browse toggles', () => {
    const listing = card({ installed: true });
    apply([listing]);
    assert.equal(listing.style.display, 'none');
});

test('Browser toggles leave the Local Models grid alone', () => {
    const local = card({ installed: true, local: true });
    apply([local]);
    assert.equal(local.style.display, '');
});
