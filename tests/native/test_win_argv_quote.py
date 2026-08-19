from __future__ import annotations

import pytest

from colossal.runtime.native_runner import HAS_NATIVE

if HAS_NATIVE:
    from colossal import colossal_native

pytestmark = pytest.mark.skipif(
    not HAS_NATIVE, reason="colossal_native C++ extension not available"
)


def _roundtrip_via_shlex_like_split(quoted: str) -> list[str]:
    """Parses a Win32-quoted command line the same way CommandLineToArgvW
    does, so we can assert the quoting round-trips to the original argv.
    This mirrors the documented algorithm rather than reusing our own
    quoting code, so it's an independent check.
    """
    args: list[str] = []
    current = []
    started = False
    i = 0
    n = len(quoted)
    in_quotes = False
    while i < n:
        c = quoted[i]
        if c == "\\":
            started = True
            backslashes = 0
            while i < n and quoted[i] == "\\":
                backslashes += 1
                i += 1
            if i < n and quoted[i] == '"':
                current.append("\\" * (backslashes // 2))
                if backslashes % 2 == 0:
                    in_quotes = not in_quotes
                else:
                    current.append('"')
                i += 1
            else:
                current.append("\\" * backslashes)
        elif c == '"':
            started = True
            in_quotes = not in_quotes
            i += 1
        elif c == " " and not in_quotes:
            if started:
                args.append("".join(current))
                current = []
                started = False
            i += 1
            while i < n and quoted[i] == " ":
                i += 1
        else:
            started = True
            current.append(c)
            i += 1
    if started:
        args.append("".join(current))
    return args


@pytest.mark.parametrize(
    "arg",
    [
        "simple",
        "with space",
        'has"quote',
        "trailing\\",
        "back\\\\slash",
        'quote\\"combo',
        "",
        "unicode-héllo-世界",
        "-y",
        "--flag=value with space",
    ],
)
def test_quote_argument_roundtrips(arg: str) -> None:
    quoted = colossal_native.win_quote_argument(arg)
    parsed = _roundtrip_via_shlex_like_split(quoted)
    assert parsed == [arg], f"{arg!r} quoted as {quoted!r} did not round-trip (got {parsed!r})"


def test_simple_argument_is_not_quoted() -> None:
    assert colossal_native.win_quote_argument("simple") == "simple"
    assert colossal_native.win_quote_argument("-y") == "-y"


def test_empty_argument_is_quoted() -> None:
    # An empty arg must still occupy a slot on the command line.
    assert colossal_native.win_quote_argument("") == '""'


def test_build_command_line_roundtrips_full_argv() -> None:
    argv = [
        "ffmpeg.exe",
        "-y",
        "-i",
        "C:\\Users\\Test User\\input file.wav",
        "-c:a",
        "libmp3lame",
        "out.mp3",
    ]
    cmdline = colossal_native.win_build_command_line(argv)
    assert _roundtrip_via_shlex_like_split(cmdline) == argv
