#pragma once

#include <filesystem>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

#include "engine.hpp"
#include "job.hpp"
#include "result.hpp"

namespace colossal {

// thread_count is accepted for API/ABI stability but currently unused:
// execution is intentionally sequential (see execute_batch). There is no
// worker pool here — do not reintroduce one without also wiring real
// concurrent execution through the Python bridge.
class NativeRuntime {
public:
    explicit NativeRuntime(size_t thread_count = 4, std::filesystem::path temp_dir = "");
    ~NativeRuntime() = default;

    NativeRuntime(const NativeRuntime&) = delete;
    NativeRuntime& operator=(const NativeRuntime&) = delete;

    void register_engine(std::shared_ptr<BaseEngine> engine);
    void register_engine(const std::string& name, std::shared_ptr<BaseEngine> engine);
    [[nodiscard]] std::shared_ptr<BaseEngine> get_engine(const std::string& engine_id) const;

    Result execute_job(std::shared_ptr<Job> job);
    std::vector<Result> execute_batch(const std::vector<std::shared_ptr<Job>>& jobs);

    void shutdown() {}

private:
    std::unordered_map<std::string, std::shared_ptr<BaseEngine>> m_engines;
    mutable std::mutex m_engines_mutex;

    std::filesystem::path m_temp_dir;

    void register_default_engines();
};

} // namespace colossal
