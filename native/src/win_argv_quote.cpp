#include "colossal/win_argv_quote.hpp"

namespace colossal {

std::string win_quote_argument(const std::string& arg) {
    // No special characters and non-empty: pass through unquoted, matching
    // CreateProcessW/CommandLineToArgvW's own behavior for plain tokens.
    if (!arg.empty() && arg.find_first_of(" \t\n\v\"") == std::string::npos) {
        return arg;
    }

    std::string result = "\"";
    for (auto it = arg.begin();; ++it) {
        size_t num_backslashes = 0;
        while (it != arg.end() && *it == '\\') {
            ++it;
            ++num_backslashes;
        }

        if (it == arg.end()) {
            // Escape all backslashes, since the closing quote we're about
            // to append would otherwise be absorbed as an escape target.
            result.append(num_backslashes * 2, '\\');
            break;
        }
        if (*it == '"') {
            // Escape all backslashes and the literal quote that follows them.
            result.append(num_backslashes * 2 + 1, '\\');
            result.push_back(*it);
        } else {
            // Backslashes not followed by a quote are literal.
            result.append(num_backslashes, '\\');
            result.push_back(*it);
        }
    }
    result.push_back('"');
    return result;
}

std::string win_build_command_line(const std::vector<std::string>& args) {
    std::string cmdline;
    for (size_t i = 0; i < args.size(); ++i) {
        if (i > 0) {
            cmdline.push_back(' ');
        }
        cmdline += win_quote_argument(args[i]);
    }
    return cmdline;
}

} // namespace colossal
