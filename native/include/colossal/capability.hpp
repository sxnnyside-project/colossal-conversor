#pragma once

#include <string>
#include <unordered_set>
#include <vector>

#include "types.hpp"

namespace colossal {

struct Capability {
    std::string id;
    std::string name;
    std::string engine_id;
    std::unordered_set<std::string> input_formats;
    std::unordered_set<std::string> output_formats;
    std::vector<std::string> requirements;
    Cardinality cardinality{Cardinality::OneToOne};
    std::string fidelity{"medium"};

    [[nodiscard]] bool supports(const std::string& in_fmt, const std::string& out_fmt) const {
        return input_formats.contains(in_fmt) && output_formats.contains(out_fmt);
    }
};

} // namespace colossal
