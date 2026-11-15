(function () {
  'use strict';

  Site.register('page', 'playground', {
    label: '编程实验室', navLabel: '编程实验室',
    render: function (S) {
      var h = S.h;
      var info = S.config.pyodide || {};
      var ta = h('textarea', {});
      ta.value = S.state.drafts['playground-code'] || "print('Hello, world!')";
      ta.addEventListener('input', function () { S.setDraft('playground-code', ta.value); });
      var out = h('div', { class: 'code-out', text: '（尚未运行）' });
      var btn = h('button', { class: 'btn primary', text: '运行' });
      btn.addEventListener('click', function () {
        if (!window.SiteCodeRunner) { out.textContent = '请先启用 q-code 插件。'; return; }
        out.textContent = '正在运行…';
        btn.disabled = true;
        window.SiteCodeRunner.run(ta.value).then(function (r) {
          out.textContent = r.out || (r.error ? r.error : '（无输出）');
        }).catch(function (e) {
          out.textContent = '运行失败：' + e.message;
        }).then(function () { btn.disabled = false; });
      });
      return h('div', {}, [
        h('h1', { text: '编程实验室' }),
        h('p', { class: 'lead', text: '浏览器内运行 Python，不需要安装环境。首次加载需联网下载运行时。' }),
        h('p', { class: 'hint', text: info.version ? '运行时版本：Pyodide ' + info.version + '（核实于 ' + (info.verifiedAt || '未标注') + '）' : '未配置运行时版本' }),
        S.card('代码', [ta, h('div', { class: 'actions' }, [btn])]),
        h('h2', { text: '输出' }),
        out
      ]);
    }
  });
})();
