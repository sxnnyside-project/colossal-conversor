#pragma once

#include <string>
#include <vector>

namespace colossal {

// Quotes a single argument per the algorithm documented by Microsoft for
// CommandLineToArgvW-compatible parsing (the same algorithm the Windows
// CRT uses to build argv from a command line). This is pure string logic
// with no OS dependency, so it is compiled and unit-tested on every
// platform even though it is only exercised by the Win32 process backend.
std::string win_quote_argument(const std::string& arg);

// Joins already-quoted arguments into a single Win32 command line string
// (space-separated), as required by CreateProcessW's lpCommandLine.
std::string win_build_command_line(const std::vector<std::string>& args);

} // namespace colossal
