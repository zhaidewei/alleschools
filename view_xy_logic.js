/**
 * 前端散点图纯逻辑（无 DOM），供 view_xy.html 使用，并可在 Node 下跑单元测试。
 * 浏览器：挂到 window.VIEW_XY；Node：module.exports
 */
(function () {
  const GOLDEN = 137.508;
  const MAX_COMPARISON_SCHOOLS = 4;
  const VALID_MODES = ['vo', 'po'];
  const VALID_LANGUAGES = ['en', 'zh', 'nl'];
  const VALID_PROFILES = ['nt', 'ng', 'em', 'cm'];

  function normalizeEnum(value, allowed, fallback) {
    const normalized = value == null ? '' : String(value).trim().toLowerCase();
    return allowed.indexOf(normalized) === -1 ? fallback : normalized;
  }

  /** URL/storage 边界使用的枚举归一化。 */
  function normalizeMode(value) {
    return normalizeEnum(value, VALID_MODES, 'vo');
  }

  function normalizeLanguage(value) {
    return normalizeEnum(value, VALID_LANGUAGES, 'en');
  }

  function normalizeProfile(value, mode) {
    if (mode != null && normalizeMode(mode) === 'po') return null;
    return normalizeEnum(value, VALID_PROFILES, 'nt');
  }

  /**
   * 比较项的稳定身份。数据契约优先使用 BRIN；显式 id 可供未来数据源使用。
   * 返回 null 表示该值不能进入比较列表。
   */
  function getStableSchoolId(school, layer) {
    if (school == null) return null;
    if (typeof school === 'string') {
      const identity = school.trim();
      if (!identity) return null;
      if (identity.includes(':')) {
        const separator = identity.indexOf(':');
        const identityLayer = identity.slice(0, separator);
        const schoolId = identity.slice(separator + 1);
        return VALID_MODES.includes(identityLayer) && schoolId ? identityLayer + ':' + schoolId : null;
      }
      return layer ? normalizeMode(layer) + ':' + identity : null;
    }
    const schoolLayer = layer != null ? normalizeMode(layer) : normalizeMode(school.layer != null ? school.layer : school.mode);
    const raw = school.vestigingId != null ? school.vestigingId
      : school.vestiging_id != null ? school.vestiging_id
      : school.pointId != null ? school.pointId
      : school.point_id != null ? school.point_id
      : school.id != null ? school.id
      : school.schoolId != null ? school.schoolId
      : school.school_id != null ? school.school_id
      : school.brin != null ? school.brin
      : school.BRIN;
    if (raw == null) return null;
    const id = String(raw).trim();
    return id ? schoolLayer + ':' + id : null;
  }

  /** 当前 profile 的两个坐标都存在且为有限数值时，学校才可进入比较。 */
  function isComparisonEligible(school) {
    return !!school && Number.isFinite(school.x) && Number.isFinite(school.y);
  }

  /** 稳定去重并截断到四所；保留第一次出现的完整对象。 */
  function normalizeComparisonList(schools, layer, limit) {
    if (typeof layer === 'number') { limit = layer; layer = null; }
    const max = limit == null ? MAX_COMPARISON_SCHOOLS : Math.max(0, Math.min(MAX_COMPARISON_SCHOOLS, Number(limit) || 0));
    if (!Array.isArray(schools) || max === 0) return [];
    const seen = new Set();
    const result = [];
    for (let i = 0; i < schools.length && result.length < max; i++) {
      if (!isComparisonEligible(schools[i])) continue;
      const id = getStableSchoolId(schools[i], layer);
      if (id == null || seen.has(id)) continue;
      seen.add(id);
      result.push(schools[i]);
    }
    return result;
  }

  /** 已存在则移除，否则在未满四所时加入。 */
  function toggleComparison(schools, school, layer) {
    const current = normalizeComparisonList(schools, layer);
    const id = getStableSchoolId(school, layer);
    if (id == null) return current;
    const existingIndex = current.findIndex(function (item) { return getStableSchoolId(item, layer) === id; });
    if (existingIndex !== -1) {
      return current.filter(function (_, index) { return index !== existingIndex; });
    }
    return current.length >= MAX_COMPARISON_SCHOOLS || !isComparisonEligible(school) ? current : current.concat([school]);
  }

  function removeComparison(schools, schoolOrId, layer) {
    const id = getStableSchoolId(schoolOrId, layer);
    const current = normalizeComparisonList(schools, layer);
    if (id == null) return current;
    return current.filter(function (item) { return getStableSchoolId(item, layer) !== id; });
  }

  function clearComparison() {
    return [];
  }

  function comparisonAfterLayerChange(schools, previousLayer, nextLayer) {
    return normalizeMode(previousLayer) === normalizeMode(nextLayer)
      ? normalizeComparisonList(schools, nextLayer)
      : [];
  }

  function comparisonAfterProfileChange(schools, layer) {
    return normalizeComparisonList(schools, layer);
  }

  function normalizeGemeenteState(value, allGemeenten) {
    if (typeof value === 'string' && value.trim().toLowerCase() === 'all') return 'all';
    const wasArray = Array.isArray(value);
    const values = wasArray ? value : (value == null || String(value).trim() === '' ? [] : String(value).split(','));
    const seen = new Set();
    const selected = values.map(function (item) { return String(item).trim(); }).filter(function (item) {
      if (!item || seen.has(item)) return false;
      seen.add(item);
      return true;
    });
    if (selected.some(function (item) { return item.toLowerCase() === 'all'; })) return 'all';

    /* 旧状态会把当前 layer 的完整城市列表逐项持久化；已知全集时迁移为 compact sentinel。 */
    if (Array.isArray(allGemeenten) && allGemeenten.length > 0) {
      const expected = new Set(allGemeenten.map(function (item) { return String(item).trim(); }).filter(Boolean));
      if (expected.size === selected.length && selected.every(function (item) { return expected.has(item); })) return 'all';
    }
    if (selected.length === 0) return wasArray ? [] : '';
    return wasArray ? selected : selected.join(',');
  }

  /** 分享前生成唯一的 canonical 状态；all 与显式空选择具有不同语义。 */
  function normalizeShareState(state) {
    const source = state && typeof state === 'object' ? state : {};
    const mode = normalizeMode(source.mode);
    const rawGemeente = source.gemeente != null ? source.gemeente : source.city;
    const allGemeenten = source.allGemeenten || source.availableGemeenten || source.gemeentenAvailable;
    const gemeente = normalizeGemeenteState(rawGemeente, allGemeenten);
    const rawComparison = source.compare != null ? source.compare : source.comparison;
    const comparisonValues = Array.isArray(rawComparison) ? rawComparison : String(rawComparison || '').split(',');
    const comparison = [];
    const seenComparison = new Set();
    comparisonValues.forEach(function (item) {
      const identity = getStableSchoolId(item, mode);
      if (identity && identity.startsWith(mode + ':') && !seenComparison.has(identity) && comparison.length < MAX_COMPARISON_SCHOOLS) {
        seenComparison.add(identity);
        comparison.push(identity);
      }
    });
    return {
      lang: normalizeLanguage(source.lang),
      mode: mode,
      q: source.q == null ? '' : String(source.q).trim(),
      gemeente: gemeente,
      profile: normalizeProfile(source.profile, mode),
      compare: comparison,
    };
  }

  function stateObject(value) {
    if (!value) return {};
    if (typeof value === 'object' && !(value instanceof URLSearchParams)) return value;
    const params = value instanceof URLSearchParams ? value : new URLSearchParams(String(value).replace(/^\?/, ''));
    const result = {};
    params.forEach(function (item, key) { result[key] = item; });
    return result;
  }

  /** URL 中存在的键逐项覆盖 storage，storage 再覆盖 default；兼容旧 city。 */
  function deserializeShareState(urlState, storageState, defaultState) {
    const defaults = stateObject(defaultState);
    const storage = stateObject(storageState);
    const url = stateObject(urlState);
    const merged = {};
    ['lang', 'mode', 'q', 'gemeente', 'profile', 'compare'].forEach(function (key) {
      if (Object.prototype.hasOwnProperty.call(url, key)) merged[key] = url[key];
      else if (key === 'gemeente' && Object.prototype.hasOwnProperty.call(url, 'city')) merged[key] = url.city;
      else if (Object.prototype.hasOwnProperty.call(storage, key)) merged[key] = storage[key];
      else if (key === 'gemeente' && Object.prototype.hasOwnProperty.call(storage, 'city')) merged[key] = storage.city;
      else if (Object.prototype.hasOwnProperty.call(defaults, key)) merged[key] = defaults[key];
      else if (key === 'gemeente' && Object.prototype.hasOwnProperty.call(defaults, 'city')) merged[key] = defaults.city;
    });
    const cityUniverse = url.allGemeenten || url.availableGemeenten
      || storage.allGemeenten || storage.availableGemeenten
      || defaults.allGemeenten || defaults.availableGemeenten;
    if (cityUniverse) merged.allGemeenten = cityUniverse;
    return normalizeShareState(merged);
  }

  /** 确定性的 URL 查询串；空值也编码，以支持显式空城市回放。 */
  function serializeShareState(state) {
    const normalized = normalizeShareState(state);
    const pairs = [
      ['lang', normalized.lang],
      ['mode', normalized.mode],
      ['q', normalized.q],
      ['gemeente', Array.isArray(normalized.gemeente) ? normalized.gemeente.join(',') : normalized.gemeente],
    ];
    if (normalized.profile != null) pairs.push(['profile', normalized.profile]);
    pairs.push(['compare', normalized.compare.join(',')]);
    return pairs.map(function (pair) { return encodeURIComponent(pair[0]) + '=' + encodeURIComponent(pair[1]); }).join('&');
  }

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

  /** 从校名生成首字母缩写（按空格分词，取每词首字母） */
  function acronymFromName(naam) {
    if (!naam || !String(naam).trim()) return '';
    return String(naam).trim().split(/\s+/).map(function (w) { return (w[0] || '').toUpperCase(); }).join('');
  }

  /** 点 p 是否匹配任意一个搜索词（校名、首字母缩写、BRIN、邮编）。市镇由独立筛选负责。 */
  function pointMatchesSearch(p, searchTerms) {
    if (!searchTerms || searchTerms.length === 0) return true;
    const naam = (p.label || '').toUpperCase();
    const acr = acronymFromName(p.label || '');
    const brin = (p.brin || '').toUpperCase();
    const postcode = (p.postcode || '').toUpperCase().replace(/\s/g, '');
    return searchTerms.some(function (term) {
      const termNorm = term.replace(/\s/g, '');
      return naam.includes(term) || (acr && acr.includes(termNorm)) || brin.includes(term) || postcode.includes(termNorm);
    });
  }

  /** 返回匹配点的新数组，供图表高亮、空状态和计数共用同一判定。 */
  function filterPointsBySearch(points, searchTerms) {
    if (!Array.isArray(points)) return [];
    return points.filter(function (point) { return pointMatchesSearch(point, searchTerms); });
  }

  function countSearchMatches(points, searchTerms) {
    return filterPointsBySearch(points, searchTerms).length;
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

  /** 面积与人数成正比：半径按 sqrt(size) 缩放，并限制在 4–18 px。 */
  function sizeToRadius(points) {
    const sizes = points.map(function (p) { return (p.size != null && p.size > 0) ? p.size : 0; }).filter(Boolean);
    if (sizes.length === 0) return function () { return 8; };
    const minS = Math.min.apply(null, sizes);
    const maxS = Math.max.apply(null, sizes);
    if (minS <= 0 || maxS <= minS) return function () { return 8; };
    const k = 4 / Math.sqrt(minS);
    const maxRadius = 4 * Math.sqrt(maxS / minS);
    const scale = maxRadius > 18 ? 18 / maxRadius : 1;
    return function (size) {
      if (size == null || size <= 0) return 8;
      const radius = k * Math.sqrt(size) * scale;
      return Math.round(Math.max(4, Math.min(18, radius)));
    };
  }

  /**
   * 从 meta.i18n 中按优先级（lang -> en -> 任意一种）查找某个 metric 的定义。
   * 返回值类似 { label, short, description }，找不到时返回 null。
   */
  function getMetricFromMeta(meta, metricId, lang) {
    if (!meta || !metricId || !meta.i18n || typeof meta.i18n !== 'object') {
      return null;
    }
    const tried = new Set();
    const order = [];
    if (lang && meta.i18n[lang]) {
      order.push(lang);
      tried.add(lang);
    }
    if (meta.i18n.en && !tried.has('en')) {
      order.push('en');
      tried.add('en');
    }
    Object.keys(meta.i18n).forEach(function (code) {
      if (!tried.has(code)) {
        order.push(code);
        tried.add(code);
      }
    });
    for (let i = 0; i < order.length; i++) {
      const code = order[i];
      const loc = meta.i18n[code];
      if (!loc || !loc.metrics) continue;
      const metric = loc.metrics[metricId];
      if (metric) return metric;
    }
    return null;
  }

  /** 仅按 gemeente 文本筛选：parts 为空则返回全部，否则保留 gemeente 包含任意 part 的点 */
  function filterPointsByGemeenteText(points, parts) {
    if (!parts || parts.length === 0) return points;
    return points.filter(function (p) {
      return p.gemeente && parts.some(function (q) { return p.gemeente.toUpperCase().includes(q); });
    });
  }

  const VIEW_XY = {
    MAX_COMPARISON_SCHOOLS: MAX_COMPARISON_SCHOOLS,
    normalizeMode: normalizeMode,
    normalizeLanguage: normalizeLanguage,
    normalizeProfile: normalizeProfile,
    normalizeGemeenteState: normalizeGemeenteState,
    getStableSchoolId: getStableSchoolId,
    isComparisonEligible: isComparisonEligible,
    normalizeComparisonList: normalizeComparisonList,
    toggleComparison: toggleComparison,
    removeComparison: removeComparison,
    clearComparison: clearComparison,
    comparisonAfterLayerChange: comparisonAfterLayerChange,
    comparisonAfterProfileChange: comparisonAfterProfileChange,
    normalizeShareState: normalizeShareState,
    deserializeShareState: deserializeShareState,
    serializeShareState: serializeShareState,
    parseSearchTerms: parseSearchTerms,
    parseGemeenteFilter: parseGemeenteFilter,
    acronymFromName: acronymFromName,
    pointMatchesSearch: pointMatchesSearch,
    filterPointsBySearch: filterPointsBySearch,
    countSearchMatches: countSearchMatches,
    getNameHighlights: getNameHighlights,
    hashString: hashString,
    gemeenteToColor: gemeenteToColor,
    gemeenteToBorderColor: gemeenteToBorderColor,
    sizeToRadius: sizeToRadius,
    filterPointsByGemeenteText: filterPointsByGemeenteText,
    getMetricFromMeta: getMetricFromMeta,
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = VIEW_XY;
  }
  if (typeof window !== 'undefined') {
    window.VIEW_XY = VIEW_XY;
  }
})();
