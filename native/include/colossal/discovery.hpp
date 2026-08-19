#pragma once

#include <filesystem>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

#include "error.hpp"

namespace colossal {

// Process-wide singleton; all state (custom paths, search dirs, resolution
// cache) is mutex-guarded and shared across every caller and every test in
// the process. Tests that register a custom path must call clear_cache()
// afterward — state here outlives the test that set it.
class ToolDiscovery {
public:
    static ToolDiscovery& instance();

    void register_custom_path(const std::string& tool_name, const std::filesystem::path& path);
    void add_search_directory(const std::filesystem::path& dir);

    [[nodiscard]] std::optional<std::filesystem::path> find_tool(const std::string& tool_name);
    [[nodiscard]] std::filesystem::path require_tool(const std::string& tool_name, std::optional<int> stage_index = std::nullopt);

    void clear_cache();

private:
    ToolDiscovery() = default;

    mutable std::mutex m_mutex;
    std::unordered_map<std::string, std::filesystem::path> m_custom_paths;
    std::vector<std::filesystem::path> m_search_dirs;
    std::unordered_map<std::string, std::optional<std::filesystem::path>> m_cache;

    std::optional<std::filesystem::path> search_system_path(const std::string& name) const;
};

} // namespace colossal
