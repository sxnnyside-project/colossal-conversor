#pragma once

#include <atomic>
#include <filesystem>
#include <functional>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "artifact.hpp"
#include "capability.hpp"
#include "discovery.hpp"
#include "error.hpp"

namespace colossal {

struct ExecutionContext {
    int stage_index{0};
    Capability capability;
    std::vector<Artifact> input_artifacts;
    std::filesystem::path destination_path;
    std::string output_format_id;
    std::unordered_map<std::string, std::string> options;
    std::shared_ptr<std::atomic<bool>> cancel_token{nullptr};
    std::function<void(double)> progress_callback{nullptr};
    std::filesystem::path intermediate_dir;

    [[nodiscard]] const Artifact& primary_input() const {
        if (input_artifacts.empty()) {
            throw Error(ErrorCode::InvalidRequest, "ExecutionContext has no input artifacts", std::nullopt, stage_index);
        }
        return input_artifacts.front();
    }
};

// Engines are registered once and shared (via shared_ptr) across every job;
// execute() must therefore be safe to call concurrently on the same engine
// instance from different jobs/threads — do not add mutable instance state
// without synchronizing it. execute() runs on whatever thread the caller is
// on (no engine spawns its own thread); it may block for the duration of a
// subprocess and must throw Error on any failure rather than returning a
// partial/empty result.
class BaseEngine {
public:
    virtual ~BaseEngine() = default;

    [[nodiscard]] virtual std::string engine_id() const = 0;

    [[nodiscard]] virtual bool can_execute(const Capability& capability) const {
        return capability.engine_id == engine_id();
    }

    [[nodiscard]] virtual std::vector<std::string> required_tools() const {
        return {engine_id()};
    }

    virtual std::vector<Artifact> execute(const ExecutionContext& ctx) = 0;

protected:
    Artifact verify_single_output(
        const std::filesystem::path& path,
        const std::string& format_id,
        int stage_index
    ) const {
        std::error_code ec;
        if (!std::filesystem::exists(path, ec)) {
            throw Error(
                ErrorCode::OutputFailure,
                "Expected output file '" + path.string() + "' was not created by engine '" + engine_id() + "'",
                std::nullopt,
                stage_index
            );
        }
        auto size = static_cast<int64_t>(std::filesystem::file_size(path, ec));
        if (size <= 0) {
            throw Error(
                ErrorCode::OutputFailure,
                "Output file '" + path.string() + "' produced by engine '" + engine_id() + "' is empty",
                std::nullopt,
                stage_index
            );
        }
        return Artifact{
            .path = std::filesystem::canonical(path, ec),
            .format_id = format_id,
            .role = ArtifactRole::Output,
            .size_bytes = size,
        };
    }
};

} // namespace colossal
