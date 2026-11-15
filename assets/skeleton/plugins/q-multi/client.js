(function () {
  'use strict';

  Site.register('question-type', 'multi', {
    label: '多项选择',
    autoGrade: true,
    grade: function (q, answer) {
      var want = (q.answer || []).slice().sort().join(',');
      var got = (answer || []).slice().sort().join(',');
      return { correct: got.length > 0 && got === want };
    },
    render: function (q, ctx) {
      var h = ctx.h, letters = ['A', 'B', 'C', 'D', 'E', 'F'];
      var chosen = Array.isArray(ctx.answer) ? ctx.answer.slice() : [];
      var sel = chosen.slice();
      var opts = h('div', { class: 'opts' });
      var box = h('div', { class: 'q' }, [
        h('div', { class: 'q-head' }, [
          h('span', { class: 'q-kind', text: '多项选择' }),
          h('div', { class: 'q-stem', text: q.stem })
        ]),
        opts
      ]);
      (q.options || []).forEach(function (text, i) {
        var cls = 'opt';
        if (ctx.locked) {
          cls += ' locked';
          if ((q.answer || []).indexOf(i) >= 0) cls += ' correct';
          else if (chosen.indexOf(i) >= 0) cls += ' wrong';
          if (chosen.indexOf(i) >= 0) cls += ' chosen';
        } else if (sel.indexOf(i) >= 0) {
          cls += ' chosen';
        }
        var o = h('label', { class: cls }, [
          h('span', { class: 'letter', text: letters[i] || String(i + 1) }),
          h('span', { text: text })
        ]);
        if (!ctx.locked) {
          o.addEventListener('click', function () {
            var at = sel.indexOf(i);
            if (at >= 0) sel.splice(at, 1); else sel.push(i);
            o.className = 'opt' + (sel.indexOf(i) >= 0 ? ' chosen' : '');
          });
        }
        opts.appendChild(o);
      });
      if (!ctx.locked) {
        box.appendChild(h('div', { class: 'actions' }, [
          h('button', {
            class: 'btn primary small', text: '提交答案',
            onclick: function () { if (sel.length) { ctx.submit(sel.slice()); ctx.reload(); } }
          }),
          h('span', { class: 'hint', text: '需完全选中正确答案' })
        ]));
      } else {
        box.appendChild(ctx.feedback(q, { correct: Site.progressOf(q.day).correct[q.id] === true }));
        box.appendChild(h('div', { class: 'actions' }, [
          h('button', { class: 'btn small', text: '重做', onclick: ctx.retry })
        ]));
      }
      return box;
    }
  });
})();
