#include "colossal/inspector.hpp"

#include <cstring>
#include <fstream>
#include <vector>

namespace colossal {

static std::vector<uint8_t> read_header(const std::filesystem::path& path, size_t max_bytes = 4096) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        return {};
    }
    std::vector<uint8_t> buffer(max_bytes);
    file.read(reinterpret_cast<char*>(buffer.data()), static_cast<std::streamsize>(max_bytes));
    buffer.resize(static_cast<size_t>(file.gcount()));
    return buffer;
}

std::string FormatDetector::detect_format(const std::filesystem::path& path) {
    auto header = read_header(path, 1024);
    if (header.empty()) {
        auto ext = path.extension().string();
        if (!ext.empty() && ext[0] == '.') ext = ext.substr(1);
        return ext.empty() ? "unknown" : ext;
    }

    const uint8_t* data = header.data();
    size_t size = header.size();

    // PNG: \x89PNG\r\n\x1a\n
    if (size >= 8 && data[0] == 0x89 && data[1] == 'P' && data[2] == 'N' && data[3] == 'G' &&
        data[4] == 0x0D && data[5] == 0x0A && data[6] == 0x1A && data[7] == 0x0A) {
        return "png";
    }

    // JPEG: \xFF\xD8\xFF
    if (size >= 3 && data[0] == 0xFF && data[1] == 0xD8 && data[2] == 0xFF) {
        return "jpeg";
    }

    // GIF: GIF87a or GIF89a
    if (size >= 6 && data[0] == 'G' && data[1] == 'I' && data[2] == 'F' && data[3] == '8' &&
        (data[4] == '7' || data[4] == '9') && data[5] == 'a') {
        return "gif";
    }

    // BMP: BM
    if (size >= 2 && data[0] == 'B' && data[1] == 'M') {
        return "bmp";
    }

    // WebP: RIFF....WEBP
    if (size >= 12 && data[0] == 'R' && data[1] == 'I' && data[2] == 'F' && data[3] == 'F' &&
        data[8] == 'W' && data[9] == 'E' && data[10] == 'B' && data[11] == 'P') {
        return "webp";
    }

    // TIFF: II*\0 or MM\0*
    if (size >= 4 && ((data[0] == 'I' && data[1] == 'I' && data[2] == 0x2A && data[3] == 0x00) ||
                      (data[0] == 'M' && data[1] == 'M' && data[2] == 0x00 && data[3] == 0x2A))) {
        return "tiff";
    }

    // PDF: %PDF-
    if (size >= 5 && data[0] == '%' && data[1] == 'P' && data[2] == 'D' && data[3] == 'F' && data[4] == '-') {
        return "pdf";
    }

    // WAV: RIFF....WAVE
    if (size >= 12 && data[0] == 'R' && data[1] == 'I' && data[2] == 'F' && data[3] == 'F' &&
        data[8] == 'W' && data[9] == 'A' && data[10] == 'V' && data[11] == 'E') {
        return "wav";
    }

    // MP3: ID3 or sync frame
    if (size >= 3 && data[0] == 'I' && data[1] == 'D' && data[2] == '3') {
        return "mp3";
    }
    if (size >= 2 && data[0] == 0xFF && (data[1] & 0xE0) == 0xE0) {
        return "mp3";
    }

    // MP4 / MOV: ....ftyp or ....moov
    if (size >= 8 && data[4] == 'f' && data[5] == 't' && data[6] == 'y' && data[7] == 'p') {
        return "mp4";
    }

    // OGG: OggS
    if (size >= 4 && data[0] == 'O' && data[1] == 'g' && data[2] == 'g' && data[3] == 'S') {
        return "ogg";
    }

    // ZIP / Office: PK\x03\x04
    if (size >= 4 && data[0] == 'P' && data[1] == 'K' && data[2] == 0x03 && data[3] == 0x04) {
        auto ext = path.extension().string();
        if (!ext.empty() && ext[0] == '.') ext = ext.substr(1);
        if (ext == "docx" || ext == "xlsx" || ext == "pptx") {
            return ext;
        }
        return "zip";
    }

    // Fallback to extension
    auto ext = path.extension().string();
    if (!ext.empty() && ext[0] == '.') ext = ext.substr(1);
    return ext.empty() ? "unknown" : ext;
}

std::string FormatDetector::detect_mime(const std::filesystem::path& path) {
    auto fmt = detect_format(path);
    if (fmt == "png") return "image/png";
    if (fmt == "jpeg" || fmt == "jpg") return "image/jpeg";
    if (fmt == "gif") return "image/gif";
    if (fmt == "bmp") return "image/bmp";
    if (fmt == "webp") return "image/webp";
    if (fmt == "tiff") return "image/tiff";
    if (fmt == "pdf") return "application/pdf";
    if (fmt == "wav") return "audio/wav";
    if (fmt == "mp3") return "audio/mpeg";
    if (fmt == "ogg") return "audio/ogg";
    if (fmt == "mp4") return "video/mp4";
    if (fmt == "mkv") return "video/x-matroska";
    if (fmt == "docx") return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
    if (fmt == "xlsx") return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
    if (fmt == "pptx") return "application/vnd.openxmlformats-officedocument.presentationml.presentation";
    return "application/octet-stream";
}

MediaMetadata MediaInspector::inspect(const std::filesystem::path& path) {
    MediaMetadata meta;
    std::error_code ec;
    meta.file_size_bytes = static_cast<int64_t>(std::filesystem::file_size(path, ec));
    meta.format_id = FormatDetector::detect_format(path);
    meta.mime_type = FormatDetector::detect_mime(path);

    auto header = read_header(path, 4096);
    if (header.empty()) {
        return meta;
    }

    const uint8_t* data = header.data();
    size_t size = header.size();

    // Parse PNG dimensions: width at byte 16 (big endian 4B), height at byte 20 (big endian 4B)
    if (meta.format_id == "png" && size >= 24) {
        meta.width = (data[16] << 24) | (data[17] << 16) | (data[18] << 8) | data[19];
        meta.height = (data[20] << 24) | (data[21] << 16) | (data[22] << 8) | data[23];
    }

    // Parse BMP dimensions: width at byte 18 (little endian 4B), height at byte 22 (little endian 4B)
    if (meta.format_id == "bmp" && size >= 26) {
        meta.width = data[18] | (data[19] << 8) | (data[20] << 16) | (data[21] << 24);
        meta.height = data[22] | (data[23] << 8) | (data[24] << 16) | (data[25] << 24);
    }

    // Parse WAV audio header: channels at byte 22 (2B LE), sample rate at byte 24 (4B LE)
    if (meta.format_id == "wav" && size >= 36) {
        meta.channels = data[22] | (data[23] << 8);
        meta.sample_rate = data[24] | (data[25] << 8) | (data[26] << 16) | (data[27] << 24);
        int bytes_per_sec = data[28] | (data[29] << 8) | (data[30] << 16) | (data[31] << 24);
        if (bytes_per_sec > 0 && meta.file_size_bytes > 44) {
            meta.duration_seconds = static_cast<double>(meta.file_size_bytes - 44) / static_cast<double>(bytes_per_sec);
        }
    }

    // Parse PDF page count hint if present in header/trailer
    if (meta.format_id == "pdf") {
        std::string content(reinterpret_cast<const char*>(data), size);
        auto pos = content.find("/Count ");
        if (pos != std::string::npos) {
            int count = 0;
            if (sscanf(content.c_str() + pos + 7, "%d", &count) == 1 && count > 0) {
                meta.page_count = count;
            }
        }
        if (!meta.page_count.has_value()) {
            meta.page_count = 1; // Default
        }
    }

    return meta;
}

} // namespace colossal
