// 无浏览器冒烟测试：给页面脚本套一层极简 DOM 桩，逐题渲染一遍。
// 用法：node smoke.js 心理学刷题.html
const fs = require('fs');

const HTML = process.argv[2];
if (!HTML) { console.log('用法: node smoke.js <刷题页.html>'); process.exit(2); }

const html = fs.readFileSync(HTML, 'utf8');
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const src = blocks.find(b => b.includes('var DATA')) || blocks[blocks.length - 1];
if (!src) { console.log('!! 找不到内联脚本'); process.exit(1); }

function El(id) {
  return {
    id, _html: '', dataset: {}, style: { setProperty() {}, removeProperty() {} },
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, v) { v ? this._s.add(c) : this._s.delete(c); },
      contains(c) { return this._s.has(c); },
    },
    set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; },
    set textContent(v) { this._html = v; }, get textContent() { return this._html; },
    addEventListener() {}, querySelectorAll() { return []; }, querySelector() { return null; },
    appendChild() {}, remove() {}, focus() {}, select() {}, click() {},
    onclick: null,
  };
}

const store = {};
global.localStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: k => { delete store[k]; },
};
const els = {};
global.document = {
  documentElement: El('html'),
  getElementById: id => (els[id] = els[id] || El(id)),
  createElement: () => El('tmp'),
  body: Object.assign(El('body'), { appendChild() {} }),
  addEventListener() {}, querySelectorAll() { return []; },
};
global.window = { addEventListener() {}, NativeBridge: null, matchMedia: () => ({ matches: false }) };
global.history = { pushState() {} };
global.location = { href: 'file:///x.html', search: '' };
global.navigator = { userAgent: 'node' };
global.URL = { createObjectURL: () => 'blob:', revokeObjectURL() {} };
global.Blob = class {};

try { new Function(src)(); } catch (e) {
  console.log('!! 初始化报错:', e.message); process.exit(1);
}
console.log('初始化 OK');

const wrapped = src + `
;globalThis.__t = { DATA, PROGRESS, viewHome, renderStudy, startStudy, render,
  get VIEW(){return VIEW}, set VIEW(v){VIEW=v}, findQ, chapStat, globalStat,
  secsOf: (typeof secsOf === 'function' ? secsOf : null),
  get TAB(){return TAB}, set TAB(v){TAB=v},
  get HIST(){return HIST}, set HIST(v){HIST=v},
  get HIST_CUR(){return HIST_CUR}, set HIST_CUR(v){HIST_CUR=v},
  snapOf, archiveChapter, histOf, histCount, histTotal, viewHist,
  HIST_MAX,
  GUIDE_DATA, guideOf, hasGuide, viewGuide, gBlock, openGuide,
  gkDone, gkToggle, gkProgress,
  get GK(){return GK}, set GK(v){GK=v} };
`;
try { new Function(wrapped)(); } catch (e) {
  console.log('!! 暴露内部函数失败:', e.message); process.exit(1);
}
const t = globalThis.__t;

let fail = 0;
const ok = (cond, msg, extra) => {
  if (!cond) { fail++; console.log('  ! ' + msg, extra === undefined ? '' : extra); }
  else console.log('  ✓ ' + msg);
};

console.log(`题量 ${t.DATA.total} / 章 ${t.DATA.chapterCount} / 节 ${t.DATA.secCount}`);
ok(t.DATA.total > 0, '题库非空');

// 首页
try {
  const home = t.viewHome();
  ok(home.includes('class="chap'), '首页渲染出章卡');
  const nRow = (home.match(/class="srow"/g) || []).length;
  ok(nRow === t.DATA.secCount, `小节行数 ${nRow} = 节数 ${t.DATA.secCount}`);
  ok(home.includes('class="stog"'), '折叠按钮存在，小节默认收起');
} catch (e) { fail++; console.log('  ! 首页渲染异常:', e.message); }

// 每章 / 每节都能出题
try {
  t.DATA.chapters.forEach(c => {
    t.startStudy('chapter', c.no);
    if (t.VIEW.list.length !== c.qs.length && !t.VIEW.list.length) {
      fail++; console.log(`  ! 第${c.no}章 出题列表为空`);
    }
    const secs = [...new Set(c.qs.map(q => q.sec))];
    secs.forEach(s => {
      t.startStudy('chapter', c.no, s);
      const want = c.qs.filter(q => q.sec === s).length;
      if (t.VIEW.list.length !== want) {
        fail++; console.log(`  ! 第${c.no}章「${s}」出题 ${t.VIEW.list.length} ≠ ${want}`);
      }
    });
  });
  console.log('  ✓ 全部章 / 小节均可出题');
} catch (e) { fail++; console.log('  ! 出题异常:', e.message); }

// 逐题渲染
let errs = 0;
t.DATA.chapters.forEach(c => {
  c.qs.forEach(q => {
    t.VIEW = { mode: 'chapter', cn: c.no, title: c.name, list: [{ cn: c.no, n: q.n }],
               idx: 0, ans: {}, checked: {}, reveal: {} };
    try { t.renderStudy(); } catch (e) {
      errs++;
      if (errs <= 5) console.log('  ! 渲染失败', c.no, q.n, e.message);
    }
  });
});
ok(errs === 0, `全库 ${t.DATA.total} 题逐题渲染无异常`, errs ? `失败 ${errs}` : '');

// 作答判定：正确 / 错误两个方向都走通
try {
  const c1 = t.DATA.chapters[0];
  const q1 = c1.qs.find(q => q.t === '单项选择题') || c1.qs[0];
  const mk = ans => {
    t.VIEW = { mode: 'chapter', cn: c1.no, title: c1.name,
               list: [{ cn: c1.no, n: q1.n }], idx: 0,
               ans: { [q1.n]: ans }, checked: { [q1.n]: true }, reveal: {} };
    return t.renderStudy();
  };
  const right = mk(q1.a);
  const wrong = mk(q1.a === 'A' ? 'B' : 'A');
  ok(right.includes('你的作答'), '答对时有作答回显');
  ok(right !== wrong, '对 / 错渲染有差异（判分为真）');
} catch (e) { fail++; console.log('  ! 作答判定异常:', e.message); }

// 填空题分支
try {
  const c = t.DATA.chapters.find(c => c.qs.some(q => q.t === '填空题'));
  if (c) {
    const f = c.qs.find(q => q.t === '填空题');
    t.VIEW = { mode: 'chapter', cn: c.no, title: c.name,
               list: [{ cn: c.no, n: f.n }], idx: 0, ans: {}, checked: {}, reveal: {} };
    const h1 = t.renderStudy();
    ok(h1.includes('fillbox') && h1.includes('revealFill'), '填空题先给「看参考答案」');
    t.VIEW.reveal = { [f.n]: true };
    const h2 = t.renderStudy();
    ok(h2.includes('参考答案') && h2.includes(f.r.slice(0, 2)),
       '点开后显示参考答案');
    t.VIEW.ans = { [f.n]: 'A' }; t.VIEW.checked = { [f.n]: true };
    const h3 = t.renderStudy();
    ok(h3.includes('自评答对'), '自评答对后进判分流程');
  } else console.log('  - 本题库无填空题，跳过');
} catch (e) { fail++; console.log('  ! 填空分支异常:', e.message); }

// 统计
try {
  const st = t.globalStat();
  ok(st && typeof st === 'object', '统计可计算', JSON.stringify(st).slice(0, 80));
  const secs = t.secsOf ? t.secsOf(t.DATA.chapters[0]) : null;
  if (secs) ok(secs.length > 0, `第1章小节统计 ${secs.length} 条`);
} catch (e) { fail++; console.log('  ! 统计异常:', e.message); }

// 章节重做 + 答题历史（只在内存里跑，不落 localStorage）
try {
  const c = t.DATA.chapters[0];
  const p = { idx: 0, ans: {}, chk: {} };
  c.qs.slice(0, 6).forEach((q, i) => {
    p.ans[q.n] = (i % 2 === 0) ? q.a : (q.a === 'A' ? 'B' : 'A');
    p.chk[q.n] = true;
  });
  t.PROGRESS[c.no] = p;

  // 存档：条数、正确数、逐题作答
  const snap = t.snapOf(c.no);
  ok(snap && snap.done === 6 && snap.total === c.qs.length, '快照统计已作答题数',
     `done=${snap && snap.done}`);
  ok(snap && snap.correct === 3 && snap.acc === 50, '快照正确数与正确率',
     `correct=${snap && snap.correct} acc=${snap && snap.acc}`);
  ok(snap && Object.keys(snap.ans).length === 6, '快照含逐题作答');

  // 上限 5 条、新的在前
  for (let i = 0; i < 7; i++) t.archiveChapter(c.no);
  const arr = t.histOf(c.no);
  ok(arr.length === 5, '历史每章最多 5 条', `实际 ${arr.length}`);
  ok(arr.every((x, i) => i === 0 || arr[i - 1].at >= x.at), '历史按时间新→旧排列');

  // 首页出现「历史 N」按钮
  t.TAB = 'home'; t.VIEW = null;
  const home = t.viewHome();
  ok(home.includes('data-hist='), '章卡出现「历史」按钮');
  ok(home.includes('data-redo='), '章卡出现「重做」按钮');

  // 历史列表 / 明细 / 只看错题
  t.HIST_CUR = { cn: c.no, at: 0, wrongOnly: false };
  const listHtml = t.viewHist();
  ok(listHtml.includes('data-hsnap='), '历史列表渲染出条目');
  t.HIST_CUR.at = arr[0].at;
  const det = t.viewHist();
  ok(det.includes('hitem') && det.includes('你的'), '历史明细显示逐题作答');
  t.HIST_CUR.wrongOnly = true;
  const det2 = t.viewHist();
  const n1 = (det.match(/class="hitem/g) || []).length;
  const n2 = (det2.match(/class="hitem/g) || []).length;
  ok(n2 === snap.done - snap.correct && n2 < n1, '「只看错题」行数 = 答错数',
     `全部 ${n1} / 只看错题 ${n2}`);

  // 清理，避免影响后续断言
  t.PROGRESS = {}; t.HIST = {}; t.HIST_CUR = { cn: 0, at: 0, wrongOnly: false };
} catch (e) { fail++; console.log('  ! 重做 / 历史异常:', e.message); }

// 先导知识
try {
  const gd = t.GUIDE_DATA || {};
  const chs = Object.keys(gd);
  console.log(`先导知识 ${chs.length} 章`);
  if (!chs.length) {
    console.log('  · 本页无先导知识，跳过');
  } else {
    let nSec = 0, nBlk = 0, nTab = 0, nKj = 0;
    chs.forEach(k => {
      const g = t.guideOf(+k);
      if (!g) { fail++; console.log(`  ! 第${k}章 guideOf 取不到`); return; }
      g.secs.forEach((s, si) => {
        nSec++;
        t.openGuide(+k, si);
        const h = t.viewGuide();
        if (!h || h.length < 100) { fail++; console.log(`  ! 第${k}章第${si + 1}节 渲染过短`); }
        if (!h.includes('考点地图')) { fail++; console.log(`  ! 第${k}章第${si + 1}节 缺考点地图`); }
        // 只有一节时页面不渲染小节胶囊（一个胶囊没意义），其余情况必须齐全
        const chips = (h.match(/data-gsec=/g) || []).length;
        const wantChips = g.secs.length > 1 ? g.secs.length : 0;
        if (chips !== wantChips) {
          fail++; console.log(`  ! 第${k}章第${si + 1}节 胶囊数 ${chips} ≠ ${g.secs.length}`);
        }
        (s.blocks || []).forEach(b => {
          nBlk++;
          if (b.k === 'table') nTab++;
          if (b.k === 'kj') nKj++;
          const one = t.gBlock(b);
          if (/undefined|\[object Object\]|NaN/.test(one)) {
            fail++; console.log(`  ! 第${k}章第${si + 1}节 ${b.k} 块渲染异常`, one.slice(0, 60));
          }
        });
      });
    });
    console.log(`  ✓ 全部 ${nSec} 节 / ${nBlk} 块可渲染（表 ${nTab} / 口诀 ${nKj}）`);

    // 口诀速查只出现在有口诀的章
    Object.keys(gd).forEach(k => {
      const g = t.guideOf(+k);
      const has = g.secs.some(s => (s.blocks || []).some(b => b.k === 'kj'));
      t.openGuide(+k, 0);
      const h = t.viewGuide();
      ok(h.includes('本章口诀速查') === has, `第${k}章口诀速查 ${has ? '有' : '无'}`);
    });

    // 背诵勾选写入 localStorage 且可取消
    const c0 = +chs[0];
    t.GK = {};
    t.openGuide(c0, 0);
    t.gkToggle(c0, 0);
    ok(t.gkDone(c0, 0) === true, '勾选后状态为已背');
    const gkey = Object.keys(store).find(k => k.endsWith('_v1_guide'));
    ok(!!gkey && /c\d+s\d+/.test(store[gkey]),
      '背诵进度写入 localStorage', gkey || '(没写进去)');
    ok(t.gkProgress(c0).done === 1, '进度统计 done=1', JSON.stringify(t.gkProgress(c0)));
    t.gkToggle(c0, 0);
    ok(t.gkDone(c0, 0) === false && t.gkProgress(c0).done === 0, '再点一次可取消');

    // 首页章卡出现「先导」按钮
    t.TAB = 'home'; t.VIEW = null;
    const home2 = t.viewHome();
    ok(home2.includes('data-guide='), '章卡出现「先导」按钮');
  }
} catch (e) { fail++; console.log('  ! 先导知识异常:', e.message); }

console.log(fail ? `\n== 冒烟测试 ${fail} 项未通过` : '\n== 冒烟测试全部通过');
process.exit(fail ? 1 : 0);
