(function () {
  'use strict';

  Site.register('page', 'index', {
    label: '今日任务', navLabel: '今日',
    render: function (S) {
      var h = S.h, n = S.currentDay(), lec = S.lectureOf(n);
      var done = Object.keys(S.state.progress).filter(function (k) {
        return S.state.progress[k] && S.state.progress[k].done;
      }).length;
      var plan = S.config.plan || S.course.dailyPlan || [];
      var points = (lec && lec.points) ? lec.points.map(function (p) { return h('li', { text: p }); }) : [];
      return h('div', {}, [
        h('h1', { text: 'Day ' + n + ' · ' + (lec ? lec.zh : '课程已结束') }),
        h('p', { class: 'lead', text: '每天一讲，约 ' + S.config.dailyMinutes + ' 分钟。作答与输入会自动保存。' }),
        h('div', { class: 'grid' }, [
          S.stat(done, '已完成讲次'),
          S.stat(S.course.lectures.length, '全部讲次'),
          S.stat(S.state.attempts.length, '累计作答')
        ]),
        h('div', { class: 'actions' }, [
          h('a', { class: 'btn primary', href: 'lesson.html?day=' + n, text: '开始今日学习' }),
          h('a', { class: 'btn', href: 'catalog.html', text: '查看课程目录' })
        ]),
        S.card('今日要点', [
          points.length ? h('ul', { class: 'points' }, points) : h('p', { class: 'muted', text: '（暂无要点）' })
        ]),
        S.card('每日时间安排', plan.map(function (p) {
          return h('div', { class: 'plan-row' }, [
            h('span', { text: p.phase }),
            h('span', { class: 'mins', text: p.minutes + ' 分钟' })
          ]);
        }))
      ]);
    }
  });
})();
