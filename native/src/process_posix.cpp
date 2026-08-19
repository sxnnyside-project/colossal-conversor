// POSIX (macOS/Linux) backend for ProcessSupervisor::execute. See
// process_windows.cpp for the Win32 backend; only one of the two is
// compiled per platform (selected in CMakeLists.txt). Both must preserve
// the same externally observable contract declared in process.hpp.
#include "colossal/process.hpp"
#include "colossal/error.hpp"

#include <chrono>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <sstream>
#include <thread>

#include <csignal>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

namespace colossal {

ProcessResult ProcessSupervisor::execute(
    const std::vector<std::string>& command,
    const std::optional<std::filesystem::path>& cwd,
    const std::shared_ptr<std::atomic<bool>>& cancel_token,
    const std::function<void(const std::string&)>& on_stderr_line,
    std::optional<double> timeout_seconds
) {
    if (command.empty()) {
        throw Error(ErrorCode::InvalidRequest, "Cannot execute an empty command");
    }

    auto start_time = std::chrono::steady_clock::now();

    int stdout_pipe[2];
    int stderr_pipe[2];

    if (pipe(stdout_pipe) != 0 || pipe(stderr_pipe) != 0) {
        throw Error(ErrorCode::ExecutionFailed, "Failed to create pipes for process execution");
    }

    pid_t pid = fork();
    if (pid < 0) {
        close(stdout_pipe[0]); close(stdout_pipe[1]);
        close(stderr_pipe[0]); close(stderr_pipe[1]);
        throw Error(ErrorCode::ExecutionFailed, "fork() failed to create child process");
    }

    if (pid == 0) {
        // Child process: set new process group for clean tree termination
        setpgid(0, 0);

        // Redirect stdout
        dup2(stdout_pipe[1], STDOUT_FILENO);
        close(stdout_pipe[0]);
        close(stdout_pipe[1]);

        // Redirect stderr
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stderr_pipe[0]);
        close(stderr_pipe[1]);

        // Change working directory if requested
        if (cwd.has_value()) {
            if (chdir(cwd.value().c_str()) != 0) {
                _exit(127);
            }
        }

        // Convert command args to char* array
        std::vector<char*> args;
        args.reserve(command.size() + 1);
        for (const auto& arg : command) {
            args.push_back(const_cast<char*>(arg.c_str()));
        }
        args.push_back(nullptr);

        execvp(args[0], args.data());
        // If execvp fails
        _exit(127);
    }

    // Parent process
    close(stdout_pipe[1]);
    close(stderr_pipe[1]);

    // Set read pipes to non-blocking
    fcntl(stdout_pipe[0], F_SETFL, O_NONBLOCK);
    fcntl(stderr_pipe[0], F_SETFL, O_NONBLOCK);

    std::string stdout_str;
    std::string stderr_str;
    std::string current_stderr_line;

    char buffer[4096];
    bool is_cancelled = false;
    int exit_status = -1;
    bool child_exited = false;

    while (!child_exited) {
        // Check cancellation token
        if (cancel_token && cancel_token->load()) {
            is_cancelled = true;
            // Terminate whole process group
            kill(-pid, SIGTERM);
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            kill(-pid, SIGKILL);
        }

        // Check timeout
        if (timeout_seconds.has_value()) {
            auto elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start_time).count();
            if (elapsed > timeout_seconds.value()) {
                kill(-pid, SIGKILL);
                close(stdout_pipe[0]);
                close(stderr_pipe[0]);
                throw Error(ErrorCode::Timeout, "Process timed out after " + std::to_string(timeout_seconds.value()) + "s");
            }
        }

        // Read stdout
        ssize_t count_out = read(stdout_pipe[0], buffer, sizeof(buffer) - 1);
        if (count_out > 0) {
            buffer[count_out] = '\0';
            stdout_str.append(buffer, count_out);
        }

        // Read stderr
        ssize_t count_err = read(stderr_pipe[0], buffer, sizeof(buffer) - 1);
        if (count_err > 0) {
            buffer[count_err] = '\0';
            stderr_str.append(buffer, count_err);
            if (on_stderr_line) {
                for (ssize_t i = 0; i < count_err; ++i) {
                    if (buffer[i] == '\n' || buffer[i] == '\r') {
                        if (!current_stderr_line.empty()) {
                            on_stderr_line(current_stderr_line);
                            current_stderr_line.clear();
                        }
                    } else {
                        current_stderr_line += buffer[i];
                    }
                }
            }
        }

        // Poll child status
        int status = 0;
        pid_t res = waitpid(pid, &status, WNOHANG);
        if (res == pid) {
            child_exited = true;
            if (WIFEXITED(status)) {
                exit_status = WEXITSTATUS(status);
            } else if (WIFSIGNALED(status)) {
                exit_status = 128 + WTERMSIG(status);
            }
        } else if (res < 0) {
            child_exited = true;
        }

        if (!child_exited) {
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
        }
    }

    // Drain remaining output
    while (true) {
        ssize_t count_out = read(stdout_pipe[0], buffer, sizeof(buffer) - 1);
        if (count_out <= 0) break;
        stdout_str.append(buffer, count_out);
    }
    while (true) {
        ssize_t count_err = read(stderr_pipe[0], buffer, sizeof(buffer) - 1);
        if (count_err <= 0) break;
        stderr_str.append(buffer, count_err);
    }

    close(stdout_pipe[0]);
    close(stderr_pipe[0]);

    auto finish_time = std::chrono::steady_clock::now();
    double duration = std::chrono::duration<double>(finish_time - start_time).count();

    return ProcessResult{
        .exit_code = exit_status,
        .stdout_text = std::move(stdout_str),
        .stderr_text = std::move(stderr_str),
        .duration_seconds = duration,
        .cancelled = is_cancelled,
    };
}

} // namespace colossal
