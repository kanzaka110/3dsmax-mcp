#!/usr/bin/env python3
"""Build the portable .skill file, sync to local + global skills, and generate AGENTS.md."""

import argparse
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "3dsmax-mcp-dev"
SKILL_SRC = SKILL_DIR / "SKILL.md"
SKILL_OUT = ROOT / "3dsmax-mcp-dev.skill"
LOCAL_SKILLS_DIR = ROOT / ".claude" / "skills" / "3dsmax-mcp-dev"
LOCAL_AGENTS_DIR = ROOT / ".agents" / "skills" / "3dsmax-mcp-dev"
GLOBAL_SKILLS_DIR = Path.home() / ".claude" / "skills" / "3dsmax-mcp-dev"
GLOBAL_AGENTS_DIR = Path.home() / ".agents" / "skills" / "3dsmax-mcp-dev"
CLAUDE_MD = ROOT / ".claude" / "CLAUDE.md"
AGENTS_MD = ROOT / "AGENTS.md"


def generate_agents_md():
    """Generate AGENTS.md from CLAUDE.md + inlined skill files.

    Codex/Gemini read AGENTS.md from the repo root. They don't have
    the skill system, so we inline SKILL.md and all maxscript-*.md
    reference files directly into AGENTS.md.
    """
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

    # Inline SKILL.md only (pitfalls, tool reference, architecture).
    # MAXScript reference files (maxscript-*.md) are too large to inline —
    # agents can read them on demand from skills/3dsmax-mcp-dev/
    parts = [text, "", "---", ""]

    if SKILL_SRC.exists():
        # Strip frontmatter from SKILL.md
        skill_text = SKILL_SRC.read_text("utf-8")
        if skill_text.startswith("---"):
            end = skill_text.find("---", 3)
            if end != -1:
                skill_text = skill_text[end + 3:].lstrip("\n")
        parts.append(skill_text)

    AGENTS_MD.write_text("\n".join(parts), "utf-8")
    print(f"  Generated {AGENTS_MD.name} (with inlined SKILL.md)")


def collect_skill_files():
    """Collect SKILL.md + all maxscript-*.md reference files."""
    files = [SKILL_SRC]
    for md in sorted(SKILL_DIR.glob("maxscript-*.md")):
        files.append(md)
    return files


def build(target="both"):
    if not SKILL_SRC.exists():
        print(f"ERROR: source not found: {SKILL_SRC}")
        raise SystemExit(1)

    skill_files = collect_skill_files()

    # 1. Build .skill ZIP archive
    with zipfile.ZipFile(SKILL_OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.mkdir("./")
        for f in skill_files:
            zf.write(f, f"./{f.name}")
    print(f"  Built {SKILL_OUT.name} ({len(skill_files)} files)")

    # 2. Select install targets
    local_dests = [
        (".claude/skills", LOCAL_SKILLS_DIR),
        (".agents/skills", LOCAL_AGENTS_DIR),
    ]
    global_dests = [
        ("~/.claude/skills", GLOBAL_SKILLS_DIR),
        ("~/.agents/skills", GLOBAL_AGENTS_DIR),
    ]

    if target == "local":
        dests = local_dests
    elif target == "global":
        dests = global_dests
    else:
        dests = local_dests + global_dests

    for label, dest in dests:
        # Clean stale symlinks/junctions from older installs (pre-0.5)
        if dest.is_symlink() or dest.is_junction():
            print(f"  Replacing old symlink: {dest}")
            dest.unlink()
        dest.mkdir(parents=True, exist_ok=True)
        try:
            for f in skill_files:
                shutil.copy2(f, dest / f.name)
            print(f"  Copied to {label}/")
        except PermissionError:
            print(f"  WARN: {label} locked, skipped")

    # 3. Generate AGENTS.md from CLAUDE.md
    generate_agents_md()

    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build and install 3dsmax-mcp-dev skill")
    parser.add_argument(
        "--target",
        choices=["local", "global", "both"],
        default="both",
        help="Where to install: 'local' (project only), 'global' (~/ only), 'both' (default)",
    )
    args = parser.parse_args()
    build(target=args.target)
