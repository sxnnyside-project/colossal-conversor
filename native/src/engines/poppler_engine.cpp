#include "colossal/discovery.hpp"
#include "colossal/engine.hpp"
#include "colossal/process.hpp"

#include <algorithm>

namespace colossal {

class PopplerEngine : public BaseEngine {
public:
    [[nodiscard]] std::string engine_id() const override {
        return "pdftoppm";
    }

    [[nodiscard]] std::vector<std::string> required_tools() const override {
        return {"pdftoppm"};
    }

    std::vector<Artifact> execute(const ExecutionContext& ctx) override {
        auto pdftoppm_path = ToolDiscovery::instance().require_tool("pdftoppm", ctx.stage_index);

        const auto& primary = ctx.primary_input();
        const auto& src = primary.path;
        const auto& to_fmt = ctx.output_format_id;
        const auto& dst = ctx.destination_path;

        std::string format_flag = "-png";
        if (to_fmt == "jpeg" || to_fmt == "jpg") {
            format_flag = "-jpeg";
        } else if (to_fmt == "tiff" || to_fmt == "tif") {
            format_flag = "-tiff";
        }

        std::filesystem::path out_dir;
        std::filesystem::path prefix;

        if (std::filesystem::is_directory(dst) || dst.extension().empty()) {
            out_dir = dst;
            prefix = out_dir / src.stem();
        } else {
            out_dir = dst.parent_path();
            prefix = out_dir / dst.stem();
        }

        std::error_code ec;
        std::filesystem::create_directories(out_dir, ec);

        std::vector<std::string> cmd = {
            pdftoppm_path.string(),
            format_flag,
            "-r",
            "150",
            src.string(),
            prefix.string()
        };

        auto res = ProcessSupervisor::execute(cmd, std::nullopt, ctx.cancel_token);

        if (res.cancelled) {
            throw Error(ErrorCode::Cancelled, "pdftoppm conversion was cancelled", std::nullopt, ctx.stage_index);
        }
        if (!res.is_success()) {
            throw Error(ErrorCode::ExecutionFailed, "pdftoppm failed with exit code " + std::to_string(res.exit_code), res.stderr_text, ctx.stage_index);
        }

        // Collect all produced page files matching the prefix
        std::vector<std::filesystem::path> produced_paths;
        for (const auto& entry : std::filesystem::directory_iterator(out_dir, ec)) {
            if (entry.is_regular_file()) {
                auto fname = entry.path().filename().string();
                if (fname.rfind(prefix.filename().string(), 0) == 0 && entry.path().extension().string().find(to_fmt) != std::string::npos) {
                    produced_paths.push_back(entry.path());
                }
            }
        }

        // Sort numerically / alphabetically by filename
        std::sort(produced_paths.begin(), produced_paths.end());

        if (produced_paths.empty()) {
            throw Error(ErrorCode::OutputFailure, "pdftoppm produced no matching page output files", std::nullopt, ctx.stage_index);
        }

        // If exactly 1 file was produced and a single-file destination path was specified, rename to exact path
        if (produced_paths.size() == 1 && !dst.extension().empty() && produced_paths[0] != dst) {
            std::filesystem::rename(produced_paths[0], dst, ec);
            produced_paths[0] = dst;
        }

        std::vector<Artifact> artifacts;
        artifacts.reserve(produced_paths.size());
        for (const auto& p : produced_paths) {
            auto canonical_p = std::filesystem::canonical(p, ec);
            auto size = static_cast<int64_t>(std::filesystem::file_size(p, ec));
            if (size <= 0) {
                throw Error(ErrorCode::OutputFailure, "pdftoppm produced an empty page file: " + p.string(), std::nullopt, ctx.stage_index);
            }
            artifacts.push_back(Artifact{
                .path = canonical_p.empty() ? p : canonical_p,
                .format_id = to_fmt,
                .role = ArtifactRole::Output,
                .size_bytes = size,
            });
        }

        return artifacts;
    }
};

std::shared_ptr<BaseEngine> create_poppler_engine() {
    return std::make_shared<PopplerEngine>();
}

} // namespace colossal
