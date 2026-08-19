#pragma once

#include <exception>
#include <optional>
#include <string>

#include "types.hpp"

namespace colossal {

class Error : public std::exception {
public:
    Error(
        ErrorCode code,
        std::string message,
        std::optional<std::string> details = std::nullopt,
        std::optional<int> stage_index = std::nullopt
    )
        : m_code(code)
        , m_message(std::move(message))
        , m_details(std::move(details))
        , m_stage_index(stage_index)
    {
        m_what_str = "[" + std::string(to_string(m_code)) + "] " + m_message;
        if (m_stage_index.has_value()) {
            m_what_str += " (stage " + std::to_string(m_stage_index.value()) + ")";
        }
        if (m_details.has_value() && !m_details.value().empty()) {
            m_what_str += ": " + m_details.value();
        }
    }

    [[nodiscard]] ErrorCode code() const noexcept { return m_code; }
    [[nodiscard]] const std::string& message() const noexcept { return m_message; }
    [[nodiscard]] const std::optional<std::string>& details() const noexcept { return m_details; }
    [[nodiscard]] std::optional<int> stage_index() const noexcept { return m_stage_index; }

    [[nodiscard]] const char* what() const noexcept override {
        return m_what_str.c_str();
    }

private:
    ErrorCode m_code;
    std::string m_message;
    std::optional<std::string> m_details;
    std::optional<int> m_stage_index;
    std::string m_what_str;
};

} // namespace colossal
