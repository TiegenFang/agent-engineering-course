"""Repeatable, offline-first accessibility audit for the T32 release gate.

The audit intentionally checks source contracts rather than pretending that a
static scan is a WCAG certification.  It catches regressions that are cheap to
review in CI (labels, alternative text, live-region/fallback hooks, focus and
responsive CSS) and records the remaining manual/assistive-technology work.
No network, browser, credentials, or external accessibility service is used.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping


AUDIT_VERSION = "1"
TEXT_SUFFIXES = {".astro", ".css", ".html", ".js", ".md", ".mdx", ".mjs", ".ts", ".tsx"}
SKIP_PARTS = {".git", ".astro", ".audit", ".worktrees", "dist", "node_modules", "__pycache__"}

TAG_RE = re.compile(r"<(?P<tag>button|input|select|textarea|img|iframe)\b(?P<attrs>[^>]*?)(?:/?>)", re.IGNORECASE | re.DOTALL)
ATTR_RE = re.compile(r"(?P<name>[A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(?P<quote>[\"'])(?P<value>.*?)(?P=quote)", re.DOTALL)
ID_RE = re.compile(r"\bid\s*=\s*([\"'])([^\"']+)\1", re.IGNORECASE)
FOR_RE = re.compile(r"\bfor\s*=\s*([\"'])([^\"']+)\1", re.IGNORECASE)
INTERACTIVE_RE = re.compile(r"<(?:button|input|select|textarea)\b", re.IGNORECASE)
ARIA_NAME_RE = re.compile(r"\baria-(?:label|labelledby)\s*=", re.IGNORECASE)
LIVE_RE = re.compile(r"\baria-live\s*=|\brole\s*=\s*['\"](?:status|alert)['\"]|<output\b", re.IGNORECASE)


def _finding(check: str, severity: str, message: str, **extra: Any) -> dict[str, Any]:
    value = {"check": check, "severity": severity, "message": message}
    value.update(extra)
    return value


def _iter_files(root: Path, suffixes: set[str]) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        try:
            parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in SKIP_PARTS for part in parts):
            continue
        yield path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _attrs(attrs: str) -> dict[str, str]:
    return {match.group("name").lower(): match.group("value") for match in ATTR_RE.finditer(attrs)}


def scan_styles(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Check the shared stylesheet for the source-level accessibility hooks."""

    findings: list[dict[str, Any]] = []
    path = root / "site" / "src" / "styles" / "custom.css"
    try:
        text = _read(path)
    except (OSError, UnicodeDecodeError) as exc:
        return [_finding("style-hooks", "fail", f"shared stylesheet unavailable: {type(exc).__name__}")], {}

    required_markers = {
        "focus-visible": ":focus-visible",
        "reduced-motion": "prefers-reduced-motion",
        "responsive-media": "@media (max-width",
        "responsive-grid": "grid-template-columns",
        "touch-target": "min-height: 44px",
    }
    missing = [name for name, marker in required_markers.items() if marker not in text]
    for name in missing:
        findings.append(_finding("style-hooks", "fail", f"shared stylesheet is missing {name} hook", marker=required_markers[name]))
    return findings, {
        "path": path.relative_to(root).as_posix(),
        "bytes": len(text.encode("utf-8")),
        "markers": {name: marker in text for name, marker in required_markers.items()},
    }


def scan_markup(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Check Astro/HTML/MDX markup for high-signal accessibility regressions."""

    findings: list[dict[str, Any]] = []
    files_checked = 0
    interactive_files = 0
    fallback_files = 0
    live_region_files = 0
    interactive_tags = 0
    labelled_inputs = 0
    image_count = 0
    iframe_count = 0
    component_ids: set[str] = set()

    component_root = root / "site" / "src" / "components"
    paths = list(_iter_files(component_root, {".astro", ".html", ".mdx"})) if component_root.exists() else []
    paths.extend(_iter_files(root / "site" / "src" / "pages", {".astro", ".html", ".mdx"}))
    for path in sorted(set(paths)):
        files_checked += 1
        try:
            text = _read(path)
        except (OSError, UnicodeDecodeError):
            findings.append(_finding("markup", "fail", "markup file cannot be decoded", path=_relative(path, root)))
            continue
        relative = _relative(path, root)
        has_interactive = bool(INTERACTIVE_RE.search(text))
        if has_interactive:
            interactive_files += 1
            if "<noscript" in text.lower():
                fallback_files += 1
            if LIVE_RE.search(text):
                live_region_files += 1

        component_ids.update(match.group(2) for match in ID_RE.finditer(text))
        labels = {match.group(2) for match in FOR_RE.finditer(text)}
        for match in TAG_RE.finditer(text):
            tag = match.group("tag").lower()
            attrs = _attrs(match.group("attrs"))
            if tag in {"button", "input", "select", "textarea"}:
                interactive_tags += 1
                if tag == "input" and attrs.get("type", "").lower() in {"hidden", "submit", "button", "reset", "image"}:
                    continue
                has_name = any(key in attrs for key in ("aria-label", "aria-labelledby", "title"))
                input_id = attrs.get("id")
                if input_id and input_id in labels:
                    has_name = True
                # Button text is the accessible name in the common case. An
                # input nested in a label is also named even without a `for`.
                if tag == "button" or (tag == "input" and "<label" in text.lower()):
                    has_name = True
                if tag in {"select", "textarea"} and "<label" in text.lower():
                    has_name = True
                if has_name:
                    labelled_inputs += 1
                else:
                    findings.append(_finding("control-names", "fail", "interactive control has no statically discoverable accessible name", path=relative, tag=tag, id=input_id))
            elif tag == "img":
                image_count += 1
                if "alt" not in attrs:
                    findings.append(_finding("alternative-text", "fail", "image is missing an alt attribute", path=relative))
            elif tag == "iframe":
                iframe_count += 1
                if not any(key in attrs for key in ("title", "aria-label", "aria-labelledby")):
                    findings.append(_finding("alternative-text", "fail", "iframe is missing a title or accessible name", path=relative))

        if has_interactive and not ARIA_NAME_RE.search(text) and "<label" not in text.lower() and "<legend" not in text.lower():
            findings.append(_finding("control-names", "fail", "interactive component has no label/ARIA naming hook", path=relative))
        if has_interactive and not LIVE_RE.search(text):
            findings.append(_finding("dynamic-status", "review", "interactive component has no statically detectable live/status output; verify its result announcement manually", path=relative))
        if has_interactive and "<noscript" not in text.lower():
            findings.append(_finding("fallback", "review", "interactive component has no no-JavaScript fallback; verify the surrounding lesson remains understandable", path=relative))

    # The checks above are intentionally limited to public markup.  Missing
    # component files are a hard failure because the release gate should not
    # silently audit an empty tree.
    if not paths:
        findings.append(_finding("markup", "fail", "no public component/page markup was found"))
    return findings, {
        "files_checked": files_checked,
        "interactive_files": interactive_files,
        "interactive_tags": interactive_tags,
        "labelled_controls": labelled_inputs,
        "files_with_live_regions": live_region_files,
        "files_with_no_js_fallback": fallback_files,
        "image_count": image_count,
        "iframe_count": iframe_count,
        "component_ids_seen": len(component_ids),
    }


def scan_shell_contract(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Check the course shell's landmark and navigation source hooks."""

    findings: list[dict[str, Any]] = []
    path = root / "site" / "src" / "components" / "CourseShell.astro"
    try:
        text = _read(path)
    except (OSError, UnicodeDecodeError) as exc:
        return [_finding("shell-contract", "fail", f"course shell unavailable: {type(exc).__name__}")], {}
    required = {
        "course-shell": "data-course-shell",
        "header-name": "aria-labelledby=\"course-shell-title\"",
        "navigation-name": "aria-label=\"课程首页章节导航\"",
        "main-anchor": 'id="course-shell-main"',
        "skip-search-copy": "Search",
        "mobile-copy": "移动阅读路径",
    }
    missing = [name for name, marker in required.items() if marker not in text]
    for name in missing:
        findings.append(_finding("shell-contract", "fail", f"course shell is missing {name} hook", marker=required[name]))
    return findings, {"path": path.relative_to(root).as_posix(), "markers": {name: marker in text for name, marker in required.items()}}


def audit_repository(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    checks: dict[str, Any] = {}
    scanners = (scan_styles, scan_markup, scan_shell_contract)
    for scanner in scanners:
        result, metadata = scanner(root)
        findings.extend(result)
        checks[scanner.__name__] = metadata
    failed = [item for item in findings if item["severity"] == "fail"]
    review = [item for item in findings if item["severity"] == "review"]
    return {
        "audit_version": AUDIT_VERSION,
        "root": ".",
        "mode": "offline-static",
        "result": "failed" if failed else "passed",
        "summary": {"failed": len(failed), "review": len(review), "finding_count": len(findings)},
        "checks": checks,
        "findings": findings,
        "boundaries": [
            "static source checks do not certify WCAG 2.2 AA conformance",
            "Playwright desktop/mobile checks cover the public routes but not every assistive technology",
            "manual screen-reader, keyboard-only, zoom/reflow, contrast sampling and cognitive review remain in T34",
            "no network, credentials, provider/API, Codex, Claude Code or external accessibility service was used",
        ],
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# T32 移动端与无障碍发布审计",
        "",
        f"- 结果：**{report['result']}**",
        "- 模式：`offline-static`；无网络、浏览器扩展、凭据或外部辅助技术服务",
        f"- 失败：`{summary['failed']}`；人工复核项：`{summary['review']}`；发现总数：`{summary['finding_count']}`",
        "",
        "> 本文件是可重复的源代码门槛。它与 CI 中已有的 Playwright 桌面/移动端路线验证配合，但不把自动化结果写成完整 WCAG 认证。",
        "",
        "## 自动化检查",
        "",
        "| 检查 | 结果元数据 |",
        "| --- | --- |",
    ]
    for name, metadata in report["checks"].items():
        lines.append(f"| `{name}` | `{json.dumps(metadata, ensure_ascii=False, sort_keys=True)}` |")
    lines.extend(["", "## 发现", ""])
    if not report["findings"]:
        lines.append("无静态发现。")
    else:
        for item in report["findings"]:
            safe = {key: value for key, value in item.items() if key not in {"value", "secret", "snippet"}}
            lines.append(f"- `{item['severity']}` `{item['check']}`：{item['message']} — `{json.dumps(safe, ensure_ascii=False, sort_keys=True)}`")
    lines.extend(["", "## T34 人工复核清单", "", "- [ ] Windows 11 + PowerShell 7：键盘完整路径、焦点可见性、缩放/重排与高对比度。", "- [ ] macOS 或 Linux：同一页面路径与真实 Codex/Claude Code 现场实验。", "- [ ] NVDA/VoiceOver 等至少一种读屏：标题层级、地标、表单标签、动态状态、下载反馈。", "- [ ] 记录浏览器、视口、系统、日期、版本、费用与阻塞；异常不得以截图代替。", "", "## 边界", "", *[f"- {boundary}" for boundary in report["boundaries"]]])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="accessibility_audit")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args(argv)
    report = audit_repository(args.root)
    markdown = render_markdown(report)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown, encoding="utf-8")
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(markdown, end="")
    return 1 if report["result"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
