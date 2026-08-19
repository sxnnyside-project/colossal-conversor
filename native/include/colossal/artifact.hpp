#pragma once

#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>

#include "types.hpp"

namespace colossal {

struct Artifact {
    std::filesystem::path path;
    std::string format_id;
    ArtifactRole role{ArtifactRole::Output};
    std::optional<int64_t> size_bytes{std::nullopt};

    [[nodiscard]] bool exists() const {
        std::error_code ec;
        return std::filesystem::exists(path, ec);
    }

    [[nodiscard]] std::string filename() const {
        return path.filename().string();
    }
};

} // namespace colossal
