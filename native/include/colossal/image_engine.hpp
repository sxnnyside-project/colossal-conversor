#pragma once

#include "engine.hpp"

namespace colossal {

class NativeImageEngine : public BaseEngine {
public:
    [[nodiscard]] std::string engine_id() const override {
        return "native_image";
    }

    [[nodiscard]] bool can_execute(const Capability& capability) const override {
        return capability.engine_id == "native_image" || capability.engine_id == "magick";
    }

    [[nodiscard]] std::vector<std::string> required_tools() const override {
        // Zero external tools required! Pure in-process C++ implementation.
        return {};
    }

    std::vector<Artifact> execute(const ExecutionContext& ctx) override;
};

std::shared_ptr<BaseEngine> create_native_image_engine();

} // namespace colossal
