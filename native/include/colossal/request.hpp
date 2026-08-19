#pragma once

#include <filesystem>
#include <string>
#include <unordered_map>
#include <vector>

#include "artifact.hpp"

namespace colossal {

struct Request {
    std::string id;
    std::vector<Artifact> input_artifacts;
    std::string output_format_id;
    std::filesystem::path destination_path;
    std::unordered_map<std::string, std::string> options;

    [[nodiscard]] bool is_multi_input() const noexcept {
        return input_artifacts.size() > 1;
    }

    [[nodiscard]] const Artifact& primary_input() const {
        return input_artifacts.front();
    }
};

} // namespace colossal
