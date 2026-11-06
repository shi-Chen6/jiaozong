# 心理学 · 刷题

教师招聘／特岗「教育综合知识」中**心理学**部分的分章节题库网页。单文件离线版，双击即可用，也可以直接发微信打开。

- **题量**：2239 题 · 34 章 · 79 节，全部配四段式解析（考点定位 / 选项辨析 / 正确答案 / 记忆口诀）
- **题型**：单选、多选、判断、填空
- **来源**：超格教育《心理学》全套课件与章节练习题（167 个 PDF/DOCX），逐页转录后归并
- **页面**：`心理学刷题.html`（约 4.8 MB，自包含，无外部依赖）

## 直接打开

| 方式 | 说明 |
| --- | --- |
| 下载 `心理学刷题.html` 双击 | 完全离线，建议 Chrome / Edge / Safari |
| 打开 `index.html` | 跳转到上面的页面（供 GitHub Pages 目录索引使用） |

移动端按 430px 版式设计，桌面端居中显示，功能一致。

## 功能

- 章节进度、章节重做、答题历史回溯
- 错题本、收藏夹、成绩统计
- 全文搜索（题干 / 解析 / 知识点）
- 每章「考点速览」先导知识卡，关键图表以 base64 内嵌，离线可看
- 答题记录存在浏览器 localStorage，换设备不互通

## 目录结构

```
xinlixue/
├─ 心理学刷题.html        交付物：单文件离线刷题页
├─ index.html             跳转页（Pages 目录索引）
├─ 心理学习题数据.json     题库数据：34 章 / 79 节 / 2239 题 + 解析
├─ quiz.json              早期题库草案（保留备查）
├─ 题库校验报告.md         逐章题量统计 + 一致性校验结果
├─ 资料归并说明.md         课件 → 题目的归并口径与取舍记录
├─ guide/                 NN.py：每章「考点速览」知识卡数据源（导出 GUIDE）
├─ ana/                   NN.py：每章逐题解析文案（ANA 列表，条数须与题量一致）
├─ src/                   课件逐章转录稿（md，题目抽取的输入）
├─ quiz.json              构建清单：34 章的 src / ana / guide 三路文件对应关系
├─ build/                 构建与校验脚本（单文件页由它生成）
│  ├─ scripts/build.py    配置 + 题目 + 解析 + 知识卡 + 模板 → 单文件 HTML
│  ├─ scripts/verify.py   题库一致性校验，产出校验报告
│  ├─ scripts/parse.py    题目文本解析（被 build.py 引用）
│  ├─ scripts/smoke.js    极简 DOM 桩，在 node 里跑一遍页面逻辑
│  └─ assets/template.html 页面模板（样式与前端逻辑全在这里）
├─ tools/                 抽取、报告、截图等辅助脚本
└─ _ext/
   ├─ GUIDE_SPEC.md       知识卡数据格式规范
   ├─ T_SPEC.md           逐页转录格式规范
   ├─ t/                  课件逐页转录稿
   ├─ gimg/               先导卡插图源图（压缩后由构建脚本转 base64）
   ├─ sel_all.py          知识点页筛选（PyMuPDF 解析 + 内容哈希去重）
   ├─ render_all.py       按筛选结果渲染整页 PNG
   └─ gimg_add.py         页面图入库并预压缩
```

## 生产流程

```
F:/xinli 课件 PDF ──render_all.py──▶ 页面 PNG ──转录──▶ _ext/t/*.md
                                                      │
                                    src/*.md ◀────────┘
                                        │
                            quiz.json (src/ana/guide 三路对应)
                                        │
                     ┌──────────────────┼──────────────────┐
                 src/*.md            ana/N.py           guide/N.py
                 题目与选项           逐题解析           先导知识卡
                     └──────────────────┼──────────────────┘
                                        ▼
                        build/scripts/build.py  ──▶  心理学刷题.html
                                                   + 心理学习题数据.json
                                        │
                        build/scripts/verify.py ──▶  题库校验报告.md
```

重建只需两条命令（在 `xinlixue/` 目录下）：

```bash
python build/scripts/build.py quiz.json      # 生成 HTML + JSON
python build/scripts/verify.py 心理学刷题.html -o 题库校验报告.md
```

当前仓库内容重建结果与已发布页面**字节一致**（md5 `c75de8fb…`），校验结果：2239 题 / 34 章 / 79 节，先导知识 34 章 100 节 1435 块（329 表、286 口诀、7 插图），一致性异常 0 处。

依赖：Python 3.9+、Pillow（插图压缩）、PyMuPDF（课件渲染）、node（冒烟测试）、playwright（截图自检）。

`build/` 下的脚本与模板来自本地 `quiz-web-builder` 工具链，随仓库固定一份，保证不装该技能也能离线重建。

交付前固定三步自检：

1. `python build/scripts/verify.py 心理学刷题.html -o 题库校验报告.md`，一致性异常必须为 0
2. 从 HTML 提取内联脚本为 `_check.js`，`node build/scripts/smoke.js` 全库渲染冒烟，失败数 0
3. `python tools/shot.py` 430px 分段截图，逐屏检查版式与 JS 报错

## 入库口径

- 章节练习汇总优先；授课课件里的配套习题不重复搬
- 只收单选／多选／判断／填空，材料题与简答另册
- 答案按「区间 + 题号」对齐，不信 PDF token 顺序（跨页会错位）
- 答案不可靠的题直接丢弃，在 `_import/report.json` 留痕
- 完全重复（题干 + 选项一致）合并，同题干不同选项保留

## 未入库的大体积素材

`_ext/p3/`（课件逐页截图 1.2 GB）、`_ext/sel/`、`_ext/txt/` 等为构建中间产物，已在 `.gitignore` 中排除；需要时用 `_ext/sel_all.py` + `_ext/render_all.py` 从原始课件重新生成。

## 版权说明

题目与解析整理自超格教育公开课件的授课内容，仅供个人学习备考使用，请勿用于商业用途。
