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
├── _redirects                # Cloudflare Pages 路由规则
├── _headers                  # Cloudflare Pages 安全/缓存头
├── .nojekyll                 # GitHub Pages：禁用 Jekyll
├── .github/workflows/        # GitHub Actions 自动部署模板
│   └── deploy.yml
├── robots.txt
└── trash/                    # 已弃用文件
```

所有内部链接均使用相对路径，因此在根域名（`example.com/`）和子路径（`username.github.io/repo/`）部署都兼容。

---

## 部署方式

### A. GitHub Pages

#### A1. 用 GitHub Actions（推荐 · 自动化）

适合把 `hotspot_survey/` 整个目录作为新仓库根目录的情况。

1. 把本目录的内容（包括 `.github/`、`.nojekyll`、`index.html` 等）推到一个新仓库的 `main` 分支
2. GitHub 仓库 → **Settings** → **Pages** → **Build and deployment** → **Source** 选 **GitHub Actions**
3. push 后 workflow 自动运行，几十秒内站点上线
4. 访问 `https://<user>.github.io/<repo>/`

如果保留当前 monorepo 结构（hotspot_survey 是子目录），把 `.github/workflows/deploy.yml` 中的 `path: "."` 改成 `path: "./claude_workspace/hotspot_survey"` 并把 workflow 文件挪到仓库根的 `.github/workflows/`。

#### A2. 用 `gh-pages` 分支（无需 Actions）

```bash
cd claude_workspace/hotspot_survey
git init -b gh-pages
git add . && git commit -m "deploy: research hub"
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin gh-pages
```

仓库 → Settings → Pages → Source 选 **Deploy from a branch** → `gh-pages` → `/ (root)` → Save。

#### A3. 用 `docs/` 文件夹

把内容拷到主仓库的 `docs/` 子目录，Settings → Pages → Source 选 `main` 分支 + `/docs` 文件夹。

> **GitHub Pages 注意事项**
> - `.nojekyll` 必须存在 —— 否则 Jekyll 会忽略所有 `_` 前缀文件/目录（包括 `_redirects`、`_headers`，虽然这两个在 GH Pages 上本就无效）
> - GH Pages 不支持服务器端重定向 / 自定义响应头；想要 301/缓存策略请用 CF Pages
> - 项目页（`<user>.github.io/<repo>/`）部署到子路径，本项目全部用相对路径所以兼容

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
| Build output directory | `claude_workspace/hotspot_survey` |

> CF Pages 会读取 `_redirects` 与 `_headers`，自动应用旧路径 301 跳转和安全头/缓存策略。

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
| 自动部署 | ✅ Actions | ✅ Git Integration | — |
| 自定义域名 + HTTPS | ✅ | ✅ | — |
