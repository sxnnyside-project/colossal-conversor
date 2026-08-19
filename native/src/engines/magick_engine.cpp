#include "colossal/discovery.hpp"
#include "colossal/engine.hpp"
#include "colossal/process.hpp"

namespace colossal {

class ImageMagickEngine : public BaseEngine {
public:
    [[nodiscard]] std::string engine_id() const override {
        return "magick";
    }

    [[nodiscard]] std::vector<std::string> required_tools() const override {
        return {"magick"};
    }

    std::vector<Artifact> execute(const ExecutionContext& ctx) override {
        auto magick_path = ToolDiscovery::instance().require_tool("magick", ctx.stage_index);

        const auto& primary = ctx.primary_input();
        const auto& src = primary.path;
        const auto& dst = ctx.destination_path;

        std::error_code ec;
        std::filesystem::create_directories(dst.parent_path(), ec);

        std::vector<std::string> cmd = {
            magick_path.string(),
            src.string(),
        };

        for (const auto& [opt_key, opt_val] : ctx.options) {
            if (opt_key == "quality") {
                cmd.push_back("-quality");
                cmd.push_back(opt_val);
            } else if (opt_key == "resize") {
                cmd.push_back("-resize");
                cmd.push_back(opt_val);
            }
        }

        cmd.push_back(dst.string());

        auto res = ProcessSupervisor::execute(cmd, std::nullopt, ctx.cancel_token);

        if (res.cancelled) {
            throw Error(ErrorCode::Cancelled, "ImageMagick conversion was cancelled", std::nullopt, ctx.stage_index);
        }
        if (!res.is_success()) {
            throw Error(ErrorCode::ExecutionFailed, "ImageMagick failed with exit code " + std::to_string(res.exit_code), res.stderr_text, ctx.stage_index);
        }

        auto art = verify_single_output(dst, ctx.output_format_id, ctx.stage_index);
        return {art};
    }
};

std::shared_ptr<BaseEngine> create_magick_engine() {
    return std::make_shared<ImageMagickEngine>();
}

} // namespace colossal
