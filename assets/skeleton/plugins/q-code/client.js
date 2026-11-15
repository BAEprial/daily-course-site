(function () {
  'use strict';

  var pyodide = null, loading = null;

  function ensure() {
    if (pyodide) return Promise.resolve(pyodide);
    if (loading) return loading;
    var c = Site.config.pyodide || {};
    if (!c.cdn) return Promise.reject(new Error('site.json 未配置 pyodide.cdn'));
    loading = new Promise(function (resolve, reject) {
      function boot() {
        if (typeof window.loadPyodide !== 'function') { reject(new Error('Pyodide 脚本未就绪')); return; }
        window.loadPyodide({ indexURL: c.cdn }).then(function (p) { pyodide = p; resolve(p); }).catch(reject);
      }
      if (typeof window.loadPyodide === 'function') boot();
      else {
        var s = document.createElement('script');
        s.src = c.cdn + 'pyodide.js';
        s.onload = boot;
        s.onerror = function () { reject(new Error('Pyodide 加载失败：' + c.cdn)); };
        document.head.appendChild(s);
      }
    });
    return loading;
  }

  function run(code) {
    var out = [];
    return ensure().then(function (p) {
      p.setStdout({ batched: function (s) { out.push(s); } });
      p.setStderr({ batched: function (s) { out.push(s); } });
      try { p.runPython(code); } catch (e) { return { out: out.join('\n'), error: String(e) }; }
      return { out: out.join('\n'), error: '' };
    });
  }

  Site.register('question-type', 'code', {
    label: '编程实操',
    autoGrade: true,
    grade: function (q, answer) {
      var j = q.judge || {};
      var got = String(answer == null ? '' : answer);
      var exp = String(j.expected == null ? '' : j.expected);
      var norm = function (s) {
        return j.looseSpace ? s.replace(/\s+/g, '') : s.replace(/\s+$/, '');
      };
      return { correct: got.length > 0 && norm(got) === norm(exp) };
    },
    render: function (q, ctx) {
      var h = ctx.h;
      var ta = h('textarea', {});
      ta.value = ctx.draft || '';
      ta.addEventListener('input', function () { ctx.setDraft(ta.value); });
      var out = h('div', { class: 'code-out', text: '（尚未运行）' });
      var fb = h('div', {});
      var btn = h('button', { class: 'btn primary', text: '运行并判题' });
      btn.addEventListener('click', function () {
        out.textContent = '正在准备运行环境…';
        btn.disabled = true;
        run(ta.value).then(function (r) {
          out.textContent = r.out || (r.error ? r.error : '（无输出）');
          var res = ctx.submit(r.error ? '' : r.out);
          fb.innerHTML = '';
          if (res) fb.appendChild(ctx.feedback(q, res));
        }).catch(function (e) {
          out.textContent = '运行环境加载失败：' + e.message;
        }).then(function () { btn.disabled = false; });
      });
      return h('div', { class: 'q' }, [
        h('div', { class: 'q-head' }, [
          h('span', { class: 'q-kind', text: '编程实操' }),
          h('div', { class: 'q-stem', text: q.stem })
        ]),
        ta,
        h('div', { class: 'actions' }, [
          btn,
          h('span', { class: 'hint', text: '首次加载需联网下载运行时，之后走浏览器缓存' })
        ]),
        out, fb
      ]);
    }
  });

  // 供 page-playground 复用同一套运行时，避免重复加载 Pyodide。
  window.SiteCodeRunner = { run: run };
})();
