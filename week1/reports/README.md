# 报告导出说明

本目录用于统一管理 `week1` 阶段核心报告的 PDF 导出脚本与导出结果。  
当前采用的不是 `pandoc + xelatex` 方案，而是：

1. `Markdown -> HTML`
2. `HTML -> Playwright / Chromium`
3. `Chromium` 无头打印为 PDF

选择这套方案的原因很直接：

- 中文排版更自然
- 图片较多的报告更容易保持原有观感
- Markdown 标题、列表、引用块、代码块的样式更接近浏览器预览效果
- 最终 PDF 看起来更像现代文档，而不是偏 LaTeX 风格的“硬排版”

---

## 1. 当前脚本

- `build_reports.py`

这个脚本负责批量导出以下 Markdown：

1. `第一版/docs/模型选型报告.md`
2. `第一版/docs/SFT训练与风险控制.md`
3. `第一版/stats/outputs/report.md`
4. `第一版/filter/outputs/report.md`
5. `第二版/01_分类效果评估与边界case分析/outputs/report.md`

导出后会直接在当前目录生成 PDF。

---

## 2. 当前方案是怎么做的

当前导出链路分成三步：

### 2.1 Markdown 转 HTML

脚本内部使用 Python 的 `markdown` 库，把每一份 `.md` 文件先转换成 HTML。  
这一步的作用是：

- 保留 Markdown 的标题层级
- 保留列表、引用块、代码块等结构
- 让后续浏览器渲染能直接接手

### 2.2 HTML 注入统一样式

脚本会给每一份 HTML 自动加上一套内嵌 CSS。  
这套样式主要控制：

- A4 页面尺寸与页边距
- 中文字体栈
- 一级到四级标题样式
- 正文行距与字号
- 列表、表格、引用块样式
- 图片最大宽度、边框、圆角、分页表现

也就是说，PDF 的观感不是浏览器默认样式，而是脚本里定制过的一套“适合中文报告打印”的样式。

### 2.3 Playwright 驱动 Chromium 打印 PDF

HTML 准备好后，脚本会调用 `Playwright` 启动无头 `Chromium` 浏览器，再执行 PDF 打印。  
这一步的好处是：

- 图片渲染更稳定
- 中文字体效果更自然
- 页面观感更接近你平时看到的网页/Markdown
- 对长文档的整体排版比纯 LaTeX 路线更直观

---

## 3. 为什么图片能正常进 PDF

`stats/outputs/report.md` 和 `filter/outputs/report.md` 里有大量相对路径图片，例如：

- `vis/train_pca.png`
- `vis/all_tfidf_top20.png`

脚本的处理方式是：

- 给每一份 HTML 自动设置 `<base href="...">`
- 让浏览器以 Markdown 文件所在目录为资源基准路径

因此这些相对图片路径在导出时可以被直接解析，不需要手工改成绝对路径。

---

## 4. 当前依赖

当前脚本依赖以下 Python 包和浏览器运行时：

### 4.1 Python 包

- `playwright`
- `markdown`

### 4.2 浏览器运行时

- `Chromium`

如果本机还没装，可以执行：

```bash
python -m pip install playwright markdown
python -m playwright install chromium
```

---

## 5. 使用方式

在 `week1/reports` 目录下执行：

```bash
python build_reports.py
```

或者在项目根目录执行：

```bash
python week1/reports/build_reports.py
```

脚本会自动：

1. 检查浏览器运行时是否存在
2. 逐份读取 Markdown
3. 转成 HTML
4. 套用统一 CSS
5. 生成 PDF

---

## 6. 输出结果

当前会生成以下 PDF：

- `中文邮政客服任务开源大模型选型研究报告.pdf`
- `中文邮政客服任务SFT训练方案与风险控制报告.pdf`
- `CSDS数据集统计分析与关键词提取结果报告.pdf`
- `邮政相关对话筛选与向量空间可视化结果报告.pdf`
- `分类效果评估与边界case分析报告.pdf`

这些 PDF 会直接落盘到 `week1/reports/` 目录。

---

## 7. 如果后面继续改报告，应该怎么用

后面如果你继续修改这四份 Markdown，本流程不需要重写。  
你只需要：

1. 改对应的 Markdown 文件
2. 重新运行：

```bash
python week1/reports/build_reports.py
```

就会得到一版新的 PDF。

也就是说，导出逻辑和报告内容是分开的：

- 报告内容在各自的 `.md`
- 导出样式和导出流程在 `build_reports.py`

---

## 8. 如果后面你只改 prompt 或某一段文本

这也是这套流程最方便的地方。

比如你后面说：

- 把 agent 的 `system prompt` 改一下
- 把模型选型结论换个写法
- 把实验目的重写
- 把某个章节标题改正式一点

那我这边的工作方式会很简单：

1. 直接改对应的 Markdown
2. 如果你要求渲染，我再运行 `build_reports.py`
3. 生成新版 PDF

也就是说，后面你只要把新的 prompt 或新的文字内容直接给我，我就可以在现有流程上继续改，不需要重新搭一套导出系统。

---

## 9. 哪些情况下需要继续调脚本

如果你后面觉得 PDF 还有这些问题，可以继续改脚本而不是改 Markdown：

- 标题太大或太小
- 页边距不合适
- 图片太宽
- 段落太松或太挤
- 表格样式不好看
- 某类报告需要更强分页控制

这些都属于 `build_reports.py` 里的 CSS 层问题。  
也就是说：

- 内容问题改 Markdown
- 排版问题改 `build_reports.py`

这样职责是分开的，后面维护会更轻松。
