#pragma once

#include <atomic>
#include <chrono>
#include <filesystem>
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace colossal {

struct ProcessResult {
    int exit_code{-1};
    std::string stdout_text;
    std::string stderr_text;
    double duration_seconds{0.0};
    bool cancelled{false};

    [[nodiscard]] bool is_success() const noexcept {
        return exit_code == 0 && !cancelled;
    }
};

// Stateless. execute() blocks the calling thread for the lifetime of the
// subprocess, so callers on a GIL-bound thread must release the GIL first.
// cancel_token is polled cooperatively — cancellation can take up to one
// poll interval to be observed and terminates the whole process tree, not
// just the immediate child (POSIX: process group + SIGTERM/SIGKILL; Win32:
// Job Object termination). on_stderr_line is invoked as lines arrive
// (synchronously on the calling thread on POSIX; from a background reader
// thread on Win32 — do not assume a specific thread identity in the
// callback). Safe to call concurrently from multiple threads: each call
// owns its own pipes/child process/job object. Exactly one backend
// (process_posix.cpp or process_windows.cpp) is compiled per platform;
// both must preserve this same contract.
class ProcessSupervisor {
public:
    static ProcessResult execute(
        const std::vector<std::string>& command,
        const std::optional<std::filesystem::path>& cwd = std::nullopt,
        const std::shared_ptr<std::atomic<bool>>& cancel_token = nullptr,
        const std::function<void(const std::string&)>& on_stderr_line = nullptr,
        std::optional<double> timeout_seconds = std::nullopt
    );
};

} // namespace colossal
