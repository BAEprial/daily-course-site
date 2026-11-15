/* core.js — 稳定内核。插件只通过 window.Site.register() 注入能力，本文件不随课程变化。 */
(function () {
  'use strict';

  var CFG = window.SITE_CONFIG || {};
  var COURSE = window.COURSE || { meta: {}, lectures: [], termNotes: [], dailyPlan: [] };
  var QUESTIONS = (window.QB && window.QB.questions) || [];
  var PAGE = document.body.dataset.page;
  var APP = document.getElementById('app');
  var LS_KEY = 'dcs.' + (CFG.shortName || 'site') + '.state.v1';
  var PORT = CFG.port || 8766;
  var API = '/api/state';
  var BASES = ['', 'http://127.0.0.1:' + PORT, 'http://localhost:' + PORT];

  var reg = { q: {}, pages: {}, features: {} };
  var listeners = {};
  var state = blank();
  var online = false, saving = false, failed = false, lastSaved = '', saveTimer = null, apiBase = '';

  /* ---------- 基础工具 ---------- */

  function blank() {
    return {
      version: 1, updatedAt: new Date().toISOString(),
      progress: {}, attempts: [], wrongBook: [], briefs: {},
      drafts: {}, notes: {}, settings: {}
    };
  }

  function normalize(s) {
    var b = blank();
    if (!s || typeof s !== 'object') return b;
    Object.keys(b).forEach(function (k) {
      if (s[k] === undefined || s[k] === null) return;
      if (Array.isArray(b[k])) { if (Array.isArray(s[k])) b[k] = s[k]; }
      else if (typeof b[k] === 'object') { if (typeof s[k] === 'object' && !Array.isArray(s[k])) b[k] = s[k]; }
      else b[k] = s[k];
    });
    return b;
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function h(tag, attrs, children) {
    var el = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = String(v);
      else if (k === 'html') el.innerHTML = v;
      else if (k.slice(0, 2) === 'on' && typeof v === 'function') el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : String(v));
    });
    (children || []).forEach(function (c) {
      if (c === null || c === undefined || c === false) return;
      el.appendChild(typeof c === 'object' ? c : document.createTextNode(String(c)));
    });
    return el;
  }

  function pad(n) { return n < 10 ? '0' + n : '' + n; }
  function dayId(n) { return 'd' + pad(n); }
  function clock(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    return pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }
  function lectureOf(n) { return COURSE.lectures[n - 1] || null; }

  /* ---------- 插件注册与钩子 ---------- */

  function register(kind, name, impl) {
    if (kind === 'question-type') reg.q[name] = impl;
    else if (kind === 'page') reg.pages[name] = impl;
    else if (kind === 'feature') reg.features[name] = impl;
    else console.warn('[Site] 未知插件类型：' + kind);
  }

  function on(name, fn) { (listeners[name] = listeners[name] || []).push(fn); }
  function emit(name, payload) {
    (listeners[name] || []).forEach(function (fn) {
      try { fn(payload); } catch (e) { console.error('[Site.emit]', e); }
    });
  }

  // mode='all' 时所有钩子都必须返回 true，用于 question:filter 的与逻辑。
  function hook(name, args, mode) {
    var all = true;
    Object.keys(reg.features).forEach(function (id) {
      var f = reg.features[id];
      var fn = f && f.hooks && f.hooks[name];
      if (typeof fn !== 'function') return;
      var r;
      try { r = fn.apply(null, args || []); } catch (e) { console.error('[Site.hook] ' + id + '.' + name, e); return; }
      if (mode === 'all' && r === false) all = false;
    });
    return all;
  }

  /* ---------- 状态与每日编排 ---------- */

  function questionsOf(n) {
    return QUESTIONS.filter(function (q) {
      return q.day === n && hook('question:filter', [q, n], 'all');
    });
  }

  function progressOf(n) {
    var k = dayId(n);
    if (!state.progress[k]) state.progress[k] = { answers: {}, correct: {}, done: false, completedAt: null };
    var p = state.progress[k];
    if (!p.answers) p.answers = {};
    if (!p.correct) p.correct = {};
    return p;
  }

  function day(n) {
    return { n: n, id: dayId(n), lecture: lectureOf(n), questions: questionsOf(n), progress: progressOf(n) };
  }

  // 当前讲次：优先取 URL 的 ?day=N，否则取第一个未完成的讲次。
  function currentDay() {
    try {
      var n = parseInt(new URLSearchParams(location.search).get('day'), 10);
      if (n >= 1 && n <= COURSE.lectures.length) return n;
    } catch (e) { /* 忽略不支持 URLSearchParams 的环境 */ }
    for (var i = 1; i <= COURSE.lectures.length; i++) {
      var p = state.progress[dayId(i)];
      if (!p || !p.done) return i;
    }
    return COURSE.lectures.length || 1;
  }

  function markWrong(q) {
    var w = null;
    state.wrongBook.forEach(function (x) { if (x.qid === q.id) w = x; });
    if (!w) {
      w = { qid: q.id, day: q.day, stem: q.stem, type: q.type, wrongCount: 0, mastered: false, retired: false, note: '' };
      state.wrongBook.push(w);
    }
    w.wrongCount = (w.wrongCount || 0) + 1;
    w.lastWrong = new Date().toISOString();
    w.mastered = false;
  }

  function markMastered(q) {
    state.wrongBook.forEach(function (w) { if (w.qid === q.id) w.mastered = true; });
  }

  function submit(q, answer) {
    var t = reg.q[q.type];
    var result = (t && typeof t.grade === 'function') ? t.grade(q, answer) : null;
    var correct = (result && typeof result.correct === 'boolean') ? result.correct : null;
    var p = progressOf(q.day);
    p.answers[q.id] = answer;
    if (correct !== null) p.correct[q.id] = correct;
    state.attempts.push({
      id: 'a' + Date.now() + Math.random().toString(36).slice(2, 7),
      ts: new Date().toISOString(), day: q.day, qid: q.id,
      type: q.type, answer: answer, correct: correct
    });
    if (correct === false) markWrong(q);
    else if (correct === true) markMastered(q);
    if (q.type === 'brief' && typeof answer === 'string') {
      state.briefs[dayId(q.day)] = { text: answer, selfChecked: false };
    }
    emit('after:submit', { q: q, result: result });
    hook('after:submit', [q, result]);
    save();
    return result;
  }

  function completeDay(n) {
    var p = progressOf(n);
    if (!p.done) { p.done = true; p.completedAt = new Date().toISOString(); }
    hook('day:complete', [n]);
    emit('day:complete', n);
    save(true);
  }

  function setDraft(key, text) { state.drafts[key] = text; save(); }

  /* ---------- 持久化：本地暂存 + 服务端合并 ---------- */

  function pill() {
    var el = document.getElementById('sync-pill');
    if (!el) return;
    var dot = !online ? 'off' : (failed ? 'off' : (saving ? 'busy' : 'on'));
    var text = !online ? '离线暂存 · 等待服务'
      : (failed ? '保存失败 · 自动重试中'
        : (saving ? '自动保存中…' : '已自动保存' + (lastSaved ? ' ' + lastSaved : '')));
    el.innerHTML = '<span class="dot ' + dot + '"></span>' + esc(text);
    el.title = online
      ? '每次作答与输入都会实时写入 records/state.json，导师可以直接读取。'
      : '当前暂存在浏览器中；请运行 start.bat 启动本地服务后再打开本站。';
  }

  function persistLocal() {
    try { localStorage.setItem(LS_KEY, JSON.stringify(state)); } catch (e) { /* 容量异常忽略 */ }
  }

  function save(immediate) {
    state.updatedAt = new Date().toISOString();
    persistLocal();
    if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; }
    var push = function () {
      if (!online) { pill(); return; }
      saving = true; pill();
      fetch(apiBase + API, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(state)
      }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        failed = false; lastSaved = clock(new Date().toISOString());
      }).catch(function () { failed = true; }).then(function () { saving = false; pill(); });
    };
    if (immediate) push(); else saveTimer = setTimeout(push, 250);
  }

  function flush() {
    if (!online) return;
    try {
      var payload = JSON.stringify(state);
      if (navigator.sendBeacon) {
        navigator.sendBeacon(apiBase + API, new Blob([payload], { type: 'text/plain;charset=UTF-8' }));
      } else {
        fetch(apiBase + API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload, keepalive: true });
      }
    } catch (e) { /* 关闭阶段不阻塞 */ }
  }

  async function initStore() {
    for (var i = 0; i < BASES.length; i++) {
      try {
        var res = await fetch(BASES[i] + API, { cache: 'no-store' });
        if (!res.ok) continue;
        apiBase = BASES[i]; online = true;
        state = normalize(await res.json());
        lastSaved = clock(state.updatedAt);
        return;
      } catch (e) { /* 尝试下一个地址 */ }
    }
    online = false;
    try { state = normalize(JSON.parse(localStorage.getItem(LS_KEY) || 'null')); }
    catch (e) { state = blank(); }
  }

  /* ---------- 渲染助手 ---------- */

  function card(title, nodes) {
    return h('section', { class: 'card' }, [title ? h('h2', { text: title }) : null].concat(nodes || []));
  }
  function stat(num, cap) {
    return h('div', { class: 'stat' }, [h('div', { class: 'num', text: String(num) }), h('div', { class: 'cap', text: cap })]);
  }
  function feedback(q, result) {
    if (!result) return null;
    return h('div', { class: 'feedback' }, [
      h('div', { class: 'verdict ' + (result.correct ? 'ok' : 'bad'), text: result.correct ? '回答正确' : '回答错误' }),
      h('div', { class: 'explain', text: q.explain || '' }),
      q.concept ? h('div', { class: 'concept', text: '知识点：' + q.concept }) : null
    ]);
  }

  function renderQuestion(q) {
    var t = reg.q[q.type];
    if (!t) return h('div', { class: 'notice', text: '题型插件未启用：' + q.type });
    var p = progressOf(q.day);
    var ans = p.answers[q.id];
    var ctx = {
      q: q, day: q.day, answer: ans, locked: ans !== undefined,
      draft: state.drafts[q.day + '-' + q.id] || '',
      submit: function (a) { return submit(q, a); },
      setDraft: function (txt) { setDraft(q.day + '-' + q.id, txt); },
      retry: function () { delete p.answers[q.id]; delete p.correct[q.id]; save(); render(); },
      h: h, esc: esc, save: save, feedback: feedback, reload: render
    };
    try { return t.render(q, ctx); }
    catch (e) {
      console.error('[Site] 渲染题目失败 ' + q.id, e);
      return h('div', { class: 'notice', text: '题目渲染失败：' + q.id });
    }
  }

  function render() {
    if (!APP) return;
    APP.innerHTML = '';
    var p = reg.pages[PAGE];
    if (!p) { APP.appendChild(h('div', { class: 'empty', text: '页面插件未启用：' + PAGE })); return; }
    var node;
    try { node = p.render(Site); } catch (e) {
      console.error('[Site] 渲染页面失败 ' + PAGE, e);
      node = h('div', { class: 'notice', text: '页面渲染失败：' + PAGE });
    }
    APP.appendChild(typeof node === 'string' ? h('div', { html: node }) : node);
  }

  var Site = {
    config: CFG, course: COURSE, questions: QUESTIONS,
    get state() { return state; },
    get online() { return online; },
    route: PAGE,
    register: register, on: on, emit: emit,
    save: save, flush: flush, pill: pill,
    day: day, currentDay: currentDay, questionsOf: questionsOf,
    lectureOf: lectureOf, progressOf: progressOf,
    submit: submit, setDraft: setDraft, completeDay: completeDay,
    renderQuestion: renderQuestion, feedback: feedback,
    h: h, esc: esc, card: card, stat: stat, render: render
  };
  window.Site = Site;

  async function init() {
    await initStore();
    hook('state:loaded', [state]);
    Object.keys(reg.features).forEach(function (id) {
      var f = reg.features[id];
      if (f && typeof f.init === 'function') {
        try { f.init(Site); } catch (e) { console.error('[Site] feature init ' + id, e); }
      }
    });
    hook('before:render', [PAGE, Site]);
    render();
    pill();
    document.addEventListener('visibilitychange', function () { if (document.hidden) flush(); });
    window.addEventListener('beforeunload', flush);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
