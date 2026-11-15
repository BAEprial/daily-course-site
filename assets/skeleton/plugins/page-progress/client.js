(function () {
  'use strict';

  Site.register('page', 'progress', {
    label: '学习进度', navLabel: '学习进度',
    render: function (S) {
      var h = S.h, total = S.course.lectures.length;
      var done = Object.keys(S.state.progress).filter(function (k) {
        return S.state.progress[k] && S.state.progress[k].done;
      }).length;
      var graded = S.state.attempts.filter(function (a) { return typeof a.correct === 'boolean'; });
      var correct = graded.filter(function (a) { return a.correct; }).length;
      var rate = graded.length ? Math.round(correct / graded.length * 100) + '%' : '—';
      var bars = S.course.lectures.map(function (lec, i) {
        var n = lec.day || i + 1;
        var p = S.state.progress[S.day(n).id] || {};
        var all = S.questionsOf(n).length || 1;
        var got = Object.keys(p.answers || {}).length;
        var pct = Math.min(100, Math.round(got / all * 100));
        return h('div', { class: 'card tight' }, [
          h('div', { class: 'plan-row' }, [
            h('span', { text: 'Day ' + n + ' · ' + (lec.zh || '') }),
            h('span', { class: 'mins', text: got + ' / ' + all + ' 题' })
          ]),
          h('div', { class: 'bar' }, [h('i', { style: 'width:' + pct + '%' })])
        ]);
      });
      return h('div', {}, [
        h('h1', { text: '学习进度' }),
        h('div', { class: 'grid' }, [
          S.stat(done + ' / ' + total, '已完成讲次'),
          S.stat(S.state.attempts.length, '累计作答'),
          S.stat(rate, '客观题正确率')
        ]),
        h('h2', { text: '分讲进度' }),
        h('div', { class: 'day-list' }, bars)
      ]);
    }
  });
})();
