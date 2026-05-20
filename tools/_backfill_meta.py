#!/usr/bin/env python3
"""One-shot: backfill hub:* meta tags into existing 8 reports.

Idempotent — safe to re-run. Reads existing meta if present (preserves
manual edits to hub:order), otherwise uses the seed table below.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import REPORTS_DIR, parse_meta, write_meta  # noqa: E402

SEED: dict[str, dict[str, str]] = {
    "ralph": {
        "slug": "ralph",
        "title": "Ralph · 自治 AI agent loop",
        "topic": "自治循环",
        "summary": "PRD → JSON 任务、fresh context 隔离、git/progress 记忆、危险权限参数与质量门禁；最具影响力，也最需要风险护栏。",
        "cover": "https://raw.githubusercontent.com/snarktank/ralph/main/ralph-flowchart.png",
        "theme": "theme-ralph",
        "pills": "Agent loop|violet;High risk|rose",
        "glyph": "loop",
        "order": "1",
        "matrix-subject": "自治编码循环",
        "matrix-question": "如何让多个新上下文 Agent 按 PRD 连续完成故事。",
        "matrix-risk": "危险权限、错误累积、质量门禁不足、成本失控。",
        "matrix-label": "Ralph",
        "status": "published",
    },
    "warp": {
        "slug": "warp",
        "title": "Warp",
        "topic": "终端 Agent",
        "summary": "Agentic Development Environment：终端、Warp Drive、Oz、开源贡献流程、许可证与云端上下文风险。",
        "cover": "https://github.com/user-attachments/assets/9976b2da-2edd-4604-a36c-8fd53719c6d4",
        "theme": "theme-warp",
        "pills": "Terminal|blue;Oz|violet",
        "glyph": "terminal",
        "order": "2",
        "matrix-subject": "Agentic 开发入口",
        "matrix-question": "终端、Agent、Drive、Oz 如何组合成开发环境。",
        "matrix-risk": "终端权限、云端上下文、许可证、自动化 review 偏差。",
        "matrix-label": "Warp",
        "status": "published",
    },
    "feishu-cli": {
        "slug": "feishu-cli",
        "title": "飞书 CLI 与 Claude Code",
        "topic": "办公自动化",
        "summary": "官方 larksuite/cli 与社区 riba2534/feishu-cli 对比：文档、Sheets/Base、消息卡片与 Token 风险。",
        "cover": "https://opengraph.githubassets.com/feishu-cli-hub/larksuite/cli",
        "theme": "theme-feishu",
        "pills": "Feishu|blue;Token risk|rose",
        "glyph": "chat",
        "order": "3",
        "matrix-subject": "办公自动化与企业数据",
        "matrix-question": "Claude Code 如何读取、生成、发送和存储飞书内容。",
        "matrix-risk": "个人 token、app secret、权限过宽、prompt injection。",
        "matrix-label": "飞书 CLI",
        "status": "published",
    },
    "playwright-mcp": {
        "slug": "playwright-mcp",
        "title": "Playwright MCP",
        "topic": "浏览器自动化",
        "summary": "结构化页面快照、网页交互、调试工具与安全边界。",
        "cover": "https://opengraph.githubassets.com/playwright-mcp-hub/microsoft/playwright-mcp",
        "theme": "theme-playwright",
        "pills": "MCP|amber",
        "glyph": "browser",
        "order": "4",
        "matrix-subject": "浏览器自动化",
        "matrix-question": "如何让 MCP 客户端通过结构化页面快照操作浏览器并做验证。",
        "matrix-risk": "登录态泄露、文件访问、网络越界、npx @latest 供应链。",
        "matrix-label": "Playwright MCP",
        "status": "published",
    },
    "agent-reach": {
        "slug": "agent-reach",
        "title": "Agent Reach",
        "topic": "互联网工具",
        "summary": "网页、社媒、视频、RSS、GitHub 读取与搜索工具；Cookie 与抓取合规风险。",
        "cover": "https://opengraph.githubassets.com/agent-reach-hub/Panniantong/Agent-Reach",
        "theme": "theme-reach",
        "pills": "Cookie risk|rose",
        "glyph": "globe",
        "order": "5",
        "matrix-subject": "Agent 互联网能力",
        "matrix-question": "如何给 Agent 安装网页、社媒、视频、RSS、GitHub 读取与搜索工具。",
        "matrix-risk": "Cookie 登录态、抓取合规、上游工具供应链、工作区污染。",
        "matrix-label": "Agent Reach",
        "status": "published",
    },
    "planning-with-files": {
        "slug": "planning-with-files",
        "title": "Planning with Files",
        "topic": "长任务记忆",
        "summary": "持久化 Markdown 计划：task_plan / findings / progress / hooks。",
        "cover": "https://raw.githubusercontent.com/OthmanAdi/planning-with-files/master/media/banner.png",
        "theme": "theme-planning",
        "pills": "Hooks|amber",
        "glyph": "file",
        "order": "6",
        "matrix-subject": "长期任务记忆",
        "matrix-question": "如何用文件弥补上下文窗口记忆不足。",
        "matrix-risk": "计划文件注入、hook 脚本、敏感信息落盘。",
        "matrix-label": "Planning with Files",
        "status": "published",
    },
    "ruview": {
        "slug": "ruview",
        "title": "RuView",
        "topic": "WiFi 感知",
        "summary": "WiFi CSI/RSSI 感知平台：硬件门槛（ESP32-S3）、Claude/Codex 插件、隐私与误判风险。",
        "cover": "https://raw.githubusercontent.com/ruvnet/RuView/main/assets/v2-screen.png",
        "theme": "theme-ruview",
        "pills": "ESP32-S3|green;Beta|amber",
        "glyph": "wifi",
        "order": "7",
        "matrix-subject": "空间感知与硬件实验",
        "matrix-question": "WiFi 信号能否在目标环境中稳定感知人和生命体征。",
        "matrix-risk": "隐私合规、误判、API 暴露、硬件和模型泛化。",
        "matrix-label": "RuView",
        "status": "published",
    },
    "mattpocock-skills": {
        "slug": "mattpocock-skills",
        "title": "Matt Pocock Skills",
        "topic": "工程实践",
        "summary": "真实工程导向的可组合 Agent skills：需求对齐、领域语言、TDD、诊断、架构改善、issue 拆解与交接。",
        "cover": "https://res.cloudinary.com/total-typescript/image/upload/v1777382277/skill-repo-light_2x.png",
        "theme": "theme-mattpocock",
        "pills": "Skills|violet;Engineering|green",
        "glyph": "skill",
        "order": "8",
        "matrix-subject": "工程实践技能",
        "matrix-question": "如何用小而可组合的技能强化需求对齐、TDD、诊断和架构维护。",
        "matrix-risk": "文档过期、流程依赖人类判断、技能安装供应链、hooks 误配置。",
        "matrix-label": "Matt Pocock Skills",
        "status": "published",
    },
}


def main() -> int:
    touched = 0
    for slug, seed in SEED.items():
        path = REPORTS_DIR / f"{slug}.html"
        if not path.exists():
            print(f"SKIP {slug}: {path} not found")
            continue
        existing = parse_meta(path)
        # Preserve order if user manually changed it
        merged = {**seed, **{k: v for k, v in existing.items() if k == "order"}}
        write_meta(path, merged)
        touched += 1
        print(f"✓ {path.name}")
    print(f"\nBackfilled meta into {touched} reports.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
