#include <pybind11/chrono.h>
#include <pybind11/complex.h>
#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/stl/filesystem.h>

#include "colossal/artifact.hpp"
#include "colossal/capability.hpp"
#include "colossal/discovery.hpp"
#include "colossal/engine.hpp"
#include "colossal/error.hpp"
#include "colossal/inspector.hpp"
#include "colossal/job.hpp"
#include "colossal/pipeline.hpp"
#include "colossal/process.hpp"
#include "colossal/request.hpp"
#include "colossal/result.hpp"
#include "colossal/runtime.hpp"
#include "colossal/types.hpp"
#include "colossal/win_argv_quote.hpp"

namespace py = pybind11;
using namespace colossal;

PYBIND11_MODULE(colossal_native, m) {
    m.doc() = "Colossal Conversor v4 C++ Native Core";

    // Enums
    py::enum_<JobStatus>(m, "JobStatus")
        .value("Pending", JobStatus::Pending)
        .value("Running", JobStatus::Running)
        .value("Cancelling", JobStatus::Cancelling)
        .value("Cancelled", JobStatus::Cancelled)
        .value("Completed", JobStatus::Completed)
        .value("Failed", JobStatus::Failed)
        .value("Partial", JobStatus::Partial)
        .export_values();

    py::enum_<Cardinality>(m, "Cardinality")
        .value("OneToOne", Cardinality::OneToOne)
        .value("OneToMany", Cardinality::OneToMany)
        .value("ManyToOne", Cardinality::ManyToOne)
        .value("ManyToMany", Cardinality::ManyToMany)
        .export_values();

    py::enum_<ArtifactRole>(m, "ArtifactRole")
        .value("Input", ArtifactRole::Input)
        .value("Intermediate", ArtifactRole::Intermediate)
        .value("Output", ArtifactRole::Output)
        .value("Auxiliary", ArtifactRole::Auxiliary)
        .export_values();

    py::enum_<ErrorCode>(m, "ErrorCode")
        .value("InvalidRequest", ErrorCode::InvalidRequest)
        .value("UnsupportedFormat", ErrorCode::UnsupportedFormat)
        .value("CapabilityNotFound", ErrorCode::CapabilityNotFound)
        .value("MissingDependency", ErrorCode::MissingDependency)
        .value("ExecutionFailed", ErrorCode::ExecutionFailed)
        .value("Cancelled", ErrorCode::Cancelled)
        .value("OutputFailure", ErrorCode::OutputFailure)
        .value("PipelineFailure", ErrorCode::PipelineFailure)
        .value("Timeout", ErrorCode::Timeout)
        .value("Unknown", ErrorCode::Unknown)
        .export_values();

    // Error
    py::class_<Error>(m, "Error")
        .def(py::init<ErrorCode, std::string, std::optional<std::string>, std::optional<int>>(),
             py::arg("code"), py::arg("message"),
             py::arg("details") = std::nullopt, py::arg("stage_index") = std::nullopt)
        .def_property_readonly("code", &Error::code)
        .def_property_readonly("message", &Error::message)
        .def_property_readonly("details", &Error::details)
        .def_property_readonly("stage_index", &Error::stage_index)
        .def("__str__", &Error::what);

    // Artifact
    py::class_<Artifact>(m, "Artifact")
        .def(py::init<>())
        .def(py::init<std::filesystem::path, std::string, ArtifactRole, std::optional<int64_t>>(),
             py::arg("path"), py::arg("format_id"), py::arg("role") = ArtifactRole::Output, py::arg("size_bytes") = std::nullopt)
        .def_readwrite("path", &Artifact::path)
        .def_readwrite("format_id", &Artifact::format_id)
        .def_readwrite("role", &Artifact::role)
        .def_readwrite("size_bytes", &Artifact::size_bytes)
        .def("exists", &Artifact::exists)
        .def("filename", &Artifact::filename);

    // Capability
    py::class_<Capability>(m, "Capability")
        .def(py::init<>())
        .def_readwrite("id", &Capability::id)
        .def_readwrite("name", &Capability::name)
        .def_readwrite("engine_id", &Capability::engine_id)
        .def_readwrite("input_formats", &Capability::input_formats)
        .def_readwrite("output_formats", &Capability::output_formats)
        .def_readwrite("requirements", &Capability::requirements)
        .def_readwrite("cardinality", &Capability::cardinality)
        .def_readwrite("fidelity", &Capability::fidelity)
        .def("supports", &Capability::supports);

    // Request
    py::class_<Request>(m, "Request")
        .def(py::init<>())
        .def_readwrite("id", &Request::id)
        .def_readwrite("input_artifacts", &Request::input_artifacts)
        .def_readwrite("output_format_id", &Request::output_format_id)
        .def_readwrite("destination_path", &Request::destination_path)
        .def_readwrite("options", &Request::options)
        .def_property_readonly("is_multi_input", &Request::is_multi_input);

    // PipelineStage & Pipeline
    py::class_<PipelineStage>(m, "PipelineStage")
        .def(py::init<>())
        .def_readwrite("stage_index", &PipelineStage::stage_index)
        .def_readwrite("name", &PipelineStage::name)
        .def_readwrite("capability", &PipelineStage::capability)
        .def_readwrite("input_format_id", &PipelineStage::input_format_id)
        .def_readwrite("output_format_id", &PipelineStage::output_format_id)
        .def_readwrite("options", &PipelineStage::options);

    py::class_<Pipeline>(m, "Pipeline")
        .def(py::init<>())
        .def_readwrite("stages", &Pipeline::stages)
        .def_property_readonly("stage_count", &Pipeline::stage_count)
        .def_property_readonly("is_multi_stage", &Pipeline::is_multi_stage)
        .def("validate", &Pipeline::validate);

    // Job
    py::class_<Job, std::shared_ptr<Job>>(m, "Job")
        .def(py::init<std::string, Request, Pipeline>(),
             py::arg("id"), py::arg("request"), py::arg("pipeline"))
        .def_property_readonly("id", &Job::id)
        .def_property_readonly("request", &Job::request)
        .def_property_readonly("pipeline", &Job::pipeline)
        .def_property_readonly("status", &Job::status)
        .def_property_readonly("progress", &Job::progress)
        .def_property_readonly("produced_artifacts", &Job::produced_artifacts)
        .def_property_readonly("intermediate_artifacts", &Job::intermediate_artifacts)
        .def_property_readonly("errors", &Job::errors)
        .def("start", &Job::start)
        .def("update_progress", &Job::update_progress)
        .def("request_cancel", &Job::request_cancel)
        .def("mark_cancelled", &Job::mark_cancelled)
        .def("complete", &Job::complete)
        .def("fail", &Job::fail)
        .def_property_readonly("duration_seconds", &Job::duration_seconds);

    // Result
    py::class_<Result>(m, "Result")
        .def(py::init<>())
        .def_readwrite("job_id", &Result::job_id)
        .def_readwrite("status", &Result::status)
        .def_readwrite("output_artifacts", &Result::output_artifacts)
        .def_readwrite("error", &Result::error)
        .def_readwrite("duration_seconds", &Result::duration_seconds)
        .def_property_readonly("is_success", &Result::is_success)
        .def_property_readonly("is_cancelled", &Result::is_cancelled)
        .def_property_readonly("is_failed", &Result::is_failed);

    // ToolDiscovery
    py::class_<ToolDiscovery>(m, "ToolDiscovery")
        .def_static("instance", &ToolDiscovery::instance, py::return_value_policy::reference)
        .def("register_custom_path", &ToolDiscovery::register_custom_path, py::arg("tool_name"), py::arg("path"))
        .def("add_search_directory", &ToolDiscovery::add_search_directory, py::arg("dir"))
        .def("find_tool", &ToolDiscovery::find_tool, py::arg("tool_name"))
        .def("require_tool", &ToolDiscovery::require_tool, py::arg("tool_name"), py::arg("stage_index") = std::nullopt)
        .def("clear_cache", &ToolDiscovery::clear_cache);

    // MediaMetadata
    py::class_<MediaMetadata>(m, "MediaMetadata")
        .def(py::init<>())
        .def_readwrite("format_id", &MediaMetadata::format_id)
        .def_readwrite("mime_type", &MediaMetadata::mime_type)
        .def_readwrite("file_size_bytes", &MediaMetadata::file_size_bytes)
        .def_readwrite("width", &MediaMetadata::width)
        .def_readwrite("height", &MediaMetadata::height)
        .def_readwrite("channels", &MediaMetadata::channels)
        .def_readwrite("sample_rate", &MediaMetadata::sample_rate)
        .def_readwrite("duration_seconds", &MediaMetadata::duration_seconds)
        .def_readwrite("page_count", &MediaMetadata::page_count)
        .def_readwrite("properties", &MediaMetadata::properties);

    // FormatDetector
    py::class_<FormatDetector>(m, "FormatDetector")
        .def_static("detect_format", &FormatDetector::detect_format, py::arg("path"))
        .def_static("detect_mime", &FormatDetector::detect_mime, py::arg("path"));

    // MediaInspector
    py::class_<MediaInspector>(m, "MediaInspector")
        .def_static("inspect", &MediaInspector::inspect, py::arg("path"));

    // ProcessResult & ProcessSupervisor
    py::class_<ProcessResult>(m, "ProcessResult")
        .def(py::init<>())
        .def_readwrite("exit_code", &ProcessResult::exit_code)
        .def_readwrite("stdout_text", &ProcessResult::stdout_text)
        .def_readwrite("stderr_text", &ProcessResult::stderr_text)
        .def_readwrite("duration_seconds", &ProcessResult::duration_seconds)
        .def_readwrite("cancelled", &ProcessResult::cancelled)
        .def_property_readonly("is_success", &ProcessResult::is_success);

    py::class_<ProcessSupervisor>(m, "ProcessSupervisor")
        .def_static("execute", [](
            const std::vector<std::string>& command,
            const std::optional<std::filesystem::path>& cwd,
            std::optional<double> timeout_seconds
        ) {
            py::gil_scoped_release release;
            return ProcessSupervisor::execute(command, cwd, nullptr, nullptr, timeout_seconds);
        }, py::arg("command"), py::arg("cwd") = std::nullopt, py::arg("timeout_seconds") = std::nullopt);

    // NativeRuntime
    py::class_<NativeRuntime, std::shared_ptr<NativeRuntime>>(m, "NativeRuntime")
        .def(py::init<size_t, std::filesystem::path>(),
             py::arg("thread_count") = 4, py::arg("temp_dir") = "")
        .def("execute_job", [](NativeRuntime& self, std::shared_ptr<Job> job) {
            py::gil_scoped_release release;
            return self.execute_job(job);
        })
        .def("execute_batch", [](NativeRuntime& self, const std::vector<std::shared_ptr<Job>>& jobs) {
            py::gil_scoped_release release;
            return self.execute_batch(jobs);
        })
        .def("get_engine", &NativeRuntime::get_engine)
        .def("has_engine", [](NativeRuntime& self, const std::string& id) {
            return self.get_engine(id) != nullptr;
        })
        .def("shutdown", &NativeRuntime::shutdown);

    // Pure string logic used by the Win32 process backend to build a safe
    // command line. Exposed so it can be unit-tested on every platform,
    // independent of whether the Windows backend itself can be exercised
    // here — it has no OS dependency.
    m.def("win_quote_argument", &win_quote_argument, py::arg("arg"));
    m.def("win_build_command_line", &win_build_command_line, py::arg("args"));
}
