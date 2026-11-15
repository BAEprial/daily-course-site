(function () {
  'use strict';

  Site.register('question-type', 'judge', {
    label: '判断',
    autoGrade: true,
    grade: function (q, answer) {
      var want = (q.answer || [])[0];
      return { correct: Array.isArray(answer) && answer.length === 1 && answer[0] === want };
    },
    render: function (q, ctx) {
      var h = ctx.h;
      var chosen = Array.isArray(ctx.answer) ? ctx.answer[0] : null;
      var opts = h('div', { class: 'opts' });
      var box = h('div', { class: 'q' }, [
        h('div', { class: 'q-head' }, [
          h('span', { class: 'q-kind', text: '判断题' }),
          h('div', { class: 'q-stem', text: q.stem })
        ]),
        opts
      ]);
      (q.options || ['正确', '错误']).forEach(function (text, i) {
        var cls = 'opt';
        if (ctx.locked) {
          cls += ' locked';
          if (i === (q.answer || [])[0]) cls += ' correct';
          else if (i === chosen) cls += ' wrong';
          if (i === chosen) cls += ' chosen';
        }
        var o = h('label', { class: cls }, [
          h('span', { class: 'letter', text: i === 0 ? 'T' : 'F' }),
          h('span', { text: text })
        ]);
        if (!ctx.locked) {
          o.addEventListener('click', function () { ctx.submit([i]); ctx.reload(); });
        }
        opts.appendChild(o);
      });
      if (ctx.locked) {
        box.appendChild(ctx.feedback(q, { correct: Site.progressOf(q.day).correct[q.id] === true }));
        box.appendChild(h('div', { class: 'actions' }, [
          h('button', { class: 'btn small', text: '重做', onclick: ctx.retry })
        ]));
      }
      return box;
    }
  });
})();
