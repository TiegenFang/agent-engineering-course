"""Repeatable, offline-first release audit for the Agent 工程入门 course.

The audit checks repository evidence that can be evaluated without contacting
the network: secret-shaped values, contract/source coverage, license metadata,
dependency pinning/lock consistency, and permission declarations.  It also
records all public links and freshness dates.  Link liveness and registry
updates are *not* inferred offline; pass ``--online`` when a maintainer has
approved a bounded network audit.

This is a release gate helper, not a penetration test, legal license opinion,
credential scanner with perfect recall, or provider/API acceptance test.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


AUDIT_VERSION = "1"
DEFAULT_MAX_URL_CHECKS = 100
TEXT_SUFFIXES = {
    ".astro",
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mdx",
    ".mjs",
    ".ps1",
    ".py",
    ".sh",
    ".ts",
    ".tsx",
    ".toml",
    ".txt",
    ".yml",
    ".yaml",
}
SKIP_PARTS = {
    ".audit",
    ".git",
    ".worktrees",
    ".astro",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "node_modules",
}

PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----")
TOKEN_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{20,})\b"
)
ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:[A-Za-z0-9]+_)?(?:api[_-]?key|access[_-]?token|secret(?:[_-]?key)?|password)\b\s*[:=]\s*[\"']?([A-Za-z0-9_./+=-]{12,})"
)
URL_RE = re.compile(r"https?://[^\s<>'\")\]]+")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
DATE_RE = re.compile(r"(?<!\d)(20\d{2}-\d{2}-\d{2})(?!\d)")
PINNED_VERSION_RE = re.compile(r"^[^\s]+$")


def _finding(check: str, severity: str, message: str, **extra: Any) -> dict[str, Any]:
    value = {"check": check, "severity": severity, "message": message}
    value.update(extra)
    return value


def _read_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, "missing"
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, str(exc)


def _iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in SKIP_PARTS for part in relative_parts):
            continue
        yield path


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().strip("\"'").lower()
    return (
        not normalized
        or normalized.startswith(("<", "${", "your", "replace", "example", "sample", "fake", "test-"))
        or normalized.startswith(("sk-test-", "ghp-test-", "assert-", "get-", "join-", "resolve-", "new-"))
        or normalized in {"changeme", "dummy", "placeholder", "not-a-real-secret", "none", "null"}
        or normalized.startswith(("not-", "no-"))
    )


def scan_sensitive(root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in _iter_text_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, 1):
            if PRIVATE_KEY_RE.search(line):
                findings.append(_finding("sensitive-data", "fail", "private-key marker found", path=str(path.relative_to(root)), line=line_number, rule="private-key-marker"))
            if TOKEN_RE.search(line):
                findings.append(_finding("sensitive-data", "fail", "provider-token-shaped value found", path=str(path.relative_to(root)), line=line_number, rule="provider-token-shape"))
            match = ASSIGNMENT_RE.search(line)
            if match and not _is_placeholder(match.group(1)):
                findings.append(_finding("sensitive-data", "fail", "credential-shaped assignment found", path=str(path.relative_to(root)), line=line_number, rule="credential-assignment"))
    return findings


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def scan_contracts(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not any((root / name).is_file() for name in ("LICENSE", "LICENSE.md", "LICENSE.txt")):
        findings.append(_finding("license-coverage", "fail", "repository has no root LICENSE file"))
    contract_path = root / "docs" / "contracts" / "content-contract.json"
    source_path = root / "docs" / "sources" / "source-ledger.json"
    contract, contract_error = _read_json(contract_path)
    ledger, ledger_error = _read_json(source_path)
    if contract_error:
        findings.append(_finding("contract-coverage", "fail", f"content contract unavailable: {contract_error}"))
        contract = {}
    if ledger_error:
        findings.append(_finding("source-coverage", "fail", f"source ledger unavailable: {ledger_error}"))
        ledger = {}
    lessons = contract.get("lessons") if isinstance(contract, Mapping) else None
    sources = ledger.get("sources") if isinstance(ledger, Mapping) else None
    if sources is None and isinstance(ledger, Mapping):
        sources = ledger.get("entries")
    if not isinstance(lessons, list):
        findings.append(_finding("contract-coverage", "fail", "content contract lessons must be a list"))
        lessons = []
    if not isinstance(sources, list):
        findings.append(_finding("source-coverage", "fail", "source ledger sources must be a list"))
        sources = []

    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, Mapping):
            findings.append(_finding("source-coverage", "fail", "source entry must be an object", index=index))
            continue
        source_id = source.get("id")
        if not _non_empty(source_id):
            findings.append(_finding("source-coverage", "fail", "source entry has no id", index=index))
            continue
        if source_id in source_ids:
            findings.append(_finding("source-coverage", "fail", "duplicate source id", source_id=source_id))
        source_ids.add(source_id)
        required = ("title", "url", "source_role", "pinned_version", "usage", "license_or_terms", "copied_assets")
        missing = [field for field in required if field not in source or not _non_empty(source[field]) and field != "copied_assets"]
        if missing:
            findings.append(_finding("source-coverage", "fail", "source metadata incomplete", source_id=source_id, missing=missing))
        if not isinstance(source.get("copied_assets"), bool):
            findings.append(_finding("source-coverage", "fail", "copied_assets must be boolean", source_id=source_id))
        url = source.get("url")
        if _non_empty(url) and not _valid_url(url):
            findings.append(_finding("link-syntax", "fail", "source URL is not valid HTTP(S) or repository path", source_id=source_id))
        if source.get("copied_assets") is True and not _non_empty(source.get("license_or_terms")):
            findings.append(_finding("license-coverage", "fail", "copied asset has no license/terms record", source_id=source_id))

    lesson_ids: set[str] = set()
    referenced_sources: set[str] = set()
    for index, lesson in enumerate(lessons):
        if not isinstance(lesson, Mapping):
            findings.append(_finding("contract-coverage", "fail", "lesson entry must be an object", index=index))
            continue
        lesson_id = lesson.get("id")
        if not _non_empty(lesson_id):
            findings.append(_finding("contract-coverage", "fail", "lesson has no id", index=index))
            continue
        if lesson_id in lesson_ids:
            findings.append(_finding("contract-coverage", "fail", "duplicate lesson id", lesson_id=lesson_id))
        lesson_ids.add(lesson_id)
        source_refs = lesson.get("sources")
        if not isinstance(source_refs, list) or not source_refs:
            findings.append(_finding("source-coverage", "fail", "lesson has no source references", lesson_id=lesson_id))
        else:
            for source_id in source_refs:
                if not _non_empty(source_id):
                    findings.append(_finding("source-coverage", "fail", "lesson source reference must be a non-empty string", lesson_id=lesson_id))
                    continue
                referenced_sources.add(source_id)
                if source_id not in source_ids:
                    findings.append(_finding("source-coverage", "fail", "lesson references unknown source", lesson_id=lesson_id, source_id=source_id))
        licenses = lesson.get("licenses")
        if not isinstance(licenses, list) or not licenses or any(not _non_empty(item) for item in licenses):
            findings.append(_finding("license-coverage", "fail", "lesson license list is incomplete", lesson_id=lesson_id))
        risk = lesson.get("risk")
        if not isinstance(risk, Mapping) or any(not _non_empty(risk.get(field)) for field in ("permissions", "side_effects", "staleness")):
            findings.append(_finding("permission-coverage", "fail", "lesson risk card must include permissions, side_effects and staleness", lesson_id=lesson_id))

    orphan_sources = sorted(source_ids - referenced_sources)
    if orphan_sources:
        findings.append(_finding("source-coverage", "review", "source entries are not referenced by a lesson; review intentional shared sources", count=len(orphan_sources), source_ids=orphan_sources[:20]))
    return findings, {"lesson_count": len(lesson_ids), "source_count": len(source_ids), "referenced_source_count": len(referenced_sources), "orphan_source_count": len(orphan_sources)}


def _valid_url(value: Any) -> bool:
    if not isinstance(value, str) or any(char.isspace() for char in value):
        return False
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return bool(parsed.netloc)
    if parsed.scheme == "" and (value.startswith("docs/") or value.startswith("./") or value.startswith("../")):
        return True
    return False


def scan_links(root: Path, *, online: bool, max_url_checks: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    urls: set[str] = set()
    internal_link_count = 0
    for path in _iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        urls.update(URL_RE.findall(text))
        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0]
            if not target or target.startswith(("#", "/", "http://", "https://", "mailto:", "tel:", "javascript:", "data:")):
                continue
            target = target.split("#", 1)[0].split("?", 1)[0]
            if not target:
                continue
            if target.startswith(("docs/", "site/", "labs/", "checker/")):
                candidate = root / target
            elif target.startswith(("./", "../")):
                candidate = path.parent / target
            else:
                continue
            internal_link_count += 1
            try:
                candidate.relative_to(root)
            except ValueError:
                findings.append(_finding("link-syntax", "fail", "relative link escapes repository root", path=str(path.relative_to(root))))
                continue
            if not candidate.exists() and target.startswith("../"):
                repository_target = target
                while repository_target.startswith("../"):
                    repository_target = repository_target[3:]
                if repository_target.startswith(("docs/", "site/", "labs/", "checker/", "scripts/")):
                    candidate = root / repository_target
            if not candidate.exists():
                findings.append(_finding("link-liveness", "fail", "relative repository link target is missing", path=str(path.relative_to(root)), target=target))
    for url in sorted(urls):
        if not _valid_url(url):
            findings.append(_finding("link-syntax", "fail", "URL has invalid syntax", url=url))
    online_results: list[dict[str, Any]] = []
    if online:
        checked = 0
        for url in sorted(urls):
            if checked >= max_url_checks:
                break
            if "${" in url or "`" in url:
                # Template-literal placeholders captured from source code are not real URLs.
                continue
            parsed_online = urlparse(url)
            if parsed_online.hostname in {"127.0.0.1", "localhost", "0.0.0.0", "::1", None}:
                # Local dev-server constants in test scripts are fixtures, not external links.
                continue
            if (parsed_online.hostname or "").endswith(".example.com") or parsed_online.hostname in {"example.com", "example.org", "example.net"}:
                # RFC 2606 reserved documentation domains appear in tests and examples by design.
                continue
            checked += 1
            try:
                request = Request(url, method="HEAD", headers={"User-Agent": "agent-engineering-course-release-audit/1"})
                with urlopen(request, timeout=8) as response:  # nosec B310: opt-in bounded audit URL
                    status = int(response.status)
                online_results.append({"url": url, "status": status})
                if status in (404, 410):
                    findings.append(_finding("link-liveness", "fail", f"remote URL returned HTTP {status} (dead link)", url=url, status=status))
                elif status >= 400:
                    # 401/403/405 etc. prove the host is alive; API endpoints reject unauthenticated HEADs by design.
                    findings.append(_finding("link-liveness", "review", f"remote URL reachable but returned HTTP {status}; verify manually if it is a documentation link", url=url, status=status))
            except HTTPError as exc:
                online_results.append({"url": url, "status": exc.code})
                if exc.code in (404, 410):
                    findings.append(_finding("link-liveness", "fail", f"remote URL returned HTTP {exc.code} (dead link)", url=url, status=exc.code))
                elif exc.code >= 400:
                    findings.append(_finding("link-liveness", "review", f"remote URL reachable but returned HTTP {exc.code}; verify manually if it is a documentation link", url=url, status=exc.code))
            except ValueError as exc:
                online_results.append({"url": url, "error": type(exc).__name__})
                findings.append(_finding("link-syntax", "review", "URL could not be checked (invalid target, likely a source-code placeholder)", url=url, error=type(exc).__name__))
            except (URLError, TimeoutError, OSError) as exc:
                online_results.append({"url": url, "error": type(exc).__name__})
                findings.append(_finding("link-liveness", "review", "remote URL could not be checked from this network; regional blocking or transient failure is possible", url=url, error=type(exc).__name__))
    else:
        findings.append(_finding("link-liveness", "review", "offline mode records links but does not claim they are live", count=len(urls), network_checked=False))
    return findings, {"url_count": len(urls), "internal_link_count": internal_link_count, "network_checked": online, "checked_url_count": len(online_results), "online_results": online_results}


def _is_exact_pin(spec: Any) -> bool:
    if not isinstance(spec, str) or not spec or spec.startswith(("^", "~", ">", "<", "git", "http")):
        return False
    return spec not in {"*", "latest"} and bool(PINNED_VERSION_RE.fullmatch(spec))


def scan_dependencies(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    lock, lock_error = _read_json(root / "package-lock.json")
    if lock_error or not isinstance(lock, Mapping):
        findings.append(_finding("dependency-lock", "fail", f"package-lock.json unavailable: {lock_error or 'invalid'}"))
        return findings, {"package_files": [], "lock_sha256": None}
    lock_packages = lock.get("packages") if isinstance(lock.get("packages"), Mapping) else {}
    lock_root = lock_packages.get("") if isinstance(lock_packages, Mapping) else {}
    package_files = [root / "package.json", root / "site" / "package.json"]
    checked_packages: list[str] = []
    for package_path in package_files:
        package, error = _read_json(package_path)
        relative = str(package_path.relative_to(root))
        if error or not isinstance(package, Mapping):
            findings.append(_finding("dependency-lock", "fail", f"package manifest unavailable: {error or 'invalid'}", path=relative))
            continue
        checked_packages.append(relative)
        for section in ("dependencies", "devDependencies", "optionalDependencies"):
            values = package.get(section, {})
            if not isinstance(values, Mapping):
                findings.append(_finding("dependency-pin", "fail", "dependency section must be an object", path=relative, section=section))
                continue
            for name, spec in values.items():
                if not _is_exact_pin(spec):
                    findings.append(_finding("dependency-pin", "fail", "dependency is not exact-pinned", package=name, spec=spec, path=relative))
                lock_key = f"node_modules/{name}"
                lock_entry = lock_packages.get(lock_key) if isinstance(lock_packages, Mapping) else None
                if not isinstance(lock_entry, Mapping) or not _non_empty(lock_entry.get("version")):
                    findings.append(_finding("dependency-lock", "fail", "dependency is missing from lockfile", package=name, path=relative))
                elif isinstance(spec, str) and spec != lock_entry.get("version"):
                    findings.append(_finding("dependency-lock", "fail", "manifest pin differs from lockfile version", package=name, manifest=spec, lock=lock_entry.get("version"), path=relative))
        if package_path == root / "package.json" and isinstance(lock_root, Mapping):
            for section in ("dependencies", "devDependencies", "optionalDependencies"):
                if package.get(section, {}) != lock_root.get(section, {}):
                    findings.append(_finding("dependency-lock", "fail", "root manifest dependency section differs from lock root", section=section))
    lock_bytes = (root / "package-lock.json").read_bytes()
    return findings, {"package_files": checked_packages, "lock_sha256": hashlib.sha256(lock_bytes).hexdigest(), "lockfile_version": lock.get("lockfileVersion")}


def scan_permissions(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    workflow_count = 0
    workflow_permissions = 0
    workflow_root = root / ".github" / "workflows"
    if workflow_root.is_dir():
        for path in sorted(workflow_root.glob("*.y*ml")):
            workflow_count += 1
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if re.search(r"(?m)^permissions:\s*$", text):
                workflow_permissions += 1
            if re.search(r"(?i)\b(?:write-all|contents\s*:\s*write|actions\s*:\s*write)\b", text):
                findings.append(_finding("permission-coverage", "fail", "workflow requests broad or write permission; review least privilege", path=str(path.relative_to(root))))
            if not re.search(r"(?m)^permissions:\s*$", text):
                findings.append(_finding("permission-coverage", "review", "workflow has no explicit top-level permissions block", path=str(path.relative_to(root))))
    return findings, {"workflow_count": workflow_count, "workflow_with_explicit_permissions": workflow_permissions}


def scan_freshness(root: Path, *, as_of: dt.date, max_age_days: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    contract, error = _read_json(root / "docs" / "contracts" / "content-contract.json")
    if error or not isinstance(contract, Mapping):
        findings.append(_finding("freshness", "fail", f"cannot inspect lesson dates: {error or 'invalid contract'}"))
        return findings, {"as_of": as_of.isoformat(), "max_age_days": max_age_days, "stale_lesson_count": None, "undated_source_count": None}
    stale_lessons = 0
    for lesson in contract.get("lessons", []):
        if not isinstance(lesson, Mapping):
            continue
        raw_date = lesson.get("verified_on")
        try:
            verified = dt.date.fromisoformat(raw_date)
        except (TypeError, ValueError):
            findings.append(_finding("freshness", "fail", "lesson verified_on is not an ISO date", lesson_id=lesson.get("id")))
            continue
        age = (as_of - verified).days
        if age < 0 or age > max_age_days:
            stale_lessons += 1
            findings.append(_finding("freshness", "fail", "lesson verification is outside the freshness window", lesson_id=lesson.get("id"), verified_on=raw_date, age_days=age))
    ledger, error = _read_json(root / "docs" / "sources" / "source-ledger.json")
    undated_sources = 0
    stale_sources = 0
    if error or not isinstance(ledger, Mapping):
        findings.append(_finding("freshness", "fail", f"cannot inspect source dates: {error or 'invalid ledger'}"))
    else:
        source_entries = ledger.get("sources") or ledger.get("entries") or []
        for source in source_entries:
            if not isinstance(source, Mapping):
                continue
            dates = [dt.date.fromisoformat(value) for value in DATE_RE.findall(str(source.get("pinned_version", ""))) if _safe_date(value)]
            if not dates:
                undated_sources += 1
                continue
            latest = max(dates)
            age = (as_of - latest).days
            if age < 0 or age > max_age_days:
                stale_sources += 1
                findings.append(_finding("freshness", "fail", "source verification date is outside the freshness window", source_id=source.get("id"), verified_on=latest.isoformat(), age_days=age))
    if undated_sources:
        findings.append(_finding("freshness", "review", "some source pinned_version values contain no parseable YYYY-MM-DD; manually review them", count=undated_sources))
    return findings, {"as_of": as_of.isoformat(), "max_age_days": max_age_days, "stale_lesson_count": stale_lessons, "stale_source_count": stale_sources, "undated_source_count": undated_sources}


def _safe_date(value: str) -> bool:
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def audit_repository(root: Path, *, as_of: dt.date, max_age_days: int = 90, online: bool = False, max_url_checks: int = DEFAULT_MAX_URL_CHECKS) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    details: dict[str, Any] = {}
    for scanner in (scan_sensitive, scan_contracts, scan_links, scan_dependencies, scan_permissions, scan_freshness):
        if scanner is scan_sensitive:
            result = scanner(root)
            metadata = {"finding_count": len(result)}
        elif scanner is scan_links:
            result, metadata = scanner(root, online=online, max_url_checks=max_url_checks)
        elif scanner is scan_freshness:
            result, metadata = scanner(root, as_of=as_of, max_age_days=max_age_days)
        else:
            result, metadata = scanner(root)
        findings.extend(result)
        details[scanner.__name__] = metadata
    failed = [item for item in findings if item["severity"] == "fail"]
    review = [item for item in findings if item["severity"] == "review"]
    return {
        "audit_version": AUDIT_VERSION,
        "root": ".",
        "mode": "online" if online else "offline",
        "as_of": as_of.isoformat(),
        "freshness_window_days": max_age_days,
        "result": "failed" if failed else "passed",
        "summary": {"failed": len(failed), "review": len(review), "finding_count": len(findings)},
        "checks": details,
        "findings": findings,
        "boundaries": [
            "offline mode does not claim remote URL liveness",
            "offline mode does not compare registry latest versions",
            "static patterns do not replace human security review or legal license review",
            "provider/API/Codex/Claude Code live behavior is not tested",
        ],
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# T33 发布安全、来源、许可证与时效审计",
        "",
        f"- 结果：**{report['result']}**",
        f"- 模式：`{report['mode']}`（网络链接现场检查：`{report['checks']['scan_links']['network_checked']}`）",
        f"- as-of：`{report['as_of']}`；时效窗口：`{report['freshness_window_days']} 天`",
        f"- 失败：`{summary['failed']}`；人工复核项：`{summary['review']}`；发现总数：`{summary['finding_count']}`",
        "",
        "> 这是可重复的静态发布审计，不是完整渗透测试、法律许可证意见、凭据扫描的完备证明，也不等同于真实 API、MCP、Codex 或 Claude Code 验收。",
        "",
        "## 检查摘要",
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
            safe = {key: value for key, value in item.items() if key not in {"snippet", "value", "secret"}}
            lines.append(f"- `{item['severity']}` `{item['check']}`：{item['message']} — `{json.dumps(safe, ensure_ascii=False, sort_keys=True)}`")
    lines.extend(["", "## 边界与下一步", "", *[f"- {boundary}" for boundary in report["boundaries"]]])
    if report["mode"] == "offline":
        lines.append("- 如需死链结论，维护者应在已批准网络环境运行同一脚本的 `--online` 模式，并人工复核异常链接。")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="release_audit")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--as-of", default=dt.date.today().isoformat(), help="ISO date used by the 90-day freshness gate")
    parser.add_argument("--max-age-days", type=int, default=90)
    parser.add_argument("--online", action="store_true", help="opt into bounded remote URL checks; registry updates still require manual review")
    parser.add_argument("--max-url-checks", type=int, default=DEFAULT_MAX_URL_CHECKS)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args(argv)
    try:
        as_of = dt.date.fromisoformat(args.as_of)
    except ValueError as exc:
        parser.error(f"--as-of must be YYYY-MM-DD: {exc}")
    report = audit_repository(args.root, as_of=as_of, max_age_days=args.max_age_days, online=args.online, max_url_checks=args.max_url_checks)
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
