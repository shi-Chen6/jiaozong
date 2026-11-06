// 极简 DOM 桩，用于在 node 里跑一遍页面逻辑做冒烟测试
const fs = require('fs');
const SRC = fs.readFileSync('_check.js', 'utf8');

function El(id) {
  return {
    id, _html: '', dataset: {}, style: { setProperty(){}, removeProperty(){} },
    classList: { _s: new Set(), add(c){this._s.add(c)}, remove(c){this._s.delete(c)},
                 toggle(c,v){v?this._s.add(c):this._s.delete(c)}, contains(c){return this._s.has(c)} },
    set innerHTML(v){ this._html = v; }, get innerHTML(){ return this._html; },
    set textContent(v){ this._html = v; }, get textContent(){ return this._html; },
    addEventListener(){}, querySelectorAll(){ return []; }, querySelector(){ return null; },
    appendChild(){}, remove(){}, focus(){}, select(){}, click(){},
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
  body: Object.assign(El('body'), { appendChild(){} }),
  addEventListener(){},
};
global.window = { addEventListener(){}, NativeBridge: null, matchMedia: () => ({matches:false}) };
global.history = { pushState(){}, };
global.location = { href: 'file:///x.html', search: '' };
global.navigator = { userAgent: 'node' };
global.URL = { createObjectURL: () => 'blob:', revokeObjectURL(){} };
global.Blob = class {};

const src = SRC;
try {
  new Function(src)();
} catch (e) {
  console.log('!! 初始化报错:', e.message);
  process.exit(1);
}
console.log('初始化 OK');

// 直接调用内部函数需要拿到作用域，改为重新构造并暴露
const wrapped = src + `
;globalThis.__t = { DATA, PROGRESS, viewHome, renderStudy, startStudy, render,
  get VIEW(){return VIEW}, set VIEW(v){VIEW=v}, findQ, chapStat, secsOf, globalStat };
`;
new Function(wrapped)();
const t = globalThis.__t;
console.log('题量', t.DATA.total, '章', t.DATA.chapterCount, '节', t.DATA.secCount);

// 首页
const home = t.viewHome();
console.log('首页小节行数', (home.match(/class="srow"/g) || []).length);
console.log('首页含“感知觉”', home.includes('感知觉'));

// 小节练习
t.startStudy('chapter', 2, '三、注意分类');
const v = t.VIEW;
console.log('小节出题', v.list.length, '标题', v.title);
const h1 = t.renderStudy();
console.log('小节分隔条', h1.includes('class="secbar"'));

// 填空题
const c3 = t.DATA.chapters[2];
const fi = c3.qs.findIndex(q => q.t === '填空题');
t.startStudy('chapter', 3);
t.VIEW.list = [{ cn: 3, n: c3.qs[fi].n }];
t.VIEW.idx = 0;
const hf = t.renderStudy();
console.log('填空题渲染', hf.includes('fillbox'), '看参考答案按钮', hf.includes('revealFill'));

// 填空题作答流程
t.VIEW.reveal = { [c3.qs[fi].n]: true };
t.VIEW.ans = { [c3.qs[fi].n]: 'A' };
t.VIEW.checked = { [c3.qs[fi].n]: true };
const hf2 = t.renderStudy();
console.log('填空判分', hf2.includes('自评答对'), '含参考答案', hf2.includes(c3.qs[fi].r.slice(0, 2)));

// 逐题渲染全库，检查异常
let errs = 0;
t.DATA.chapters.forEach(c => {
  c.qs.forEach((q, i) => {
    t.VIEW = { mode:'chapter', cn:c.no, title:c.name, list:[{cn:c.no, n:q.n}], idx:0,
      ans:{}, checked:{}, reveal:{} };
    try { t.renderStudy(); } catch (e) { errs++; if (errs < 4) console.log('渲染失败', c.no, q.n, e.message); }
  });
});
console.log('全库渲染失败数', errs);

// 统计核查
const st = t.globalStat();
console.log('统计', JSON.stringify(st));
const secs = t.secsOf(t.DATA.chapters[1]);
console.log('第2章小节', secs.map(s => s.name + ':' + s.total).join(' | '));
