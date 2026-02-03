/**
 * 前端散点图纯逻辑（无 DOM），供 view_xy.html 使用，并可在 Node 下跑单元测试。
 * 浏览器：挂到 window.VIEW_XY；Node：module.exports
 */
(function () {
  const GOLDEN = 137.508;

  /** 从搜索框原始字符串解析出词列表（逗号分隔、去空、大写） */
  function parseSearchTerms(raw) {
    const s = (raw || '').trim();
    if (!s) return [];
    return s.split(',').map(function (t) { return t.trim().toUpperCase(); }).filter(Boolean);
  }

  /** 从 gemeente 筛选框字符串解析出词列表 */
  function parseGemeenteFilter(value) {
    const s = (value || '').trim();
    if (!s) return [];
    return s.split(',').map(function (t) { return t.trim().toUpperCase(); }).filter(Boolean);
  }

  /** 点 p 是否匹配任意一个搜索词（校名、BRIN、gemeente、邮编） */
  function pointMatchesSearch(p, searchTerms) {
    if (!searchTerms || searchTerms.length === 0) return true;
    const naam = (p.label || '').toUpperCase();
    const brin = (p.brin || '').toUpperCase();
    const gemeente = (p.gemeente || '').toUpperCase();
    const postcode = (p.postcode || '').toUpperCase().replace(/\s/g, '');
    return searchTerms.some(function (term) {
      const termNorm = term.replace(/\s/g, '');
      return naam.includes(term) || brin.includes(term) || gemeente.includes(term) || postcode.includes(termNorm);
    });
  }

  /** 在 label 中找出被 searchTerms 命中的区间，合并重叠后返回 [[start,end], ...] */
  function getNameHighlights(label, searchTerms) {
    if (!label || !searchTerms || searchTerms.length === 0) return [];
    const upper = label.toUpperCase();
    const ranges = [];
    for (let t = 0; t < searchTerms.length; t++) {
      const term = searchTerms[t];
      let idx = 0;
      while (true) {
        const i = upper.indexOf(term, idx);
        if (i === -1) break;
        ranges.push([i, i + term.length]);
        idx = i + 1;
      }
    }
    ranges.sort(function (a, b) { return a[0] - b[0]; });
    const merged = [];
    for (let i = 0; i < ranges.length; i++) {
      const s = ranges[i][0], e = ranges[i][1];
      if (merged.length && s <= merged[merged.length - 1][1]) {
        merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], e);
      } else {
        merged.push([s, e]);
      }
    }
    return merged;
  }

  /** 确定性 hash，用于 gemeente 上色 */
  function hashString(s, seed) {
    let h = seed || 0;
    const str = (s || '').toString().toUpperCase();
    for (let i = 0; i < str.length; i++) h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
    return Math.abs(h) >>> 0;
  }

  function gemeenteToColor(gemeente) {
    const h = hashString(gemeente);
    const hS = hashString(gemeente, 1);
    const hL = hashString(gemeente, 2);
    const hue = (h * GOLDEN) % 360;
    const sat = 60 + (hS % 35);
    const light = 35 + (hL % 45);
    return 'hsla(' + hue + ', ' + sat + '%, ' + light + '%, 0.9)';
  }

  function gemeenteToBorderColor(gemeente) {
    const h = hashString(gemeente);
    const hS = hashString(gemeente, 1);
    const hL = hashString(gemeente, 2);
    const hue = (h * GOLDEN) % 360;
    const sat = Math.min(85, 60 + (hS % 35) + 10);
    const light = Math.max(18, 35 + (hL % 45) - 22);
    return 'hsl(' + hue + ', ' + sat + '%, ' + light + '%)';
  }

  /** 根据 points 的 size 得到映射函数：size -> 半径(约 4–20) */
  function sizeToRadius(points) {
    const sizes = points.map(function (p) { return (p.size != null && p.size > 0) ? p.size : 0; }).filter(Boolean);
    if (sizes.length === 0) return function () { return 8; };
    const minS = Math.min.apply(null, sizes);
    const maxS = Math.max.apply(null, sizes);
    const range = maxS - minS || 1;
    return function (size) {
      if (size == null || size <= 0) return 8;
      return Math.round(4 + 14 * (size - minS) / range);
    };
  }

  /** 仅按 gemeente 文本筛选：parts 为空则返回全部，否则保留 gemeente 包含任意 part 的点 */
  function filterPointsByGemeenteText(points, parts) {
    if (!parts || parts.length === 0) return points;
    return points.filter(function (p) {
      return p.gemeente && parts.some(function (q) { return p.gemeente.toUpperCase().includes(q); });
    });
  }

  const VIEW_XY = {
    parseSearchTerms: parseSearchTerms,
    parseGemeenteFilter: parseGemeenteFilter,
    pointMatchesSearch: pointMatchesSearch,
    getNameHighlights: getNameHighlights,
    hashString: hashString,
    gemeenteToColor: gemeenteToColor,
    gemeenteToBorderColor: gemeenteToBorderColor,
    sizeToRadius: sizeToRadius,
    filterPointsByGemeenteText: filterPointsByGemeenteText,
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = VIEW_XY;
  }
  if (typeof window !== 'undefined') {
    window.VIEW_XY = VIEW_XY;
  }
})();
