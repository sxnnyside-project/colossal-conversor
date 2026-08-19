#pragma once

#include <string>
#include <unordered_map>
#include <vector>

#include "capability.hpp"
#include "error.hpp"

namespace colossal {

struct PipelineStage {
    int stage_index{0};
    std::string name;
    Capability capability;
    std::string input_format_id;
    std::string output_format_id;
    std::unordered_map<std::string, std::string> options;
};

struct Pipeline {
    std::vector<PipelineStage> stages;

    [[nodiscard]] size_t stage_count() const noexcept {
        return stages.size();
    }

    [[nodiscard]] bool is_multi_stage() const noexcept {
        return stages.size() > 1;
    }

    void validate() const {
        if (stages.empty()) {
            throw Error(ErrorCode::InvalidRequest, "Pipeline must contain at least one stage");
        }
        for (size_t i = 0; i < stages.size(); ++i) {
            if (stages[i].stage_index != static_cast<int>(i)) {
                throw Error(
                    ErrorCode::PipelineFailure,
                    "Stage index mismatch: expected " + std::to_string(i) + ", got " + std::to_string(stages[i].stage_index),
                    std::nullopt,
                    static_cast<int>(i)
                );
            }
            if (i > 0) {
                const auto& prev = stages[i - 1];
                const auto& curr = stages[i];
                if (prev.output_format_id != curr.input_format_id) {
                    throw Error(
                        ErrorCode::PipelineFailure,
                        "Pipeline format discontinuity: stage " + std::to_string(i - 1) +
                        " outputs '" + prev.output_format_id + "' but stage " +
                        std::to_string(i) + " expects '" + curr.input_format_id + "'",
                        std::nullopt,
                        static_cast<int>(i)
                    );
                }
            }
        }
    }
};

} // namespace colossal
