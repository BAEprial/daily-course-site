(function () {
  'use strict';

  Site.register('feature', 'mentor', {
    init: function () {
      // 导师只读这些文件；本插件不复制进度，避免多处状态不同步。
      Site.mentor = {
        facts: 'records/state.json',
        context: 'records/HANDOFF.md',
        history: 'records/teaching-log.md',
        drafts: 'records/drafts.md',
        replies: 'records/mentor-replies.json'
      };
    },
    hooks: {
      'state:loaded': function () { /* 需要按学员水平调整难度时在此接入 */ },
      'after:submit': function (q, result) {
        if (!result || result.correct !== false || !q.concept) return;
        var s = Site.state.settings;
        var weak = s.weakConcepts || {};
        weak[q.concept] = (weak[q.concept] || 0) + 1;
        s.weakConcepts = weak;
      },
      'day:complete': function () { /* 追加 teaching-log.md 由导师在对话中完成 */ }
    }
  });
})();
