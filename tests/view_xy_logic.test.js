/**
 * 前端纯逻辑 view_xy_logic.js 的单元测试（Node 内置 test runner）
 * 运行：node --test tests/view_xy_logic.test.js
 */
const { describe, it } = require('node:test');
const assert = require('node:assert');
const path = require('path');

const VIEW_XY = require(path.join(__dirname, '..', 'view_xy_logic.js'));

describe('V2 enum normalization', function () {
  it('normalizes mode and falls back to vo', function () {
    assert.strictEqual(VIEW_XY.normalizeMode(' PO '), 'po');
    assert.strictEqual(VIEW_XY.normalizeMode('invalid'), 'vo');
    assert.strictEqual(VIEW_XY.normalizeMode(null), 'vo');
  });
  it('normalizes language and falls back to en', function () {
    assert.strictEqual(VIEW_XY.normalizeLanguage('ZH'), 'zh');
    assert.strictEqual(VIEW_XY.normalizeLanguage('de'), 'en');
  });
  it('accepts only VO profiles, defaults VO to nt and makes PO profile absent', function () {
    assert.strictEqual(VIEW_XY.normalizeProfile(' NT '), 'nt');
    assert.strictEqual(VIEW_XY.normalizeProfile('overview'), 'nt');
    assert.strictEqual(VIEW_XY.normalizeProfile('bad'), 'nt');
    assert.strictEqual(VIEW_XY.normalizeProfile('cm', 'po'), null);
  });
});

describe('comparison list', function () {
  const schools = [
    { layer: 'vo', brin: 'A', label: 'Alpha', x: 1, y: 6.1 },
    { layer: 'vo', brin: 'B', label: 'Beta', x: 2, y: 6.2 },
    { layer: 'vo', brin: 'C', label: 'Gamma', x: 3, y: 6.3 },
    { layer: 'vo', brin: 'D', label: 'Delta', x: 4, y: 6.4 },
    { layer: 'vo', brin: 'E', label: 'Epsilon', x: 5, y: 6.5 },
  ];

  it('deduplicates by stable id, preserves order and caps at four', function () {
    const duplicate = { layer: 'vo', brin: 'A', label: 'Second Alpha', x: 9, y: 9 };
    const result = VIEW_XY.normalizeComparisonList([schools[0], duplicate].concat(schools.slice(1)));
    assert.deepStrictEqual(result, schools.slice(0, 4));
  });
  it('toggles without mutating the input and blocks a fifth school', function () {
    const original = schools.slice(0, 2);
    assert.deepStrictEqual(VIEW_XY.toggleComparison(original, schools[0]), [schools[1]]);
    assert.deepStrictEqual(original, schools.slice(0, 2));
    assert.deepStrictEqual(VIEW_XY.toggleComparison(schools.slice(0, 4), schools[4]), schools.slice(0, 4));
  });
  it('removes by object or id and clears', function () {
    assert.deepStrictEqual(VIEW_XY.removeComparison(schools.slice(0, 3), { layer: 'vo', brin: 'B' }), [schools[0], schools[2]]);
    assert.deepStrictEqual(VIEW_XY.removeComparison(schools.slice(0, 3), 'vo:C'), schools.slice(0, 2));
    assert.deepStrictEqual(VIEW_XY.clearComparison(schools), []);
  });
  it('accepts explicit id fields and rejects identity-less entries', function () {
    assert.strictEqual(VIEW_XY.getStableSchoolId({ layer: 'po', vestiging_id: 42, brin: 'ignored' }), 'po:42');
    const valid = { layer: 'vo', BRIN: '00AA', x: 0, y: 0 };
    assert.deepStrictEqual(VIEW_XY.normalizeComparisonList([{ layer: 'vo', label: 'No id', x: 1, y: 1 }, valid]), [valid]);
  });
  it('requires finite x and y for the current profile', function () {
    assert.strictEqual(VIEW_XY.isComparisonEligible({ x: 0, y: 0 }), true);
    assert.strictEqual(VIEW_XY.isComparisonEligible({ x: '1', y: 2 }), false);
    assert.strictEqual(VIEW_XY.isComparisonEligible({ x: NaN, y: 2 }), false);
    assert.strictEqual(VIEW_XY.isComparisonEligible({ x: 1, y: Infinity }), false);
    assert.deepStrictEqual(VIEW_XY.toggleComparison(schools.slice(0, 1), { layer: 'vo', brin: 'Z', x: 1, y: null }), schools.slice(0, 1));
  });
  it('clears on layer change and preserves identities on profile change', function () {
    assert.deepStrictEqual(VIEW_XY.comparisonAfterLayerChange(schools.slice(0, 2), 'vo', 'po'), []);
    assert.deepStrictEqual(VIEW_XY.comparisonAfterProfileChange(schools.slice(0, 2), 'vo'), schools.slice(0, 2));
  });
});

describe('share state normalization', function () {
  it('normalizes enums, text, comparison and preserves explicit empty cities', function () {
    assert.deepStrictEqual(VIEW_XY.normalizeShareState({
      lang: 'NL', mode: 'PO', q: '  school ', gemeente: [], profile: 'NT',
      compare: ['po:A', 'po:A', 'po:B'],
    }), {
      lang: 'nl', mode: 'po', q: 'school', gemeente: [], profile: null, compare: ['po:A', 'po:B'],
    });
  });
  it('serializes a deterministic canonical query string', function () {
    assert.strictEqual(
      VIEW_XY.serializeShareState({ lang: 'zh', mode: 'vo', q: 'A B', gemeente: [], profile: 'EM' }),
      'lang=zh&mode=vo&q=A%20B&gemeente=&profile=em&compare=',
    );
  });
  it('roundtrips the all sentinel without expanding it', function () {
    const query = VIEW_XY.serializeShareState({ lang: 'en', mode: 'vo', gemeente: 'all', profile: 'nt' });
    assert.strictEqual(query, 'lang=en&mode=vo&q=&gemeente=all&profile=nt&compare=');
    assert.strictEqual(VIEW_XY.deserializeShareState(query).gemeente, 'all');
  });
  it('roundtrips explicit empty selection separately from all', function () {
    const query = VIEW_XY.serializeShareState({ mode: 'vo', gemeente: [] });
    assert.strictEqual(query, 'lang=en&mode=vo&q=&gemeente=&profile=nt&compare=');
    assert.strictEqual(VIEW_XY.deserializeShareState(query).gemeente, '');
  });
  it('migrates an old complete city list when its layer city universe is available', function () {
    assert.strictEqual(VIEW_XY.normalizeShareState({
      mode: 'vo', city: ['Amsterdam', 'Utrecht'], allGemeenten: ['Utrecht', 'Amsterdam'],
    }).gemeente, 'all');
    assert.strictEqual(VIEW_XY.deserializeShareState({}, {
      city: ['Amsterdam', 'Utrecht'],
    }, { allGemeenten: ['Utrecht', 'Amsterdam'] }).gemeente, 'all');
  });
  it('omits profile for PO and keeps canonical parameter order', function () {
    assert.strictEqual(VIEW_XY.serializeShareState({ mode: 'po', profile: 'nt' }), 'lang=en&mode=po&q=&gemeente=&compare=');
  });
  it('deserializes with URL over storage over defaults and migrates city', function () {
    assert.deepStrictEqual(
      VIEW_XY.deserializeShareState('?mode=vo&q=url&city=&profile=cm', { lang: 'nl', q: 'storage', gemeente: 'Utrecht' }, { lang: 'en', mode: 'po', q: 'default' }),
      { lang: 'nl', mode: 'vo', q: 'url', gemeente: '', profile: 'cm', compare: [] },
    );
  });
  it('lets an explicit URL all or empty value override storage', function () {
    assert.strictEqual(VIEW_XY.deserializeShareState('?gemeente=all', { gemeente: ['Utrecht'] }).gemeente, 'all');
    assert.strictEqual(VIEW_XY.deserializeShareState('?gemeente=', { gemeente: 'all' }).gemeente, '');
  });
});

describe('parseSearchTerms', function () {
  it('returns [] for empty or whitespace', function () {
    assert.deepStrictEqual(VIEW_XY.parseSearchTerms(''), []);
    assert.deepStrictEqual(VIEW_XY.parseSearchTerms('   '), []);
    assert.deepStrictEqual(VIEW_XY.parseSearchTerms(null), []);
  });
  it('splits by comma, trims, uppercases', function () {
    assert.deepStrictEqual(VIEW_XY.parseSearchTerms('a,b'), ['A', 'B']);
    assert.deepStrictEqual(VIEW_XY.parseSearchTerms('  ams , zand  '), ['AMS', 'ZAND']);
  });
  it('filters empty segments', function () {
    assert.deepStrictEqual(VIEW_XY.parseSearchTerms('a,,b'), ['A', 'B']);
  });
});

describe('parseGemeenteFilter', function () {
  it('returns [] for empty', function () {
    assert.deepStrictEqual(VIEW_XY.parseGemeenteFilter(''), []);
  });
  it('parses comma-separated, upper case', function () {
    assert.deepStrictEqual(VIEW_XY.parseGemeenteFilter("gra,zoe,voor"), ['GRA', 'ZOE', 'VOOR']);
  });
});

describe('acronymFromName', function () {
  it('returns empty for empty or whitespace', function () {
    assert.strictEqual(VIEW_XY.acronymFromName(''), '');
    assert.strictEqual(VIEW_XY.acronymFromName('   '), '');
    assert.strictEqual(VIEW_XY.acronymFromName(null), '');
  });
  it('takes first letter of each word, uppercase', function () {
    assert.strictEqual(VIEW_XY.acronymFromName('H Wesselink College'), 'HWC');
    assert.strictEqual(VIEW_XY.acronymFromName('Amsterdam School'), 'AS');
    assert.strictEqual(VIEW_XY.acronymFromName('single'), 'S');
  });
  it('trims and collapses spaces', function () {
    assert.strictEqual(VIEW_XY.acronymFromName('  a  b  '), 'AB');
  });
});

describe('pointMatchesSearch', function () {
  it('returns true when no terms', function () {
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: 'X' }, []), true);
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: 'X' }, null), true);
  });
  it('matches on label (naam)', function () {
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: 'Amsterdam School', brin: '', gemeente: '', postcode: '' }, ['AMS']), true);
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: 'Amsterdam School', brin: '', gemeente: '', postcode: '' }, ['OTHER']), false);
  });
  it('matches on acronym (full and partial)', function () {
    var p = { label: 'H Wesselink College', brin: '', gemeente: '', postcode: '' };
    assert.strictEqual(VIEW_XY.pointMatchesSearch(p, ['HWC']), true);
    assert.strictEqual(VIEW_XY.pointMatchesSearch(p, ['WC']), true);
    assert.strictEqual(VIEW_XY.pointMatchesSearch(p, ['HW']), true);
    assert.strictEqual(VIEW_XY.pointMatchesSearch(p, ['XY']), false);
  });
  it('matches on brin and postcode but leaves municipality to its own filter', function () {
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: '', brin: '02QZ00', gemeente: '', postcode: '' }, ['02QZ']), true);
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: '', brin: '', gemeente: 'Amsterdam', postcode: '' }, ['AMSTERDAM']), false);
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: '', brin: '', gemeente: '', postcode: '1234 AB' }, ['1234']), true);
  });
  it('normalizes postcode (no spaces) for matching', function () {
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: '', brin: '', gemeente: '', postcode: '1234AB' }, ['1234 AB']), true);
  });
  it('reuses the same predicate for filtering and match counts', function () {
    const points = [
      { label: 'Alpha School', brin: '01AA', postcode: '1234 AB', gemeente: 'Utrecht' },
      { label: 'Beta College', brin: '02BB', postcode: '5678 CD', gemeente: 'Amsterdam' },
    ];
    assert.deepStrictEqual(VIEW_XY.filterPointsBySearch(points, ['ALPHA']), [points[0]]);
    assert.strictEqual(VIEW_XY.countSearchMatches(points, ['ALPHA']), 1);
    assert.strictEqual(VIEW_XY.countSearchMatches(points, ['AMSTERDAM']), 0);
    assert.strictEqual(VIEW_XY.countSearchMatches(points, []), 2);
  });
});

describe('getNameHighlights', function () {
  it('returns [] for no label or no terms', function () {
    assert.deepStrictEqual(VIEW_XY.getNameHighlights('', ['a']), []);
    assert.deepStrictEqual(VIEW_XY.getNameHighlights('Hello', []), []);
  });
  it('returns merged ranges for term matches', function () {
    assert.deepStrictEqual(VIEW_XY.getNameHighlights('Amsterdam', ['AMS']), [[0, 3]]);
    // 'AM' in "AMSTERDAM SCHOOL" at 0 and 7
    assert.deepStrictEqual(VIEW_XY.getNameHighlights('Amsterdam School', ['AM']), [[0, 2], [7, 9]]);
  });
  it('merges overlapping ranges', function () {
    // 'AM' at [0,2], 'STER' at [2,6] -> merge to [0,6]; second 'AM' at [7,9] stays separate
    assert.deepStrictEqual(VIEW_XY.getNameHighlights('Amsterdam', ['AM', 'STER']), [[0, 6], [7, 9]]);
  });
});

describe('hashString', function () {
  it('is deterministic', function () {
    assert.strictEqual(VIEW_XY.hashString('A'), VIEW_XY.hashString('A'));
    assert.strictEqual(VIEW_XY.hashString('GRAVENHAGE', 0), VIEW_XY.hashString('GRAVENHAGE', 0));
  });
  it('seed changes result', function () {
    const a = VIEW_XY.hashString('X', 0);
    const b = VIEW_XY.hashString('X', 1);
    assert.notStrictEqual(a, b);
  });
  it('returns unsigned 32-bit', function () {
    const h = VIEW_XY.hashString('something');
    assert.ok(typeof h === 'number' && h >= 0 && h <= 0xffffffff);
  });
});

describe('gemeenteToColor', function () {
  it('returns hsla string', function () {
    const c = VIEW_XY.gemeenteToColor('Amsterdam');
    assert.ok(/^hsla\([\d.]+,\s*[\d.]+%,\s*[\d.]+%,\s*0\.9\)$/.test(c));
  });
  it('same gemeente gives same color', function () {
    assert.strictEqual(VIEW_XY.gemeenteToColor('X'), VIEW_XY.gemeenteToColor('X'));
  });
});

describe('gemeenteToBorderColor', function () {
  it('returns hsl string', function () {
    const c = VIEW_XY.gemeenteToBorderColor('Amsterdam');
    assert.ok(/^hsl\([\d.]+,\s*[\d.]+%,\s*[\d.]+%\)$/.test(c));
  });
});

describe('sizeToRadius', function () {
  it('returns default 8 when no sizes', function () {
    const fn = VIEW_XY.sizeToRadius([{ size: 0 }, { size: null }]);
    assert.strictEqual(fn(100), 8);
  });
  it('maps size to radius between 4 and ~18', function () {
    const points = [{ size: 10 }, { size: 100 }, { size: 1000 }];
    const fn = VIEW_XY.sizeToRadius(points);
    assert.strictEqual(fn(10), 4);
    assert.strictEqual(fn(1000), 18);
    assert.ok(fn(100) >= 4 && fn(100) <= 18);
  });
  it('null/zero size gives 8', function () {
    const fn = VIEW_XY.sizeToRadius([{ size: 50 }, { size: 200 }]);
    assert.strictEqual(fn(null), 8);
    assert.strictEqual(fn(0), 8);
  });
});

describe('filterPointsByGemeenteText', function () {
  it('returns all points when parts empty', function () {
    const points = [{ gemeente: 'Amsterdam' }, { gemeente: 'Rotterdam' }];
    assert.strictEqual(VIEW_XY.filterPointsByGemeenteText(points, []).length, 2);
    assert.strictEqual(VIEW_XY.filterPointsByGemeenteText(points, null).length, 2);
  });
  it('filters by partial gemeente match', function () {
    const points = [
      { gemeente: 'Amsterdam' },
      { gemeente: "'s-Gravenhage" },
      { gemeente: 'Rotterdam' },
    ];
    // only GRA -> Gravenhage; Amsterdam/Rotterdam don't contain GRA
    const out = VIEW_XY.filterPointsByGemeenteText(points, ['GRA']);
    assert.strictEqual(out.length, 1);
    assert.strictEqual(out[0].gemeente, "'s-Gravenhage");
  });
});

describe('getMetricFromMeta', function () {
  const meta = {
    i18n: {
      nl: {
        metrics: {
          po_vwo_advice_share: {
            label: 'VWO-advies aandeel',
            short: 'VWO-advies %',
          },
        },
      },
      en: {
        metrics: {
          po_vwo_advice_share: {
            label: 'VWO advice share',
            short: 'VWO advice %',
          },
        },
      },
    },
  };

  it('returns null when meta or metricId missing', function () {
    assert.strictEqual(VIEW_XY.getMetricFromMeta(null, 'x', 'en'), null);
    assert.strictEqual(VIEW_XY.getMetricFromMeta({}, 'x', 'en'), null);
    assert.strictEqual(VIEW_XY.getMetricFromMeta(meta, '', 'en'), null);
  });

  it('prefers requested lang when available', function () {
    const m = VIEW_XY.getMetricFromMeta(meta, 'po_vwo_advice_share', 'nl');
    assert.ok(m);
    assert.strictEqual(m.label, 'VWO-advies aandeel');
  });

  it('falls back to en when requested lang missing', function () {
    const m = VIEW_XY.getMetricFromMeta(meta, 'po_vwo_advice_share', 'zh');
    assert.ok(m);
    assert.strictEqual(m.label, 'VWO advice share');
  });

  it('returns null when metricId not found in any language', function () {
    const m = VIEW_XY.getMetricFromMeta(meta, 'unknown_metric', 'nl');
    assert.strictEqual(m, null);
  });
});
