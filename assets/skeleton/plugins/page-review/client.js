(function () {
  'use strict';

  Site.register('page', 'review', {
    label: '错题册', navLabel: '错题册',
    render: function (S) {
      var h = S.h;
      var list = S.state.wrongBook.filter(function (w) { return !w.mastered && !w.retired; });
      var mastered = S.state.wrongBook.filter(function (w) { return w.mastered && !w.retired; });
      var rows = list.map(function (w) {
        return h('div', { class: 'q' }, [
          h('div', { class: 'q-head' }, [
            h('span', { class: 'q-kind', text: 'Day ' + w.day }),
            h('div', { class: 'q-stem', text: w.stem || w.qid })
          ]),
          h('p', { class: 'hint', text: '答错 ' + (w.wrongCount || 1) + ' 次' + (w.lastWrong ? ' · 最近 ' + w.lastWrong.slice(0, 10) : '') }),
          h('div', { class: 'actions' }, [
            h('a', { class: 'btn small', href: 'lesson.html?day=' + w.day, text: '回到该讲重做' })
          ])
        ]);
      });
      return h('div', {}, [
        h('h1', { text: '错题册' }),
        h('p', { class: 'lead', text: '未掌握 ' + list.length + ' 题，已掌握 ' + mastered.length + ' 题。' }),
        rows.length ? h('div', { class: 'section' }, rows) : h('div', { class: 'empty', text: '暂无未掌握的错题。' })
      ]);
    }
  });
})();
