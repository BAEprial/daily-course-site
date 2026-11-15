(function () {
  'use strict';

  Site.register('page', 'notes', {
    label: '简述与笔记', navLabel: '笔记',
    render: function (S) {
      var h = S.h;
      var briefs = S.state.briefs || {};
      var entries = Object.keys(briefs).filter(function (k) { return String(briefs[k].text || '').trim(); });
      var list = entries.map(function (k) {
        return h('div', { class: 'card' }, [
          h('h3', { text: k }),
          h('p', { text: briefs[k].text }),
          h('p', { class: 'hint', text: briefs[k].selfChecked ? '已对照参考要点自评' : '尚未对照参考要点自评' })
        ]);
      });
      var ta = h('textarea', {});
      ta.value = (S.state.drafts['notes-main'] || '');
      ta.addEventListener('input', function () { S.setDraft('notes-main', ta.value); });
      var replyBox = h('div', { class: 'empty', text: '（暂无导师回信）' });
      fetch('records/mentor-replies.json', { cache: 'no-store' }).then(function (r) {
        return r.ok ? r.json() : null;
      }).then(function (data) {
        if (!data || !data.length) return;
        replyBox.className = '';
        replyBox.innerHTML = '';
        data.forEach(function (m) {
          replyBox.appendChild(h('div', { class: 'card soft' }, [
            h('h3', { text: m.title || '导师回信' }),
            h('p', { text: m.body || '' })
          ]));
        });
      }).catch(function () { /* 文件不存在时保持空态 */ });
      return h('div', {}, [
        h('h1', { text: '简述与笔记' }),
        h('p', { class: 'lead', text: '输入内容实时落盘，写到一半关闭页面也不会丢失。' }),
        h('h2', { text: '简述题答案' }),
        list.length ? h('div', { class: 'section' }, list) : h('div', { class: 'empty', text: '（暂无）' }),
        S.card('笔记', [ta]),
        h('h2', { text: '导师回信' }),
        replyBox
      ]);
    }
  });
})();
