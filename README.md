# Research Hub · AI Agent & DevTools 调研中心

按统一五段式结构（**结论 → 核心能力 → 应用场景 → 风险与缓解 → 来源**）系统拆解 AI Agent 与开发者工具，覆盖能力、应用价值与安全风险。

**线上**：https://lee-jet.github.io/hotspot_survey/

---

## ⚡ Quick Start —— 加一个新工具

```bash
bash tools/hub.sh https://github.com/owner/tool
```

90 秒内：抓 README → 调 LLM 写五段式 → 注入 index → 提交 → CI 部署 → 上线。

批量：
```bash
bash tools/hub.sh \
    https://github.com/o1/repo1 \
    https://github.com/o2/repo2 \
    --yes
```

详见 [`tools/README.md`](tools/README.md)。

---

## 目录结构

```
hotspot_survey/
├── index.html                # 主页（手写 hero/pillars + 三块 AUTO 区域）
├── reports/                  # 子报告（按 slug 命名）
│   ├── feishu-cli.html       # ⎫
│   ├── ruview.html           # ⎬ 每份顶部含 hub:* meta，
│   ├── warp.html             # ⎪ 是 merge.py 的输入契约
│   ├── planning-with-files.html
│   ├── ralph.html
│   ├── agent-reach.html
│   ├── playwright-mcp.html
│   ├── mattpocock-skills.html
│   └── codegraph.html        # ⎭
├── assets/
│   └── report.css            # 统一设计系统（深色 hero + 卡片 + scroll-reveal）
├── tools/                    # 自动化脚本（见 tools/README.md）
│   ├── hub.sh                #    总管 = generate → lint → merge → 确认 → ship
│   ├── generate.py           #    步骤 1 · URL → reports/<slug>.html（LLM 填充）
│   ├── merge.py              #    步骤 2 · 重建 index AUTO 区域；--lint 质量门
│   ├── ship.sh               #    步骤 3 · git commit + push
│   ├── _common.py            #    共用：meta 解析 / AUTO 替换 / glyph 字典
│   └── README.md             #    工具链文档
├── .github/workflows/
│   ├── deploy.yml            # push → GitHub Pages 自动部署
│   └── lint.yml              # PR/push → meta 校验 + 质量门 + drift 检测
├── _redirects                # Cloudflare Pages 旧路径 301（GH Pages 上无效）
├── _headers                  # Cloudflare Pages 安全/缓存头
├── .nojekyll                 # GitHub Pages：禁用 Jekyll
├── .gitignore                # __pycache__ / trash 等
├── robots.txt
└── trash/                    # 已弃用文件（不部署）
```

所有内部链接相对路径 → 根域名 (`example.com/`) 和子路径 (`user.github.io/repo/`) 都兼容。

---

## 内容创作流程

完整三步独立工具链（也可通过 `hub.sh` 一键串联）：

```
你输入 URL  ──►  generate.py  ──►  reports/<slug>.html
                  抓 README + 调 LLM
                  按结构产 5 段内容
                              │
                              ▼
                       merge.py
                       重建 index.html 三处 AUTO 区域
                       （cards / matrix / kpi）
                              │
                              ▼
                       ship.sh
                       git add（白名单）→ commit → push
                              │
                              ▼
                       GitHub Actions
                       lint.yml（质量门）+ deploy.yml（上线）
                              │
                              ▼
                       https://lee-jet.github.io/hotspot_survey/
```

每个子报告 `<head>` 内含 14 个 `hub:*` meta 标签（slug / title / topic / summary / cover / theme / pills / glyph / order / matrix-* / status），是 merge.py 重建 index 的输入契约。详见 [`tools/README.md`](tools/README.md) 中的 meta schema。

---

## 部署方式

### A. GitHub Pages（推荐 · 已在用）

仓库 → **Settings** → **Pages** → **Source** 选 **GitHub Actions**。
push 到 `main` 后 `.github/workflows/deploy.yml` 自动跑，30 秒上线。

> 首次部署如果报 `Get Pages site failed`，是因为 `configure-pages` 需要 `enablement: true`（本仓库已设置好）。

### B. Cloudflare Pages

#### B1. Direct Upload（最快）

Dashboard → **Pages** → **Create a project** → **Direct Upload** → 拖入本目录 → Build output directory 留空 → Deploy。

#### B2. Wrangler CLI

```bash
npm i -g wrangler
wrangler login
wrangler pages deploy . --project-name research-hub --branch main
```

#### B3. Git 集成

| Setting | Value |
| --- | --- |
| Framework preset | None |
| Build command | _(empty)_ |
| Build output directory | `.`（本目录） |

> CF Pages 会自动读取 `_redirects` + `_headers`。

### C. 本地预览

```bash
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080/
```

---

## 兼容矩阵

| 能力 | GitHub Pages | Cloudflare Pages | 本地 http.server |
| --- | :---: | :---: | :---: |
| 静态 HTML/CSS | ✅ | ✅ | ✅ |
| 相对路径子路径部署 | ✅ | ✅ | ✅ |
| `_redirects` 301 跳转 | ❌（被忽略） | ✅ | ❌ |
| `_headers` 安全头/缓存 | ❌（被忽略） | ✅ | ❌ |
| GitHub Actions 自动部署 | ✅ | — | — |
| Git 集成自动部署 | — | ✅ | — |
| 自定义域名 + HTTPS | ✅ | ✅ | — |

---

## 维护场景速查

| 想做的事 | 命令 |
| --- | --- |
| 加一个新工具 | `bash tools/hub.sh <URL>` |
| 批量加多个工具（一次 push） | `bash tools/hub.sh <URL1> <URL2> … --yes` |
| 手工改了某份报告，想同步首页并推送 | `bash tools/hub.sh` |
| 草稿模式（不进首页、不推送） | `bash tools/hub.sh <URL> --draft --no-push` |
| 离线 / 不想用 LLM | `bash tools/hub.sh <URL> --no-llm` |
| 只想看质量门有没有过 | `python3 tools/merge.py --lint` |
| 只想看 merge 会改什么 | `python3 tools/merge.py --dry-run` |
| 校验 meta 完整 | `python3 tools/merge.py --check` |
| 改样式（CSS 调整）后重新部署 | 编辑 `assets/report.css` → `bash tools/hub.sh` |
| 删除某份报告 | `mv reports/<slug>.html trash/ && bash tools/hub.sh` |

---

## SEO

分两层：站点（被 Google/Bing 索引）+ 仓库（在 github.com 内被搜索）。

### A. 站点 SEO（已自动化）

每次 `bash tools/hub.sh`（或单独跑 `python3 tools/merge.py`）会自动维护：

| 资产 | 来源 | 内容 |
| --- | --- | --- |
| **每页 `<head>` 内 AUTO:seo 块** | hub:* meta | description / keywords / canonical / OG / Twitter Card / JSON-LD Article |
| **首页 AUTO:seo 块** | `tools/_common.py` 常量 | OG website + JSON-LD WebSite + 完整 OG/Twitter 套件 |
| **sitemap.xml** | 报告文件 mtime | 1 个 index + 9 个 report 的 lastmod / changefreq / priority |
| **robots.txt** | 静态 | `Sitemap:` 指向 + 排除 `/trash/` |

可通过环境变量切换站点 URL（自定义域名时）：

```bash
HUB_SITE_URL=https://research.example.com bash tools/hub.sh
```

未设置时自动从 `git remote get-url origin` 推导，例如 `git@github.com:lee-jet/hotspot_survey.git` → `https://lee-jet.github.io/hotspot_survey`。

### B. GitHub 仓库 SEO（要手动在 UI 填）

GitHub 内搜索 / 仓库 OG 卡片靠这些字段：

| 位置 | 字段 | 建议填法 |
| --- | --- | --- |
| 仓库主页右侧 ⚙ **About** | **Description** | `按结论→能力→应用→风险→来源五段式拆解 AI Agent 与开发者工具。已收录 9 份调研。` |
| ⚙ About | **Website** | `https://lee-jet.github.io/hotspot_survey/` |
| ⚙ About | **Topics**（最多 20 个） | `ai-agent` `agentic-tools` `claude-code` `cursor` `mcp` `devtools` `research-hub` `awesome-list` `prompt-engineering` `code-graph` `playwright-mcp` `feishu-cli` `developer-tools` `security-research` `chinese-content` |
| ⚙ About | **Releases / Packages / Deployments** 三个复选框 | 至少勾 **Deployments**（链到 Pages） |
| **Settings → General → Social preview** | 1280×640 PNG 图 | 用 [shields.io](https://shields.io) 或 [og-img.vercel.app](https://og-img.vercel.app) 生成；包含项目名、tagline、关键数字。**未上传时 GitHub 会自动用 README 第一张图 + 仓库名** |
| **Settings → General** | **Description**（同步 About） | 同上 |
| **Settings → General** | ☑ **Wikis** 关闭 / ☑ **Issues** 开启 / ☑ **Discussions** 可选 | 减少噪音入口 |
| README 第一段 | — | 前 160 字符就要把价值讲清楚，会出现在 Google 搜索结果的预览里（已优化） |
| README 顶部 | badges | License / build status / last commit 等小徽章提升仓库质感（可加） |

### 一次性手动 5 分钟操作清单

1. 打开 https://github.com/lee-jet/hotspot_survey
2. 主页右上 ⚙ → 填上面表里 About 的 Description / Website / Topics → Save changes
3. Settings → General → 滚到 **Social preview** → Upload an image（如无可暂跳过 —— Pages 部署后 OG 会先用站点的）
4. Settings → General → 顶部 Description 同步一份（与 About 同）
5. 完成后访问 https://github.com/lee-jet/hotspot_survey/community 看 Community Standards 完成度

### 验收

| 检查项 | 方法 |
| --- | --- |
| 站点 sitemap | 浏览器开 `<SITE_URL>/sitemap.xml` 应看到 10 个 `<url>` |
| robots | 开 `<SITE_URL>/robots.txt` 应有 `Sitemap:` 指向 |
| OG 预览 | 把任一报告 URL 贴到 https://www.opengraph.xyz/ 看渲染效果 |
| Google 索引 | 部署后 1–7 天去 https://search.google.com/search-console 提交站点；用 `site:lee-jet.github.io/hotspot_survey` 查收录 |
| GitHub 内搜 | `topic:ai-agent` 等关键词在 github.com 搜索能命中 |

---

## 系统约束

- **生成需要联网**：generate.py 要访问 `raw.githubusercontent.com` 拿 README、`api.github.com` 拿元数据（offline 时元数据降级为"—"）、调 `claude -p` 时还要 `api.anthropic.com`
- **生成需要 `claude` CLI**：默认走 LLM 模式；没装时自动回退到 `--no-llm` 脚手架
- **CI 会拦不达标的报告**：lint.yml 要求 `sources ≥ 3`、无 TODO 残留、内部链接不破、index 与 reports 同步
- **手写区与自动区分离**：merge.py 只动 `<!-- AUTO:cards|matrix|kpi -->` 三块，hero / pillars / 研究边界 / footer 永远不动

详见 [`tools/README.md`](tools/README.md)。
