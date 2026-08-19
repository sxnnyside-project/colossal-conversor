#pragma once

#include "engine.hpp"

namespace colossal {

class NativeAudioEngine : public BaseEngine {
public:
    [[nodiscard]] std::string engine_id() const override {
        return "native_audio";
    }

    [[nodiscard]] bool can_execute(const Capability& capability) const override {
        return capability.engine_id == "native_audio";
    }

    [[nodiscard]] std::vector<std::string> required_tools() const override {
        // Zero external tools required! Pure in-process C++ implementation.
        return {};
    }

    std::vector<Artifact> execute(const ExecutionContext& ctx) override;
};

std::shared_ptr<BaseEngine> create_native_audio_engine();

} // namespace colossal
