// Win32 backend for ProcessSupervisor::execute. See process_posix.cpp for
// the macOS/Linux backend; only one of the two is compiled per platform
// (selected in CMakeLists.txt). Both must preserve the same externally
// observable contract declared in process.hpp.
//
// A Job Object (not just TerminateProcess) gives cancellation/timeout the
// same whole-tree-dies semantics the POSIX backend gets from process
// groups + SIGKILL. stdout/stderr are each read on their own thread so one
// filling up can't block the other from draining. All HANDLEs are owned by
// a small RAII wrapper.
#include "colossal/process.hpp"
#include "colossal/error.hpp"
#include "colossal/win_argv_quote.hpp"

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <chrono>
#include <string>
#include <thread>
#include <vector>

namespace colossal {

namespace {

class UniqueHandle {
public:
    UniqueHandle() = default;
    explicit UniqueHandle(HANDLE h) : handle_(h) {}
    ~UniqueHandle() { reset(); }

    UniqueHandle(const UniqueHandle&) = delete;
    UniqueHandle& operator=(const UniqueHandle&) = delete;

    UniqueHandle(UniqueHandle&& other) noexcept : handle_(other.release()) {}
    UniqueHandle& operator=(UniqueHandle&& other) noexcept {
        if (this != &other) {
            reset();
            handle_ = other.release();
        }
        return *this;
    }

    [[nodiscard]] HANDLE get() const noexcept { return handle_; }

    HANDLE release() noexcept {
        HANDLE h = handle_;
        handle_ = nullptr;
        return h;
    }

    void reset(HANDLE h = nullptr) noexcept {
        if (handle_ != nullptr && handle_ != INVALID_HANDLE_VALUE) {
            CloseHandle(handle_);
        }
        handle_ = h;
    }

    explicit operator bool() const noexcept {
        return handle_ != nullptr && handle_ != INVALID_HANDLE_VALUE;
    }

private:
    HANDLE handle_ = nullptr;
};

std::wstring utf8_to_wide(const std::string& s) {
    if (s.empty()) {
        return {};
    }
    int size = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), static_cast<int>(s.size()), nullptr, 0);
    std::wstring result(static_cast<size_t>(size), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, s.c_str(), static_cast<int>(s.size()), result.data(), size);
    return result;
}

// Drains one pipe on a background thread into a string, optionally
// invoking a per-line callback (used for stderr progress parsing).
struct PipeReader {
    UniqueHandle read_handle;
    std::string data;
    std::function<void(const std::string&)> on_line;
    std::string pending_line;
    std::thread worker;

    void start() {
        worker = std::thread([this]() {
            char buffer[4096];
            DWORD bytes_read = 0;
            while (ReadFile(read_handle.get(), buffer, sizeof(buffer), &bytes_read, nullptr) && bytes_read > 0) {
                data.append(buffer, bytes_read);
                if (on_line) {
                    for (DWORD i = 0; i < bytes_read; ++i) {
                        char c = buffer[i];
                        if (c == '\n' || c == '\r') {
                            if (!pending_line.empty()) {
                                on_line(pending_line);
                                pending_line.clear();
                            }
                        } else {
                            pending_line += c;
                        }
                    }
                }
            }
        });
    }

    void join() {
        if (worker.joinable()) {
            worker.join();
        }
    }
};

} // namespace

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

    UniqueHandle job(CreateJobObjectW(nullptr, nullptr));
    if (!job) {
        throw Error(ErrorCode::ExecutionFailed, "Failed to create Job Object for process supervision");
    }
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limit_info{};
    limit_info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if (!SetInformationJobObject(
            job.get(), JobObjectExtendedLimitInformation, &limit_info, sizeof(limit_info)
        )) {
        throw Error(ErrorCode::ExecutionFailed, "Failed to configure Job Object limits");
    }

    SECURITY_ATTRIBUTES sa{};
    sa.nLength = sizeof(sa);
    sa.bInheritHandle = TRUE;

    HANDLE stdout_read_raw = nullptr;
    HANDLE stdout_write_raw = nullptr;
    HANDLE stderr_read_raw = nullptr;
    HANDLE stderr_write_raw = nullptr;
    if (!CreatePipe(&stdout_read_raw, &stdout_write_raw, &sa, 0) ||
        !CreatePipe(&stderr_read_raw, &stderr_write_raw, &sa, 0)) {
        throw Error(ErrorCode::ExecutionFailed, "Failed to create pipes for process execution");
    }
    UniqueHandle stdout_read(stdout_read_raw);
    UniqueHandle stdout_write(stdout_write_raw);
    UniqueHandle stderr_read(stderr_read_raw);
    UniqueHandle stderr_write(stderr_write_raw);

    // The parent's read ends must not be inherited by the child, or the
    // child's pipe handles never see EOF once the child exits.
    if (!SetHandleInformation(stdout_read.get(), HANDLE_FLAG_INHERIT, 0) ||
        !SetHandleInformation(stderr_read.get(), HANDLE_FLAG_INHERIT, 0)) {
        throw Error(ErrorCode::ExecutionFailed, "Failed to configure pipe handle inheritance");
    }

    std::wstring cmdline_w = utf8_to_wide(win_build_command_line(command));
    std::vector<wchar_t> cmdline_buf(cmdline_w.begin(), cmdline_w.end());
    cmdline_buf.push_back(L'\0');

    std::wstring cwd_w;
    const wchar_t* cwd_ptr = nullptr;
    if (cwd.has_value()) {
        cwd_w = cwd.value().wstring();
        cwd_ptr = cwd_w.c_str();
    }

    STARTUPINFOW si{};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESTDHANDLES;
    si.hStdOutput = stdout_write.get();
    si.hStdError = stderr_write.get();
    si.hStdInput = GetStdHandle(STD_INPUT_HANDLE);

    PROCESS_INFORMATION pi{};
    BOOL created = CreateProcessW(
        nullptr, // resolved from the command line's first token, like execvp
        cmdline_buf.data(),
        nullptr,
        nullptr,
        TRUE, // inherit handles: required for the pipe write ends
        CREATE_SUSPENDED | CREATE_NO_WINDOW,
        nullptr, // inherit the parent's environment
        cwd_ptr,
        &si,
        &pi
    );

    // The child has its own copies of the write ends now (or never did, if
    // creation failed); the parent must not keep them open, or the reader
    // threads below would never see EOF.
    stdout_write.reset();
    stderr_write.reset();

    if (!created) {
        throw Error(ErrorCode::ExecutionFailed, "CreateProcessW failed to start the process");
    }

    UniqueHandle process_handle(pi.hProcess);
    UniqueHandle thread_handle(pi.hThread);

    // Assign to the Job Object before resuming, so the process can never
    // run even briefly outside job supervision.
    if (!AssignProcessToJobObject(job.get(), process_handle.get())) {
        TerminateProcess(process_handle.get(), 1);
        throw Error(ErrorCode::ExecutionFailed, "Failed to assign process to Job Object");
    }
    ResumeThread(thread_handle.get());

    PipeReader stdout_reader{std::move(stdout_read)};
    PipeReader stderr_reader{std::move(stderr_read)};
    stderr_reader.on_line = on_stderr_line;
    stdout_reader.start();
    stderr_reader.start();

    bool is_cancelled = false;
    bool timed_out = false;

    while (true) {
        DWORD wait_result = WaitForSingleObject(process_handle.get(), 20);
        if (wait_result == WAIT_OBJECT_0) {
            break;
        }

        if (cancel_token && cancel_token->load()) {
            is_cancelled = true;
            // Kills the entire job (process + all descendants), not just
            // this one process — the Win32 equivalent of signalling a
            // whole POSIX process group.
            TerminateJobObject(job.get(), 1);
            WaitForSingleObject(process_handle.get(), INFINITE);
            break;
        }

        if (timeout_seconds.has_value()) {
            double elapsed =
                std::chrono::duration<double>(std::chrono::steady_clock::now() - start_time).count();
            if (elapsed > timeout_seconds.value()) {
                timed_out = true;
                TerminateJobObject(job.get(), 1);
                WaitForSingleObject(process_handle.get(), INFINITE);
                break;
            }
        }
    }

    // Always join the reader threads before returning or throwing, so no
    // thread is ever left running against a handle we're about to close.
    stdout_reader.join();
    stderr_reader.join();

    if (timed_out) {
        throw Error(
            ErrorCode::Timeout,
            "Process timed out after " + std::to_string(timeout_seconds.value()) + "s"
        );
    }

    DWORD exit_code = 0;
    GetExitCodeProcess(process_handle.get(), &exit_code);

    auto finish_time = std::chrono::steady_clock::now();
    double duration = std::chrono::duration<double>(finish_time - start_time).count();

    return ProcessResult{
        .exit_code = static_cast<int>(exit_code),
        .stdout_text = std::move(stdout_reader.data),
        .stderr_text = std::move(stderr_reader.data),
        .duration_seconds = duration,
        .cancelled = is_cancelled,
    };
}

} // namespace colossal
