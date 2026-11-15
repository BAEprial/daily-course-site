(function () {
  'use strict';

  Site.register('page', 'lesson', {
    label: '每日学习', navLabel: '学习',
    render: function (S) {
      var h = S.h, n = S.currentDay(), lec = S.lectureOf(n);
      if (!lec) return h('div', { class: 'empty', text: '没有找到该讲次。' });
      var qs = S.questionsOf(n);
      var nodes = [
        h('h1', { text: 'Day ' + n + ' · ' + lec.zh }),
        lec.url ? h('p', {}, [h('a', { href: lec.url, target: '_blank', rel: 'noopener', text: '打开课程原文' })]) : null,
        S.card('要点卡片', [
          h('ul', { class: 'points' }, (lec.points || []).map(function (p) { return h('li', { text: p }); }))
        ]),
        h('h2', { text: '当日练习（' + qs.length + ' 题）' })
      ];
      qs.forEach(function (q) { nodes.push(S.renderQuestion(q)); });
      nodes.push(h('div', { class: 'actions' }, [
        h('button', {
          class: 'btn primary', text: '完成本讲并打卡',
          onclick: function () { S.completeDay(n); S.render(); }
        }),
        h('a', { class: 'btn', href: 'catalog.html', text: '返回目录' })
      ]));
      return h('div', {}, nodes);
    }
  });
})();
