#include "colossal/discovery.hpp"

#include <cstdlib>
#include <sstream>

#if defined(_WIN32)
#include <windows.h>
#else
#include <unistd.h>
#endif

namespace colossal {

ToolDiscovery& ToolDiscovery::instance() {
    static ToolDiscovery s_instance;
    return s_instance;
}

void ToolDiscovery::register_custom_path(const std::string& tool_name, const std::filesystem::path& path) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_custom_paths[tool_name] = path;
    m_cache[tool_name] = path;
}

void ToolDiscovery::add_search_directory(const std::filesystem::path& dir) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_search_dirs.push_back(dir);
    m_cache.clear();
}

void ToolDiscovery::clear_cache() {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_cache.clear();
}

std::optional<std::filesystem::path> ToolDiscovery::find_tool(const std::string& tool_name) {
    std::lock_guard<std::mutex> lock(m_mutex);

    auto it = m_cache.find(tool_name);
    if (it != m_cache.end()) {
        return it->second;
    }

    // Check custom paths
    auto cust_it = m_custom_paths.find(tool_name);
    if (cust_it != m_custom_paths.end()) {
        std::error_code ec;
        if (std::filesystem::exists(cust_it->second, ec)) {
            m_cache[tool_name] = cust_it->second;
            return cust_it->second;
        }
    }

    // Check search directories
    for (const auto& dir : m_search_dirs) {
        auto candidate = dir / tool_name;
        std::error_code ec;
        if (std::filesystem::exists(candidate, ec)) {
            m_cache[tool_name] = candidate;
            return candidate;
        }
    }

    // Check system PATH
    auto sys_found = search_system_path(tool_name);
    if (sys_found.has_value()) {
        m_cache[tool_name] = sys_found;
        return sys_found;
    }

    // Aliases
    std::vector<std::string> aliases;
    if (tool_name == "soffice") {
        aliases = {"libreoffice", "soffice.bin"};
    } else if (tool_name == "magick") {
        aliases = {"convert"};
    } else if (tool_name == "pdftoppm") {
        aliases = {"pdf2image"};
    }

    for (const auto& alias : aliases) {
        auto alias_found = search_system_path(alias);
        if (alias_found.has_value()) {
            m_cache[tool_name] = alias_found;
            return alias_found;
        }
    }

    m_cache[tool_name] = std::nullopt;
    return std::nullopt;
}

#if defined(_WIN32)
namespace {
// Windows resolves a bare command name (no extension) against %PATHEXT%,
// trying each extension in order (this is what CreateProcess/cmd.exe do
// implicitly for an unqualified command). Falls back to the standard
// default list if PATHEXT isn't set, matching Windows' own documented
// default.
std::vector<std::string> windows_path_extensions() {
    std::vector<std::string> exts;
    const char* pathext_env = std::getenv("PATHEXT");
    std::string pathext = pathext_env ? pathext_env : ".COM;.EXE;.BAT;.CMD";
    std::stringstream ss(pathext);
    std::string ext;
    while (std::getline(ss, ext, ';')) {
        if (!ext.empty()) {
            exts.push_back(ext);
        }
    }
    return exts;
}
} // namespace
#endif

std::optional<std::filesystem::path> ToolDiscovery::search_system_path(const std::string& name) const {
    const char* path_env = std::getenv("PATH");
    if (!path_env) {
        return std::nullopt;
    }

#if defined(_WIN32)
    char delimiter = ';';
    bool name_has_extension = std::filesystem::path(name).has_extension();
#else
    char delimiter = ':';
#endif

    std::stringstream ss(path_env);
    std::string item;
    while (std::getline(ss, item, delimiter)) {
        if (item.empty()) continue;
        std::error_code ec;

#if defined(_WIN32)
        if (name_has_extension) {
            auto p = std::filesystem::path(item) / name;
            if (std::filesystem::exists(p, ec) && !std::filesystem::is_directory(p, ec)) {
                return p;
            }
        } else {
            // Try the bare name first (rare, but possible for extensionless
            // scripts), then each PATHEXT extension in order.
            auto bare = std::filesystem::path(item) / name;
            if (std::filesystem::exists(bare, ec) && !std::filesystem::is_directory(bare, ec)) {
                return bare;
            }
            for (const auto& ext : windows_path_extensions()) {
                auto candidate = std::filesystem::path(item) / (name + ext);
                if (std::filesystem::exists(candidate, ec) && !std::filesystem::is_directory(candidate, ec)) {
                    return candidate;
                }
            }
        }
#else
        auto p = std::filesystem::path(item) / name;
        if (std::filesystem::exists(p, ec) && !std::filesystem::is_directory(p, ec)) {
            if (access(p.c_str(), X_OK) == 0) {
                return p;
            }
        }
#endif
    }

    return std::nullopt;
}

std::filesystem::path ToolDiscovery::require_tool(const std::string& tool_name, std::optional<int> stage_index) {
    auto found = find_tool(tool_name);
    if (!found.has_value()) {
        std::string msg = "Required external conversion tool '" + tool_name + "' was not found on system";
        std::string details = "Ensure '" + tool_name + "' is installed or bundled in the application path.";
        throw Error(ErrorCode::MissingDependency, msg, details, stage_index);
    }
    return found.value();
}

} // namespace colossal
