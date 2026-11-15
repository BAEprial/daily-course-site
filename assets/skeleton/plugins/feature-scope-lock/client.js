(function () {
  'use strict';

  function firstDay(concept) {
    var lecs = Site.course.lectures || [];
    for (var i = 0; i < lecs.length; i++) {
      if ((lecs[i].concepts || []).indexOf(concept) >= 0) return lecs[i].day || i + 1;
    }
    var extra = Site.course.extraConcepts || {};
    if (Object.prototype.hasOwnProperty.call(extra, concept)) return extra[concept];
    return null; // 未登记概念由 verify_site.py 报错，此处不擅自隐藏题目
  }

  Site.register('feature', 'scope-lock', {
    init: function () { /* 概念索引按需计算，不做缓存以免课程数据热更新后失效 */ },
    hooks: {
      'question:filter': function (q, day) {
        var d = firstDay(q.concept);
        return d === null || d <= day;
      }
    }
  });
})();
