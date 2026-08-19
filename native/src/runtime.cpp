#include "colossal/runtime.hpp"
#include "colossal/error.hpp"

#include <iostream>
#include <random>
#include <sstream>

namespace colossal {

namespace {
// Removes the multi-stage intermediate workspace on any exit path (success,
// failure, or cancellation) via stack unwinding, instead of only on success.
struct TempDirGuard {
    std::filesystem::path dir;
    ~TempDirGuard() {
        if (!dir.empty()) {
            std::error_code ec;
            std::filesystem::remove_all(dir, ec);
        }
    }
};
} // namespace

// Declarations of factory functions from engine cpp files
std::shared_ptr<BaseEngine> create_ffmpeg_engine();
std::shared_ptr<BaseEngine> create_libreoffice_engine();
std::shared_ptr<BaseEngine> create_poppler_engine();
std::shared_ptr<BaseEngine> create_magick_engine();
std::shared_ptr<BaseEngine> create_pandoc_engine();
std::shared_ptr<BaseEngine> create_native_image_engine();
std::shared_ptr<BaseEngine> create_native_audio_engine();

NativeRuntime::NativeRuntime(size_t thread_count, std::filesystem::path temp_dir)
    : m_temp_dir(std::move(temp_dir))
{
    (void)thread_count;
    if (m_temp_dir.empty()) {
        m_temp_dir = std::filesystem::temp_directory_path();
    }
    register_default_engines();
}

void NativeRuntime::register_default_engines() {
    auto native_img = create_native_image_engine();
    register_engine(native_img);
    register_engine("image", native_img);

    auto native_aud = create_native_audio_engine();
    register_engine(native_aud);
    register_engine("audio", native_aud);

    auto ffmpeg = create_ffmpeg_engine();
    register_engine(ffmpeg);
    register_engine("transcoder", ffmpeg);
    register_engine("video", ffmpeg);

    auto soffice = create_libreoffice_engine();
    register_engine(soffice);
    register_engine("libreoffice", soffice);
    register_engine("office", soffice);
    register_engine("tabular", soffice);

    auto poppler = create_poppler_engine();
    register_engine(poppler);
    register_engine("poppler", poppler);
    register_engine("pdftoppm", poppler);
    register_engine("pdf", poppler);
    register_engine("pdf_toolchain", poppler);

    auto magick = create_magick_engine();
    register_engine(magick);
    register_engine("imagemagick", magick);
    register_engine("default", magick);

    auto pandoc = create_pandoc_engine();
    register_engine(pandoc);
    register_engine("markdown", pandoc);
}

void NativeRuntime::register_engine(std::shared_ptr<BaseEngine> engine) {
    if (engine) {
        std::lock_guard<std::mutex> lock(m_engines_mutex);
        m_engines[engine->engine_id()] = engine;
    }
}

void NativeRuntime::register_engine(const std::string& name, std::shared_ptr<BaseEngine> engine) {
    if (engine && !name.empty()) {
        std::lock_guard<std::mutex> lock(m_engines_mutex);
        m_engines[name] = engine;
    }
}

std::shared_ptr<BaseEngine> NativeRuntime::get_engine(const std::string& engine_id) const {
    std::lock_guard<std::mutex> lock(m_engines_mutex);
    auto it = m_engines.find(engine_id);
    if (it != m_engines.end()) {
        return it->second;
    }
    return nullptr;
}

Result NativeRuntime::execute_job(std::shared_ptr<Job> job) {
    if (!job) {
        throw Error(ErrorCode::InvalidRequest, "Null job pointer provided to NativeRuntime");
    }

    if (job->status() == JobStatus::Cancelled) {
        return Result{
            .job_id = job->id(),
            .status = JobStatus::Cancelled,
            .output_artifacts = job->produced_artifacts(),
            .duration_seconds = job->duration_seconds().value_or(0.0),
        };
    }

    auto cancel_token = job->cancel_token();

    try {
        job->start();
        const auto& pipeline = job->pipeline();
        const auto& request = job->request();
        size_t total_stages = pipeline.stage_count();

        std::vector<Artifact> current_inputs = request.input_artifacts;
        std::vector<Artifact> produced_outputs;

        // Intermediate workspace
        std::filesystem::path stage_temp_dir;
        if (pipeline.is_multi_stage()) {
            stage_temp_dir = m_temp_dir / ("colossal_native_" + job->id());
            std::filesystem::create_directories(stage_temp_dir);
        }
        TempDirGuard temp_guard{stage_temp_dir};

        for (size_t idx = 0; idx < total_stages; ++idx) {
            const auto& stage = pipeline.stages[idx];

            auto engine = get_engine(stage.capability.engine_id);
            if (!engine) {
                throw Error(
                    ErrorCode::CapabilityNotFound,
                    "No native engine registered for engine ID '" + stage.capability.engine_id + "'",
                    std::nullopt,
                    static_cast<int>(idx)
                );
            }

            bool is_last_stage = (idx == total_stages - 1);
            std::filesystem::path dst_path;
            if (is_last_stage) {
                dst_path = request.destination_path;
            } else {
                dst_path = stage_temp_dir / ("stage_" + std::to_string(idx) + "_" + current_inputs[0].path.stem().string() + "." + stage.output_format_id);
            }

            auto on_progress = [job, idx, total_stages](double p) {
                double overall = (static_cast<double>(idx) + std::clamp(p, 0.0, 1.0)) / static_cast<double>(total_stages);
                try {
                    job->update_progress(overall);
                } catch (...) {}
            };

            ExecutionContext ctx{
                .stage_index = static_cast<int>(idx),
                .capability = stage.capability,
                .input_artifacts = current_inputs,
                .destination_path = dst_path,
                .output_format_id = stage.output_format_id,
                .options = stage.options,
                .cancel_token = cancel_token,
                .progress_callback = on_progress,
                .intermediate_dir = stage_temp_dir,
            };

            auto stage_outputs = engine->execute(ctx);

            if (!is_last_stage) {
                for (auto& art : stage_outputs) {
                    art.role = ArtifactRole::Intermediate;
                    job->add_intermediate_artifact(art);
                }
                current_inputs = stage_outputs;
            } else {
                produced_outputs = stage_outputs;
            }

            job->update_progress(static_cast<double>(idx + 1) / static_cast<double>(total_stages));
        }

        job->complete(produced_outputs);

    } catch (const Error& err) {
        if (err.code() == ErrorCode::Cancelled) {
            job->mark_cancelled();
        } else {
            job->fail(err);
        }
    } catch (const std::exception& exc) {
        job->fail(Error(ErrorCode::ExecutionFailed, exc.what()));
    }

    std::optional<Error> primary_err = std::nullopt;
    auto errs = job->errors();
    if (!errs.empty()) {
        primary_err = errs.front();
    }

    return Result{
        .job_id = job->id(),
        .status = job->status(),
        .output_artifacts = job->produced_artifacts(),
        .error = primary_err,
        .duration_seconds = job->duration_seconds().value_or(0.0),
    };
}

std::vector<Result> NativeRuntime::execute_batch(const std::vector<std::shared_ptr<Job>>& jobs) {
    std::vector<Result> results;
    results.reserve(jobs.size());
    for (const auto& job : jobs) {
        results.push_back(execute_job(job));
    }
    return results;
}

} // namespace colossal
