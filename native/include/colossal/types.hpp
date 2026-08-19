#pragma once

#include <string>
#include <string_view>

namespace colossal {

enum class JobStatus {
    Pending,
    Running,
    Cancelling,
    Cancelled,
    Completed,
    Failed,
    Partial
};

enum class Cardinality {
    OneToOne,
    OneToMany,
    ManyToOne,
    ManyToMany
};

enum class ArtifactRole {
    Input,
    Intermediate,
    Output,
    Auxiliary
};

enum class ErrorCode {
    InvalidRequest,
    UnsupportedFormat,
    CapabilityNotFound,
    MissingDependency,
    ExecutionFailed,
    Cancelled,
    OutputFailure,
    PipelineFailure,
    Timeout,
    Unknown
};

inline std::string_view to_string(JobStatus s) {
    switch (s) {
        case JobStatus::Pending: return "pending";
        case JobStatus::Running: return "running";
        case JobStatus::Cancelling: return "cancelling";
        case JobStatus::Cancelled: return "cancelled";
        case JobStatus::Completed: return "completed";
        case JobStatus::Failed: return "failed";
        case JobStatus::Partial: return "partial";
    }
    return "unknown";
}

inline std::string_view to_string(Cardinality c) {
    switch (c) {
        case Cardinality::OneToOne: return "one_to_one";
        case Cardinality::OneToMany: return "one_to_many";
        case Cardinality::ManyToOne: return "many_to_one";
        case Cardinality::ManyToMany: return "many_to_many";
    }
    return "unknown";
}

inline std::string_view to_string(ArtifactRole r) {
    switch (r) {
        case ArtifactRole::Input: return "input";
        case ArtifactRole::Intermediate: return "intermediate";
        case ArtifactRole::Output: return "output";
        case ArtifactRole::Auxiliary: return "auxiliary";
    }
    return "unknown";
}

inline std::string_view to_string(ErrorCode e) {
    switch (e) {
        case ErrorCode::InvalidRequest: return "invalid_request";
        case ErrorCode::UnsupportedFormat: return "unsupported_format";
        case ErrorCode::CapabilityNotFound: return "capability_not_found";
        case ErrorCode::MissingDependency: return "missing_dependency";
        case ErrorCode::ExecutionFailed: return "execution_failed";
        case ErrorCode::Cancelled: return "cancelled";
        case ErrorCode::OutputFailure: return "output_failure";
        case ErrorCode::PipelineFailure: return "pipeline_failure";
        case ErrorCode::Timeout: return "timeout";
        case ErrorCode::Unknown: return "unknown";
    }
    return "unknown";
}

} // namespace colossal
