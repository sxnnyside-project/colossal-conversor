#pragma once

#include <optional>
#include <string>
#include <vector>

#include "artifact.hpp"
#include "error.hpp"
#include "types.hpp"

namespace colossal {

struct Result {
    std::string job_id;
    JobStatus status{JobStatus::Pending};
    std::vector<Artifact> output_artifacts;
    std::optional<Error> error{std::nullopt};
    double duration_seconds{0.0};

    [[nodiscard]] bool is_success() const noexcept {
        return status == JobStatus::Completed;
    }

    [[nodiscard]] bool is_cancelled() const noexcept {
        return status == JobStatus::Cancelled;
    }

    [[nodiscard]] bool is_failed() const noexcept {
        return status == JobStatus::Failed;
    }
};

} // namespace colossal
