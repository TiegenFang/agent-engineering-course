"""Offline T25 dual-track capstone integration lab.

The runner emits only synthetic portfolio artifacts and an anonymous evidence
document.  It never starts a Coding Agent, calls an API, reads credentials, or
touches a learner repository.  Use a new output directory for every run.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COURSE_VERSION = json.loads(
    (ROOT / "course-version.json").read_text(encoding="utf-8")
)["course_version"]
LESSON_ID = "t25-capstone-integration"
VERSION = "1"
BASELINE_ID = "telemetry-capstone-integration-v1"
CHECK_IDS = [
    "track-selected",
    "problem-scoped",
    "context-memory-linked",
    "skill-mcp-bounded",
    "core-evidence-linked",
    "validation-recorded",
    "migration-recorded",
    "delivery-reviewed",
    "privacy-safe",
    "version-locked",
    "portfolio-exported",
    "offline-deterministic",
]
TRACKS = {
    "research": {
        "label": "科研结课轨道",
        "delivery": "数据检查、分析、图表、实验记录和报告",
    },
    "enterprise": {
        "label": "企业结课轨道",
        "delivery": "Issue 澄清、计划、实现、测试、评审和交付说明",
    },
}
FAULTS = {"none", "missing-core", "unsafe-side-effect", "incomplete-delivery"}


def expected_flags(track: str, fault: str) -> dict[str, bool]:
    if track not in TRACKS:
        raise ValueError(f"unsupported track: {track}")
    if fault not in FAULTS:
        raise ValueError(f"unsupported fault: {fault}")
    return {
        "track": True,
        "problem": True,
        "context_memory": fault != "missing-core",
        "skill_mcp": fault != "unsafe-side-effect",
        "core": fault != "missing-core",
        "validation": fault != "incomplete-delivery",
        "migration": True,
        "delivery": fault != "incomplete-delivery",
        "privacy": fault != "unsafe-side-effect",
        "version": True,
        "portfolio": fault != "incomplete-delivery",
        "offline": True,
    }


def checks_for(flags: dict[str, bool]) -> list[dict[str, str]]:
    fields = [
        ("track-selected", "track"),
        ("problem-scoped", "problem"),
        ("context-memory-linked", "context_memory"),
        ("skill-mcp-bounded", "skill_mcp"),
        ("core-evidence-linked", "core"),
        ("validation-recorded", "validation"),
        ("migration-recorded", "migration"),
        ("delivery-reviewed", "delivery"),
        ("privacy-safe", "privacy"),
        ("version-locked", "version"),
        ("portfolio-exported", "portfolio"),
        ("offline-deterministic", "offline"),
    ]
    return [
        {"id": check_id, "result": "passed" if flags[field] else "failed"}
        for check_id, field in fields
    ]


def build_run(track: str, fault: str = "none") -> dict[str, object]:
    flags = expected_flags(track, fault)
    checks = checks_for(flags)
    return {
        "version": VERSION,
        "baseline_id": BASELINE_ID,
        "track": track,
        "fault": fault,
        **flags,
        "checks": checks,
    }


def write_outputs(output: Path, run: dict[str, object]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    checks = run["checks"]
    assert isinstance(checks, list)
    result = "passed" if all(check["result"] == "passed" for check in checks) else "partial"
    track = str(run["track"])
    track_label = TRACKS[track]["label"]
    delivery = TRACKS[track]["delivery"]

    (output / "integration-checklist.json").write_text(
        json.dumps(
            {
                "version": VERSION,
                "track": track,
                "track_label": track_label,
                "shared_dimensions": [
                    "问题定义",
                    "上下文质量",
                    "操作安全",
                    "验证证据",
                    "可复现性",
                    "迁移能力",
                    "交付清晰度",
                ],
                "delivery": delivery,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (output / "integration-record.json").write_text(
        json.dumps(
            {
                "version": VERSION,
                "track": track,
                "fault": run["fault"],
                "context_memory": run["context_memory"],
                "skill_mcp": run["skill_mcp"],
                "core": run["core"],
                "validation": run["validation"],
                "migration": run["migration"],
                "privacy": run["privacy"],
                "recovery": "safe-default-rerun" if run["fault"] != "none" else "not-needed",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (output / "portfolio.md").write_text(
        "# 设备遥测与报告工具：结课集成组合\n\n"
        f"- track: `{track}` ({track_label})\n"
        f"- delivery: {delivery}\n"
        f"- result: `{result}`\n"
        f"- fault: `{run['fault']}`\n"
        "- data: synthetic telemetry only\n"
        "- network/API/Coding Agent: none\n\n"
        "本组合把公共能力证据与所选双场景轨道的交付证据放在同一验收量表下。"
        "路径、源码、凭据和原始数据留在本地，不进入匿名 evidence。\n",
        encoding="utf-8",
    )
    (output / "migration-notes.md").write_text(
        "# 迁移记录\n\n"
        f"选择 `{track}` 轨道后，保持问题定义、上下文、验证、安全和版本维度不变；"
        "只改变交付视角。Codex/Claude Code 的现场调用未由此离线实验执行。\n",
        encoding="utf-8",
    )
    evidence = {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": LESSON_ID,
        "result": result,
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": "所有必需证据均已通过。" if result == "passed" else "部分证据已通过，仍有证据需要补齐。",
        "evidence": checks,
        "experiment": {
            "version": VERSION,
            "baseline_id": BASELINE_ID,
            "track": track,
            "fault": run["fault"],
            "problem": run["problem"],
            "context_memory": run["context_memory"],
            "skill_mcp": run["skill_mcp"],
            "core": run["core"],
            "validation": run["validation"],
            "migration": run["migration"],
            "delivery": run["delivery"],
            "privacy": run["privacy"],
            "version_lock": run["version"],
            "portfolio": run["portfolio"],
            "offline": run["offline"],
        },
    }
    (output / f"{LESSON_ID}-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the offline T25 capstone integration fixture")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--track", choices=sorted(TRACKS), default="enterprise")
    parser.add_argument("--fault", choices=sorted(FAULTS), default="none")
    args = parser.parse_args()
    write_outputs(args.output.resolve(), build_run(args.track, args.fault))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
