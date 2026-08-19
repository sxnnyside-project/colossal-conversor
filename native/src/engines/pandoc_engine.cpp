#include "colossal/discovery.hpp"
#include "colossal/engine.hpp"
#include "colossal/process.hpp"

namespace colossal {

class PandocEngine : public BaseEngine {
public:
    [[nodiscard]] std::string engine_id() const override {
        return "pandoc";
    }

    [[nodiscard]] std::vector<std::string> required_tools() const override {
        return {"pandoc"};
    }

    std::vector<Artifact> execute(const ExecutionContext& ctx) override {
        auto pandoc_path = ToolDiscovery::instance().require_tool("pandoc", ctx.stage_index);

        const auto& primary = ctx.primary_input();
        const auto& src = primary.path;
        const auto& dst = ctx.destination_path;

        std::error_code ec;
        std::filesystem::create_directories(dst.parent_path(), ec);

        std::vector<std::string> cmd = {
            pandoc_path.string(),
            src.string(),
            "-o",
            dst.string()
        };

        if (ctx.output_format_id == "pdf") {
            // Check for available PDF rendering engines
            std::vector<std::string> pdf_engines = {"typst", "weasyprint", "wkhtmltopdf", "xelatex", "pdflatex", "lualatex"};
            for (const auto& eng : pdf_engines) {
                auto found = ToolDiscovery::instance().find_tool(eng);
                if (found.has_value()) {
                    cmd.push_back("--pdf-engine=" + found.value().string());
                    break;
                }
            }
        }

        auto res = ProcessSupervisor::execute(cmd, std::nullopt, ctx.cancel_token);

        if (res.cancelled) {
            throw Error(ErrorCode::Cancelled, "Pandoc conversion was cancelled", std::nullopt, ctx.stage_index);
        }
        if (!res.is_success()) {
            std::string details = res.stderr_text;
            if (ctx.output_format_id == "pdf" && details.find("pdf-engine") != std::string::npos) {
                details += "\n\nTip: Markdown to PDF conversion requires a PDF engine (such as typst, weasyprint, wkhtmltopdf, or pdflatex).";
            }
            throw Error(ErrorCode::ExecutionFailed, "Pandoc failed with exit code " + std::to_string(res.exit_code), details, ctx.stage_index);
        }

        auto art = verify_single_output(dst, ctx.output_format_id, ctx.stage_index);
        return {art};
    }
};

std::shared_ptr<BaseEngine> create_pandoc_engine() {
    return std::make_shared<PandocEngine>();
}

} // namespace colossal
