(function (root) {
  'use strict';
  var COOKIE_NAME = 'alleschools-language';
  var SUPPORTED = ['en', 'zh', 'nl'];
  function normalize(value) { return SUPPORTED.indexOf(value) >= 0 ? value : 'en'; }
  function get() {
    var prefix = COOKIE_NAME + '=';
    var match = document.cookie.split(';').map(function (part) { return part.trim(); })
      .find(function (part) { return part.indexOf(prefix) === 0; });
    return normalize(match ? decodeURIComponent(match.slice(prefix.length)) : 'en');
  }
  function set(value) {
    var lang = normalize(value);
    document.cookie = COOKIE_NAME + '=' + encodeURIComponent(lang) + '; Path=/; Max-Age=31536000; SameSite=Lax';
    return lang;
  }
  root.ALLESCHOOLS_LANGUAGE = { get: get, set: set, normalize: normalize };
}(typeof window !== 'undefined' ? window : globalThis));
