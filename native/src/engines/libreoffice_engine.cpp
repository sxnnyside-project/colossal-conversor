#include "colossal/discovery.hpp"
#include "colossal/engine.hpp"
#include "colossal/process.hpp"

namespace colossal {

class LibreOfficeEngine : public BaseEngine {
public:
    [[nodiscard]] std::string engine_id() const override {
        return "soffice";
    }

    [[nodiscard]] std::vector<std::string> required_tools() const override {
        return {"soffice"};
    }

    std::vector<Artifact> execute(const ExecutionContext& ctx) override {
        auto soffice_path = ToolDiscovery::instance().require_tool("soffice", ctx.stage_index);

        const auto& primary = ctx.primary_input();
        const auto& src = primary.path;
        const auto& to_fmt = ctx.output_format_id;
        const auto& dst = ctx.destination_path;

        std::filesystem::path out_dir;
        std::filesystem::path expected_target;

        if (std::filesystem::is_directory(dst) || dst.extension().empty()) {
            out_dir = dst;
            expected_target = out_dir / (src.stem().string() + "." + to_fmt);
        } else {
            out_dir = dst.parent_path();
            expected_target = dst;
        }

        std::error_code ec;
        std::filesystem::create_directories(out_dir, ec);

        std::vector<std::string> cmd = {
            soffice_path.string(),
            "--headless",
            "--convert-to",
            to_fmt,
            "--outdir",
            out_dir.string(),
            src.string()
        };

        auto res = ProcessSupervisor::execute(cmd, std::nullopt, ctx.cancel_token);

        if (res.cancelled) {
            throw Error(ErrorCode::Cancelled, "LibreOffice conversion was cancelled", std::nullopt, ctx.stage_index);
        }
        if (!res.is_success()) {
            throw Error(ErrorCode::ExecutionFailed, "LibreOffice failed with exit code " + std::to_string(res.exit_code), res.stderr_text, ctx.stage_index);
        }

        auto default_produced = out_dir / (src.stem().string() + "." + to_fmt);
        if (!std::filesystem::exists(default_produced, ec) && !std::filesystem::exists(expected_target, ec)) {
            // Check for case differences or alternatives
            bool found = false;
            for (const auto& entry : std::filesystem::directory_iterator(out_dir, ec)) {
                if (entry.is_regular_file() && entry.path().stem() == src.stem()) {
                    default_produced = entry.path();
                    found = true;
                    break;
                }
            }
            if (!found) {
                throw Error(ErrorCode::OutputFailure, "LibreOffice did not produce expected output", std::nullopt, ctx.stage_index);
            }
        }

        if (std::filesystem::exists(default_produced, ec) && default_produced != expected_target) {
            std::filesystem::rename(default_produced, expected_target, ec);
        }

        auto art = verify_single_output(expected_target, to_fmt, ctx.stage_index);
        return {art};
    }
};

std::shared_ptr<BaseEngine> create_libreoffice_engine() {
    return std::make_shared<LibreOfficeEngine>();
}

} // namespace colossal
