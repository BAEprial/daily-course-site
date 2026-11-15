(function () {
  'use strict';

  Site.register('page', 'catalog', {
    label: '课程目录', navLabel: '课程目录',
    render: function (S) {
      var h = S.h;
      var rows = S.course.lectures.map(function (lec, i) {
        var n = lec.day || i + 1;
        var p = S.state.progress[S.day(n).id] || {};
        return h('div', { class: 'day-row' }, [
          h('span', { class: 'no', text: 'Day ' + n }),
          h('div', { class: 'body' }, [
            h('a', { class: 'zh', href: 'lesson.html?day=' + n, text: lec.zh || '' }),
            h('div', { class: 'en', text: lec.en || '' })
          ]),
          h('span', { class: 'tag' + (p.done ? ' done' : ''), text: p.done ? '已完成' : '未完成' })
        ]);
      });
      return h('div', {}, [
        h('h1', { text: '课程目录' }),
        h('p', { class: 'lead', text: '共 ' + S.course.lectures.length + ' 讲，每讲对应一个 Day。' }),
        h('div', { class: 'day-list' }, rows)
      ]);
    }
  });
})();
