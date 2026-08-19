from __future__ import annotations

import sys
from pathlib import Path

import pytest

from colossal.runtime.native_runner import HAS_NATIVE

if HAS_NATIVE:
    from colossal import colossal_native


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_native_process_supervisor_success() -> None:
    cmd = [
        sys.executable,
        "-c",
        "import sys; sys.stdout.write('native stdout\\n'); sys.stderr.write('native stderr\\n')",
    ]
    res = colossal_native.ProcessSupervisor.execute(cmd)

    assert res.is_success
    assert res.exit_code == 0
    assert "native stdout" in res.stdout_text
    assert "native stderr" in res.stderr_text
    assert not res.cancelled
    assert res.duration_seconds >= 0.0


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_native_process_supervisor_exit_code() -> None:
    cmd = [sys.executable, "-c", "import sys; sys.stderr.write('crash report\\n'); sys.exit(7)"]
    res = colossal_native.ProcessSupervisor.execute(cmd)

    assert not res.is_success
    assert res.exit_code == 7
    assert "crash report" in res.stderr_text


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_native_tool_discovery() -> None:
    discovery = colossal_native.ToolDiscovery.instance()
    discovery.clear_cache()

    # Register python executable as a known tool
    discovery.register_custom_path("python_cli", Path(sys.executable))
    found = discovery.find_tool("python_cli")
    assert found is not None
    assert Path(found) == Path(sys.executable)

    req = discovery.require_tool("python_cli", 0)
    assert Path(req) == Path(sys.executable)

    # Missing tool raises RuntimeError containing missing_dependency
    with pytest.raises(RuntimeError, match="missing_dependency"):
        discovery.require_tool("nonexistent_tool_123456", 0)
