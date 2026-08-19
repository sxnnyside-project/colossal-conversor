#pragma once

#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <unordered_map>

namespace colossal {

struct MediaMetadata {
    std::string format_id{"unknown"};
    std::string mime_type{"application/octet-stream"};
    int64_t file_size_bytes{0};

    // Visual attributes
    std::optional<int> width{std::nullopt};
    std::optional<int> height{std::nullopt};

    // Audio attributes
    std::optional<int> channels{std::nullopt};
    std::optional<int> sample_rate{std::nullopt};
    std::optional<double> duration_seconds{std::nullopt};

    // Document attributes
    std::optional<int> page_count{std::nullopt};

    std::unordered_map<std::string, std::string> properties;
};

class FormatDetector {
public:
    static std::string detect_format(const std::filesystem::path& path);
    static std::string detect_mime(const std::filesystem::path& path);
};

class MediaInspector {
public:
    static MediaMetadata inspect(const std::filesystem::path& path);
};

} // namespace colossal
