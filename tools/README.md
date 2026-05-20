# tools/ — Research Hub 工具链

四个脚本：底层三步独立 + 一个总管。

```
URL  ──►  generate.py  ──►  reports/<slug>.html        # 步骤 1
                                    │
        reports/*.html  ──►  merge.py  ──►  index.html  # 步骤 2
                                    │
                  git  ──►  ship.sh  ──►  origin/main   # 步骤 3

         ┌─────────────────────────────────────────────┐
         │  hub.sh = 1 + 2 + 3 串联（含 lint 与确认提示）│
         └─────────────────────────────────────────────┘
```

## 0. `hub.sh` —— 总管（推荐入口）

```bash
# 加一个新工具（端到端，~130 秒，提示前会让你确认）
bash tools/hub.sh https://github.com/owner/tool

# 批量入库（一次 push）
bash tools/hub.sh \
    https://github.com/o1/a \
    https://github.com/o2/b \
    https://github.com/o3/c \
    --yes

# 草稿模式（generate 完不 merge 也不 push，方便慢慢改）
bash tools/hub.sh https://github.com/owner/tool --draft --no-push

# 资料手工改完了，只想同步 + 推
bash tools/hub.sh

# 自定义 commit 信息
bash tools/hub.sh https://github.com/owner/tool -m "feat: add owner/tool"
```

| 标志 | 作用 |
|---|---|
| `-y, --yes` | 跳过 push 前确认 |
| `--no-push` | 走到 merge 就停 |
| `--no-merge` | generate 完就停 |
| `--no-llm` | 用脚手架模式（不调 LLM） |
| `--draft` | 新报告标 draft，不进索引 |
| `--overwrite` | 覆盖同 slug 报告 |
| `--order N` | 设置 hub:order |
| `-m, --message` | 自定义 commit message |

`hub.sh` 内部按顺序跑：generate（每个 URL）→ `merge.py --lint` → `merge.py` → 显示 diff → 确认 → `ship.sh`。任何一步失败立即停。

## 步骤 1 · `generate.py` —— URL → 报告脚手架

抓 GitHub 仓库元数据 + README，emit 一份带 `hub:*` meta 的 HTML 脚手架，
五段式 section（结论 / 能力 / 应用 / 风险 / 来源）为 TODO 占位。

```bash
# 最小用法
python3 tools/generate.py https://github.com/owner/repo

# 控制排序、状态、覆盖
python3 tools/generate.py https://github.com/owner/repo --order 9 --draft
python3 tools/generate.py https://github.com/owner/repo --overwrite

# 微调展示
python3 tools/generate.py https://github.com/owner/repo \
    --title "自定义标题" --topic "MCP" --pills "MCP|amber;Beta|rose"

# 矩阵行字段
python3 tools/generate.py https://github.com/owner/repo \
    --matrix-subject "浏览器自动化" \
    --matrix-question "如何用 MCP 操控浏览器" \
    --matrix-risk "登录态泄露、文件访问越界"
```

**生成后必须手工/LLM 填充五段式 TODO**，然后才能进入步骤 2。
草稿（`--draft`）会被 `merge.py` 跳过，方便先建后写。

### 网络要求

需联网访问：
- `api.github.com`（仓库元数据）
- `raw.githubusercontent.com`（README）

## 步骤 2 · `merge.py` —— 重建 index.html AUTO 区域

扫 `reports/*.html`，按 `hub:order` + `slug` 排序，重写 index.html 三个区域：

| AUTO 区域 | 渲染数据 |
| --- | --- |
| `cards` | 8 张报告卡（hub:title / topic / summary / cover / theme / pills / glyph） |
| `matrix` | 主题地图表（hub:matrix-subject / question / risk / label） |
| `kpi` | 报告数 + 总来源数（自动统计 `<a class="source-link">`） |

```bash
python3 tools/merge.py            # 写盘
python3 tools/merge.py --dry-run  # 显示 diff，不写盘
python3 tools/merge.py --check    # 只校验 meta 完整性
```

**幂等**：重复运行结果稳定；删一份报告再跑，索引自动收缩；草稿状态自动排除。

**不碰** AUTO 标记外的内容（hero、研究边界、footer 等手写部分原样保留）。

## 步骤 3 · `ship.sh` —— git commit + push

```bash
bash tools/ship.sh                         # 自动生成 commit 信息
bash tools/ship.sh "feat: add agent-reach" # 自定义信息
bash tools/ship.sh --dry-run               # 看会提交什么，不真推
```

只 stage 白名单路径：
`index.html / reports/ / assets/ / README.md / _redirects / _headers / robots.txt / .nojekyll / .github/`

避免 `trash/` 或临时实验文件被误提交。

## 常用组合

```bash
# 加一个新工具
python3 tools/generate.py https://github.com/owner/new-tool
# … 手工/LLM 填充 reports/new-tool.html …
python3 tools/merge.py && bash tools/ship.sh

# 批量入库（一次 push）
python3 tools/generate.py https://github.com/o1/r1 --order 10
python3 tools/generate.py https://github.com/o2/r2 --order 11
python3 tools/generate.py https://github.com/o3/r3 --order 12
# … 分别填充内容 …
python3 tools/merge.py && bash tools/ship.sh "batch: add r1/r2/r3"

# 只改样式不加内容
python3 tools/merge.py && bash tools/ship.sh "style: tweak design"

# 仅 review
python3 tools/generate.py https://github.com/owner/repo --draft
# 内容反复打磨
python3 tools/merge.py --dry-run   # 不进 index
```

## hub:* meta schema

子报告 `<head>` 内的元信息，所有 merge 渲染都从这里读：

| Key | 用途 | 示例 |
| --- | --- | --- |
| `hub:slug` | 唯一标识 + 文件名 | `ralph` |
| `hub:title` | 卡片大标题 | `Ralph · 自治 AI agent loop` |
| `hub:topic` | 主题胶囊 | `自治循环` |
| `hub:summary` | 卡片描述（1-2 句） | `PRD → JSON 任务…` |
| `hub:cover` | 封面图 URL | `https://raw.githubusercontent.com/...` |
| `hub:theme` | CSS 主题类 | `theme-ralph` |
| `hub:pills` | `Label|color;…` | `Agent loop|violet;High risk|rose` |
| `hub:glyph` | 右下角图标键 | `loop` / `chat` / `wifi` / ... |
| `hub:order` | 排序权重（小靠前） | `1` |
| `hub:matrix-subject` | 主题表 - 主题列 | `自治编码循环` |
| `hub:matrix-question` | 主题表 - 核心问题 | `如何让多个 Agent 按 PRD 完成故事。` |
| `hub:matrix-risk` | 主题表 - 风险 | `危险权限、错误累积…` |
| `hub:matrix-label` | 主题表 - 报告链接文字 | `Ralph` |
| `hub:status` | `published` / `draft` | `published` |

## 文件清单

| 文件 | 类型 | 用途 |
| --- | --- | --- |
| `hub.sh` | **总管入口** | 串联 generate → lint → merge → 确认 → ship |
| `generate.py` | 步骤 1 | URL → 报告（LLM 填充或脚手架） |
| `merge.py` | 步骤 2 | 重建 index AUTO 区域；`--check` / `--lint` / `--dry-run` |
| `ship.sh` | 步骤 3 | git 提交 + push（白名单 stage） |
| `_common.py` | 共用模块 | meta 解析 / AUTO 区域替换 / glyph SVG 字典 |
| `_backfill_meta.py` | 一次性 | 已有报告回填 meta（已运行） |
| `README.md` | 文档 | 本文件 |
