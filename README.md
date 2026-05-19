# Research Hub · AI Agent & DevTools 调研中心

## 目录结构

```
hotspot_survey/
├── index.html                # 主页（总览）
├── reports/                  # 子报告（独立目录）
│   ├── feishu-cli.html
│   ├── ruview.html
│   ├── warp.html
│   ├── planning-with-files.html
│   ├── ralph.html
│   ├── agent-reach.html
│   ├── playwright-mcp.html
│   └── mattpocock-skills.html
├── assets/
│   └── report.css            # 统一设计系统
├── _redirects                # 旧路径 → 新路径 + 主页规则
├── _headers                  # 安全头 + 缓存策略
├── robots.txt
└── trash/                    # 已弃用文件（如旧 readme.html）
```

## 部署到 Cloudflare Pages

### A. Direct Upload（最快）

Cloudflare Dashboard → **Pages** → **Create a project** → **Direct Upload** →
拖入本目录 → Build output directory 留空 → Deploy。

### B. Wrangler CLI

```bash
npm i -g wrangler
wrangler login
wrangler pages deploy . --project-name research-hub --branch main
```

### C. Git 集成

| Setting | Value |
| --- | --- |
| Framework preset | None |
| Build command | _(empty)_ |
| Build output directory | `claude_workspace/hotspot_survey` |

## 本地预览

```bash
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080/
```

## 旧链接兼容

通过 `_redirects` 自动 301 跳转：

| 旧路径 | 新路径 |
| --- | --- |
| `/readme.html` | `/` |
| `/feishu-cli-claude-code.html` | `/reports/feishu-cli.html` |
| `/ruview-report.html` | `/reports/ruview.html` |
| ⋯ | ⋯ |
