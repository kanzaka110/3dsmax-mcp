"""Harness validation tests for 3dsmax-mcp."""

import ast
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent

SECRET_PATTERNS = [
    re.compile(r'sk-ant-[a-zA-Z0-9_-]{20,}'),
    re.compile(r'sk-proj-[a-zA-Z0-9_-]{20,}'),
    re.compile(r'API_KEY\s*=\s*["\'][a-zA-Z0-9_-]{10,}["\']'),
    re.compile(r'password\s*=\s*["\'][^"\']{8,}["\']', re.IGNORECASE),
]


class TestProjectStructure:
    """Core project structure validation."""

    def test_claude_md_exists(self):
        assert (PROJECT_ROOT / "CLAUDE.md").exists() or (PROJECT_ROOT / ".claude" / "CLAUDE.md").exists()

    def test_readme_exists(self):
        assert (PROJECT_ROOT / "README.md").exists()

    def test_src_directory_exists(self):
        assert (PROJECT_ROOT / "src").exists()

    def test_server_entry_point(self):
        assert (PROJECT_ROOT / "src" / "server.py").exists()

    def test_required_src_modules(self):
        src = PROJECT_ROOT / "src"
        for module in ["max_client.py", "safety.py", "lifecycle.py", "coerce.py"]:
            assert (src / module).exists(), f"src/{module} missing"

    def test_tools_directory(self):
        tools = PROJECT_ROOT / "src" / "tools"
        assert tools.exists()
        py_files = list(tools.glob("*.py"))
        assert len(py_files) >= 3, f"Only {len(py_files)} tool files (need >= 3)"

    def test_helpers_directory(self):
        assert (PROJECT_ROOT / "src" / "helpers").exists()

    def test_maxscript_directory(self):
        assert (PROJECT_ROOT / "maxscript").exists()

    def test_native_directory(self):
        assert (PROJECT_ROOT / "native").exists()

    def test_pyproject_toml_exists(self):
        assert (PROJECT_ROOT / "pyproject.toml").exists()

    def test_install_script_exists(self):
        assert (PROJECT_ROOT / "install.py").exists()


class TestNoHardcodedSecrets:
    """No hardcoded secrets in Python files."""

    def test_no_secrets_in_source(self):
        violations = []
        skip_dirs = {"__pycache__", ".venv", "venv", "node_modules", ".git"}
        for py_file in PROJECT_ROOT.rglob("*.py"):
            if any(d in py_file.parts for d in skip_dirs):
                continue
            if "test_" in py_file.name:
                continue
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for pattern in SECRET_PATTERNS:
                if pattern.findall(content):
                    violations.append(str(py_file.relative_to(PROJECT_ROOT)))
        assert not violations, f"Secrets found: {violations}"


class TestPythonSyntax:
    """All Python files have valid syntax."""

    def test_all_py_files_valid(self):
        errors = []
        for py_file in PROJECT_ROOT.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                ast.parse(source)
            except SyntaxError as e:
                errors.append(f"{py_file.relative_to(PROJECT_ROOT)}: {e}")
        assert not errors, f"Syntax errors: {errors}"


class TestSkillsAndAgents:
    """Skills and agents files validation."""

    def test_skill_file_exists(self):
        skill_files = list(PROJECT_ROOT.glob("*.skill"))
        assert len(skill_files) >= 1, "No .skill files found"

    def test_agents_md_exists(self):
        assert (PROJECT_ROOT / "AGENTS.md").exists()

    def test_skills_directory(self):
        skills = PROJECT_ROOT / "skills"
        if skills.exists():
            md_files = list(skills.rglob("*.md"))
            assert len(md_files) >= 1, "skills/ has no markdown files"


class TestMcpConfig:
    """MCP configuration validation."""

    def test_mcp_config_exists(self):
        assert (PROJECT_ROOT / "mcp_config.ini").exists()

    def test_mcp_config_parseable(self):
        import configparser
        config = configparser.ConfigParser()
        config.read(PROJECT_ROOT / "mcp_config.ini")
        assert len(config.sections()) >= 0  # At least parseable
