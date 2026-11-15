(function () {
  'use strict';

  Site.register('question-type', 'brief', {
    label: '简述',
    autoGrade: false,
    grade: function () { return null; },
    render: function (q, ctx) {
      var h = ctx.h;
      var text = typeof ctx.answer === 'string' ? ctx.answer : (ctx.draft || '');
      var ta = h('textarea', {});
      ta.value = text;
      ta.addEventListener('input', function () { ctx.setDraft(ta.value); });
      var box = h('div', { class: 'q' }, [
        h('div', { class: 'q-head' }, [
          h('span', { class: 'q-kind', text: '简述题' }),
          h('div', { class: 'q-stem', text: q.stem })
        ]),
        ta,
        h('div', { class: 'actions' }, [
          h('button', {
            class: 'btn primary small', text: '保存作答',
            onclick: function () { ctx.submit(ta.value); ctx.reload(); }
          }),
          h('span', { class: 'hint', text: '输入内容会自动落盘，不需要点击保存也能被导师读到' })
        ])
      ]);
      var brief = Site.state.briefs[Site.day(q.day).id] || {};
      var chk = h('input', { type: 'checkbox' });
      chk.checked = !!brief.selfChecked;
      chk.addEventListener('change', function () {
        var id = Site.day(q.day).id;
        var b = Site.state.briefs[id] || { text: ta.value, selfChecked: false };
        b.selfChecked = chk.checked;
        Site.state.briefs[id] = b;
        Site.save();
      });
      box.appendChild(h('label', { class: 'hint' }, [chk, ' 已对照参考要点自评']));
      if ((q.keypoints || []).length) {
        box.appendChild(h('h3', { text: '参考要点', class: 'keypoints-title' }));
        box.appendChild(h('ul', { class: 'keypoints' }, (q.keypoints || []).map(function (k) {
          return h('li', { text: k });
        })));
      }
      if (q.guide) box.appendChild(h('p', { class: 'hint', text: q.guide }));
      return box;
    }
  });
})();
