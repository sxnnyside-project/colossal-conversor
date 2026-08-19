#include "colossal/discovery.hpp"
#include "colossal/engine.hpp"
#include "colossal/process.hpp"

#include <algorithm>
#include <iostream>
#include <regex>

namespace colossal {

namespace {

// Parses an ffmpeg "HH:MM:SS.cc" timestamp (as found in "Duration: ..." and
// "time=..." stderr lines) into seconds. Returns nullopt if unparseable.
std::optional<double> parse_ffmpeg_timestamp(const std::string& line, const std::regex& pattern) {
    std::smatch m;
    if (!std::regex_search(line, m, pattern)) {
        return std::nullopt;
    }
    double hours = std::stod(m[1]);
    double minutes = std::stod(m[2]);
    double seconds = std::stod(m[3]);
    double centis = std::stod(m[4]);
    return hours * 3600.0 + minutes * 60.0 + seconds + centis / 100.0;
}

} // namespace

class FFmpegEngine : public BaseEngine {
public:
    [[nodiscard]] std::string engine_id() const override {
        return "ffmpeg";
    }

    [[nodiscard]] std::vector<std::string> required_tools() const override {
        return {"ffmpeg"};
    }

    std::vector<Artifact> execute(const ExecutionContext& ctx) override {
        auto ffmpeg_path = ToolDiscovery::instance().require_tool("ffmpeg", ctx.stage_index);

        const auto& primary = ctx.primary_input();
        const auto& src = primary.path;
        const auto& dst = ctx.destination_path;

        std::error_code ec;
        std::filesystem::create_directories(dst.parent_path(), ec);

        std::vector<std::string> cmd = {
            ffmpeg_path.string(), "-y", "-i", src.string()
        };

        for (const auto& [opt_key, opt_val] : ctx.options) {
            if (opt_key == "vcodec") {
                cmd.push_back("-c:v"); cmd.push_back(opt_val);
            } else if (opt_key == "acodec") {
                cmd.push_back("-c:a"); cmd.push_back(opt_val);
            } else if (opt_key == "preset") {
                cmd.push_back("-preset"); cmd.push_back(opt_val);
            } else if (opt_key == "crf") {
                cmd.push_back("-crf"); cmd.push_back(opt_val);
            } else if (opt_key == "audio_bitrate") {
                cmd.push_back("-b:a"); cmd.push_back(opt_val);
            }
        }

        cmd.push_back(dst.string());

        static const std::regex duration_pattern(R"(Duration:\s*(\d+):(\d+):(\d+)\.(\d+))");
        static const std::regex time_pattern(R"(time=(\d+):(\d+):(\d+)\.(\d+))");
        auto total_duration_seconds = std::make_shared<std::optional<double>>();

        auto on_stderr = [&ctx, total_duration_seconds](const std::string& line) {
            if (!ctx.progress_callback) {
                return;
            }
            if (!total_duration_seconds->has_value()) {
                *total_duration_seconds = parse_ffmpeg_timestamp(line, duration_pattern);
                return;
            }
            auto current = parse_ffmpeg_timestamp(line, time_pattern);
            if (current.has_value() && total_duration_seconds->value() > 0.0) {
                double frac = std::clamp(current.value() / total_duration_seconds->value(), 0.0, 1.0);
                ctx.progress_callback(frac);
            }
            // Duration unknown or unparsed: report nothing rather than a fabricated number.
        };

        auto res = ProcessSupervisor::execute(cmd, std::nullopt, ctx.cancel_token, on_stderr);

        if (res.cancelled) {
            throw Error(ErrorCode::Cancelled, "FFmpeg conversion was cancelled", std::nullopt, ctx.stage_index);
        }
        if (!res.is_success()) {
            throw Error(ErrorCode::ExecutionFailed, "FFmpeg failed with exit code " + std::to_string(res.exit_code), res.stderr_text, ctx.stage_index);
        }

        auto art = verify_single_output(dst, ctx.output_format_id, ctx.stage_index);
        return {art};
    }
};

std::shared_ptr<BaseEngine> create_ffmpeg_engine() {
    return std::make_shared<FFmpegEngine>();
}

} // namespace colossal
