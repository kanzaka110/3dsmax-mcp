#!/usr/bin/env python3
"""Build the portable .skill file, sync to local + global skills, and generate AGENTS.md."""

import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_SRC = ROOT / "skills" / "3dsmax-mcp-dev" / "SKILL.md"
SKILL_OUT = ROOT / "3dsmax-mcp-dev.skill"
LOCAL_SKILLS_DIR = ROOT / ".claude" / "skills" / "3dsmax-mcp-dev"
GLOBAL_SKILLS_DIR = Path.home() / ".claude" / "skills" / "3dsmax-mcp-dev"
CLAUDE_MD = ROOT / ".claude" / "CLAUDE.md"
AGENTS_MD = ROOT / "AGENTS.md"


def generate_agents_md():
    """Generate AGENTS.md from CLAUDE.md by replacing agent-specific references."""
    if not CLAUDE_MD.exists():
        print(f"  WARN: {CLAUDE_MD} not found, skipping AGENTS.md")
        return

    text = CLAUDE_MD.read_text("utf-8")

    # Replace agent-specific terms (case-sensitive, whole-word where possible)
    subs = [
        (r"(?<!\w)Claude(?!\w)", "Codex"),    # "Claude" as standalone word
        (r"\.claude/skills/", ".Codex/skills/"),
    ]
    for pattern, repl in subs:
        text = re.sub(pattern, repl, text)

    # Fix the self-reference line — keep it pointing to CLAUDE.md as source
    text = text.replace(
        "from it via `scripts/build_skill.py`",
        "from `.claude/CLAUDE.md` via `scripts/build_skill.py`",
    )

    AGENTS_MD.write_text(text, "utf-8")
    print(f"  Generated {AGENTS_MD.name}")


def build():
    if not SKILL_SRC.exists():
        print(f"ERROR: source not found: {SKILL_SRC}")
        raise SystemExit(1)

    # 1. Build .skill ZIP archive
    with zipfile.ZipFile(SKILL_OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.mkdir("./")
        zf.write(SKILL_SRC, "./SKILL.md")
    print(f"  Built {SKILL_OUT.name}")

    # 2. Copy to project-local .claude/skills/ (in-project discovery)
    LOCAL_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SKILL_SRC, LOCAL_SKILLS_DIR / "SKILL.md")
    print(f"  Copied to project .claude/skills/")

    # 3. Copy to global ~/.claude/skills/ (cross-project discovery)
    GLOBAL_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(SKILL_SRC, GLOBAL_SKILLS_DIR / "SKILL.md")
        print(f"  Copied to global ~/.claude/skills/")
    except PermissionError:
        # File may be locked by a running Claude Code instance
        print(f"  WARN: global skill locked (Claude Code running?), skipped")

    # 4. Generate AGENTS.md from CLAUDE.md
    generate_agents_md()

    print("Done.")


if __name__ == "__main__":
    build()
