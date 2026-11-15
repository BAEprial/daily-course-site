(function () {
  'use strict';

  Site.register('page', 'about', {
    label: '课程说明', navLabel: '课程说明',
    render: function (S) {
      var h = S.h, meta = S.course.meta || {}, src = S.config.source || {};
      var terms = (S.course.termNotes || []).map(function (t) {
        return h('div', { class: 'term' }, [
          h('h3', { text: t.wrong + ' → ' + t.right }),
          h('p', { class: 'muted', text: t.why || '' })
        ]);
      });
      var plan = (S.config.plan || S.course.dailyPlan || []).map(function (p) {
        return h('div', { class: 'plan-row' }, [
          h('span', { text: p.phase }),
          h('span', { class: 'mins', text: p.minutes + ' 分钟' })
        ]);
      });
      var quota = Object.keys(S.config.quota || {}).map(function (k) {
        return h('span', { class: 'tag', text: k + ' × ' + S.config.quota[k] });
      });
      return h('div', {}, [
        h('h1', { text: '课程说明' }),
        S.card('课程信息', [
          h('p', { text: meta.name || S.config.name || '' }),
          h('p', { class: 'muted', text: meta.nameEn || '' }),
          h('p', { text: (meta.lectures || S.course.lectures.length) + ' 讲 · 每日约 ' + S.config.dailyMinutes + ' 分钟' }),
          h('p', { class: 'muted', text: meta.description || '' }),
          src.name ? h('p', {}, [
            h('span', { text: '来源：' }),
            src.url ? h('a', { href: src.url, target: '_blank', rel: 'noopener', text: src.name }) : h('span', { text: src.name })
          ]) : null,
          src.verifiedAt ? h('p', { class: 'hint', text: '课程信息核实于 ' + src.verifiedAt }) : null
        ]),
        S.card('每日编排', [
          h('div', { class: 'actions' }, quota),
          h('div', { class: 'section' }, plan)
        ]),
        S.card('术语订正', terms.length ? terms : [h('p', { class: 'muted', text: '（无）' })]),
        S.card('启用的组件', [
          h('div', { class: 'actions' }, (S.config.plugins || []).map(function (id) {
            return h('span', { class: 'tag', text: id });
          }))
        ]),
        h('p', { class: 'hint', text: src.copyright || '' })
      ]);
    }
  });
})();
