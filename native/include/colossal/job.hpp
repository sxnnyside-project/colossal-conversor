#pragma once

#include <atomic>
#include <chrono>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <vector>

#include "artifact.hpp"
#include "error.hpp"
#include "pipeline.hpp"
#include "request.hpp"
#include "types.hpp"

namespace colossal {

class Job {
public:
    Job(std::string id, Request request, Pipeline pipeline)
        : m_id(std::move(id))
        , m_request(std::move(request))
        , m_pipeline(std::move(pipeline))
        , m_status(JobStatus::Pending)
        , m_progress(0.0)
        , m_created_at(std::chrono::system_clock::now())
        , m_cancel_token(std::make_shared<std::atomic<bool>>(false))
    {}

    [[nodiscard]] const std::string& id() const noexcept { return m_id; }
    [[nodiscard]] const Request& request() const noexcept { return m_request; }
    [[nodiscard]] const Pipeline& pipeline() const noexcept { return m_pipeline; }

    [[nodiscard]] JobStatus status() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_status;
    }

    [[nodiscard]] double progress() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_progress;
    }

    [[nodiscard]] std::vector<Artifact> produced_artifacts() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_produced_artifacts;
    }

    [[nodiscard]] std::vector<Artifact> intermediate_artifacts() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_intermediate_artifacts;
    }

    [[nodiscard]] std::vector<Error> errors() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_errors;
    }

    void start() {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_status != JobStatus::Pending) {
            throw Error(ErrorCode::InvalidRequest, "Cannot start job not in Pending state");
        }
        m_status = JobStatus::Running;
        m_started_at = std::chrono::system_clock::now();
    }

    void update_progress(double value) {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_status != JobStatus::Running && m_status != JobStatus::Cancelling) {
            throw Error(ErrorCode::InvalidRequest, "Cannot update progress when job is not active");
        }
        m_progress = std::max(0.0, std::min(1.0, value));
    }

    // Safe to call from any thread while execution runs on another.
    void request_cancel() {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_cancel_token->store(true, std::memory_order_relaxed);
        if (m_status == JobStatus::Pending) {
            m_status = JobStatus::Cancelled;
            m_finished_at = std::chrono::system_clock::now();
        } else if (m_status == JobStatus::Running) {
            m_status = JobStatus::Cancelling;
        }
    }

    [[nodiscard]] std::shared_ptr<std::atomic<bool>> cancel_token() const noexcept {
        return m_cancel_token;
    }

    void mark_cancelled() {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_status = JobStatus::Cancelled;
        m_finished_at = std::chrono::system_clock::now();
    }

    void complete(const std::vector<Artifact>& artifacts) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_produced_artifacts = artifacts;
        m_status = JobStatus::Completed;
        m_progress = 1.0;
        m_finished_at = std::chrono::system_clock::now();
    }

    void fail(const Error& err) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_errors.push_back(err);
        m_status = JobStatus::Failed;
        m_finished_at = std::chrono::system_clock::now();
    }

    void add_intermediate_artifact(const Artifact& art) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_intermediate_artifacts.push_back(art);
    }

    [[nodiscard]] std::optional<double> duration_seconds() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_started_at.has_value() && m_finished_at.has_value()) {
            std::chrono::duration<double> diff = m_finished_at.value() - m_started_at.value();
            return diff.count();
        }
        return std::nullopt;
    }

private:
    std::string m_id;
    Request m_request;
    Pipeline m_pipeline;

    mutable std::mutex m_mutex;
    JobStatus m_status{JobStatus::Pending};
    double m_progress{0.0};
    std::vector<Artifact> m_produced_artifacts;
    std::vector<Artifact> m_intermediate_artifacts;
    std::vector<Error> m_errors;

    std::chrono::system_clock::time_point m_created_at;
    std::optional<std::chrono::system_clock::time_point> m_started_at;
    std::optional<std::chrono::system_clock::time_point> m_finished_at;

    std::shared_ptr<std::atomic<bool>> m_cancel_token;
};

} // namespace colossal
