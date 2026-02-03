/**
 * 前端纯逻辑 view_xy_logic.js 的单元测试（Node 内置 test runner）
 * 运行：node --test tests/view_xy_logic.test.js
 */
const { describe, it } = require('node:test');
const assert = require('node:assert');
const path = require('path');

const VIEW_XY = require(path.join(__dirname, '..', 'view_xy_logic.js'));

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

describe('pointMatchesSearch', function () {
  it('returns true when no terms', function () {
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: 'X' }, []), true);
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: 'X' }, null), true);
  });
  it('matches on label (naam)', function () {
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: 'Amsterdam School', brin: '', gemeente: '', postcode: '' }, ['AMS']), true);
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: 'Amsterdam School', brin: '', gemeente: '', postcode: '' }, ['OTHER']), false);
  });
  it('matches on brin, gemeente, postcode', function () {
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: '', brin: '02QZ00', gemeente: '', postcode: '' }, ['02QZ']), true);
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: '', brin: '', gemeente: 'Amsterdam', postcode: '' }, ['AMSTERDAM']), true);
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: '', brin: '', gemeente: '', postcode: '1234 AB' }, ['1234']), true);
  });
  it('normalizes postcode (no spaces) for matching', function () {
    assert.strictEqual(VIEW_XY.pointMatchesSearch({ label: '', brin: '', gemeente: '', postcode: '1234AB' }, ['1234 AB']), true);
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
