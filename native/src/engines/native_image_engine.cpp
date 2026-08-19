#include "colossal/image_engine.hpp"
#include "colossal/error.hpp"

#include <cmath>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace colossal {

struct RawImage {
    int width{0};
    int height{0};
    int channels{3}; // 3 = RGB, 4 = RGBA
    std::vector<uint8_t> pixels; // Row-major, top-to-bottom
};

// BMP Reader (24-bit / 32-bit uncompressed)
static RawImage read_bmp(const std::filesystem::path& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        throw Error(ErrorCode::ExecutionFailed, "Failed to open input BMP file: " + path.string());
    }

    uint8_t header[54];
    file.read(reinterpret_cast<char*>(header), 54);
    if (file.gcount() < 54 || header[0] != 'B' || header[1] != 'M') {
        throw Error(ErrorCode::ExecutionFailed, "Invalid BMP file header");
    }

    int width = header[18] | (header[19] << 8) | (header[20] << 16) | (header[21] << 24);
    int height = header[22] | (header[23] << 8) | (header[24] << 16) | (header[25] << 24);
    int bpp = header[28] | (header[29] << 8);
    int data_offset = header[10] | (header[11] << 8) | (header[12] << 16) | (header[13] << 24);

    if (width <= 0 || height == 0 || (bpp != 24 && bpp != 32)) {
        throw Error(ErrorCode::UnsupportedFormat, "Unsupported BMP bit depth or dimensions");
    }

    bool flip_vertically = (height > 0);
    int abs_height = std::abs(height);

    file.seekg(data_offset, std::ios::beg);
    int row_padded = (width * (bpp / 8) + 3) & (~3);
    std::vector<uint8_t> row_buffer(row_padded);

    RawImage img;
    img.width = width;
    img.height = abs_height;
    img.channels = 3;
    img.pixels.resize(width * abs_height * 3);

    for (int y = 0; y < abs_height; ++y) {
        file.read(reinterpret_cast<char*>(row_buffer.data()), row_padded);
        int target_y = flip_vertically ? (abs_height - 1 - y) : y;
        for (int x = 0; x < width; ++x) {
            int src_idx = x * (bpp / 8);
            int dst_idx = (target_y * width + x) * 3;
            // BMP is BGR(A)
            img.pixels[dst_idx + 0] = row_buffer[src_idx + 2]; // R
            img.pixels[dst_idx + 1] = row_buffer[src_idx + 1]; // G
            img.pixels[dst_idx + 2] = row_buffer[src_idx + 0]; // B
        }
    }

    return img;
}

// PPM Reader (P6 binary)
static RawImage read_ppm(const std::filesystem::path& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        throw Error(ErrorCode::ExecutionFailed, "Failed to open input PPM file: " + path.string());
    }

    std::string magic;
    file >> magic;
    if (magic != "P6") {
        throw Error(ErrorCode::UnsupportedFormat, "Only binary P6 PPM is supported by native image reader");
    }

    auto skip_comments = [&file]() {
        while (file >> std::ws && file.peek() == '#') {
            std::string comment;
            std::getline(file, comment);
        }
    };

    skip_comments();
    int width = 0, height = 0, max_val = 0;
    file >> width;
    skip_comments();
    file >> height;
    skip_comments();
    file >> max_val;
    file.get(); // consume single trailing whitespace byte

    if (width <= 0 || height <= 0 || max_val <= 0 || max_val > 255) {
        throw Error(ErrorCode::UnsupportedFormat, "Invalid PPM dimensions or maxval");
    }

    RawImage img;
    img.width = width;
    img.height = height;
    img.channels = 3;
    img.pixels.resize(width * height * 3);

    file.read(reinterpret_cast<char*>(img.pixels.data()), width * height * 3);
    if (file.gcount() < static_cast<std::streamsize>(width * height * 3)) {
        throw Error(ErrorCode::ExecutionFailed, "Unexpected EOF reading PPM image data");
    }
    return img;
}

// BMP Writer (24-bit RGB)
static void write_bmp(const std::filesystem::path& path, const RawImage& img) {
    std::ofstream file(path, std::ios::binary);
    if (!file.is_open()) {
        throw Error(ErrorCode::OutputFailure, "Failed to create output BMP file: " + path.string());
    }

    int row_padded = (img.width * 3 + 3) & (~3);
    int image_size = row_padded * img.height;
    int file_size = 54 + image_size;

    uint8_t header[54] = {0};
    header[0] = 'B'; header[1] = 'M';
    header[2] = static_cast<uint8_t>(file_size);
    header[3] = static_cast<uint8_t>(file_size >> 8);
    header[4] = static_cast<uint8_t>(file_size >> 16);
    header[5] = static_cast<uint8_t>(file_size >> 24);
    header[10] = 54; // Data offset

    header[14] = 40; // DIB header size
    header[18] = static_cast<uint8_t>(img.width);
    header[19] = static_cast<uint8_t>(img.width >> 8);
    header[20] = static_cast<uint8_t>(img.width >> 16);
    header[21] = static_cast<uint8_t>(img.width >> 24);

    header[22] = static_cast<uint8_t>(img.height);
    header[23] = static_cast<uint8_t>(img.height >> 8);
    header[24] = static_cast<uint8_t>(img.height >> 16);
    header[25] = static_cast<uint8_t>(img.height >> 24);

    header[26] = 1; // Color planes
    header[28] = 24; // Bits per pixel
    header[34] = static_cast<uint8_t>(image_size);
    header[35] = static_cast<uint8_t>(image_size >> 8);
    header[36] = static_cast<uint8_t>(image_size >> 16);
    header[37] = static_cast<uint8_t>(image_size >> 24);

    file.write(reinterpret_cast<const char*>(header), 54);

    std::vector<uint8_t> row_buffer(row_padded, 0);
    for (int y = img.height - 1; y >= 0; --y) {
        for (int x = 0; x < img.width; ++x) {
            int src_idx = (y * img.width + x) * img.channels;
            int dst_idx = x * 3;
            // Write BGR
            row_buffer[dst_idx + 0] = img.pixels[src_idx + 2]; // B
            row_buffer[dst_idx + 1] = img.pixels[src_idx + 1]; // G
            row_buffer[dst_idx + 2] = img.pixels[src_idx + 0]; // R
        }
        file.write(reinterpret_cast<const char*>(row_buffer.data()), row_padded);
    }
}

// PPM (P6 binary) Writer
static void write_ppm(const std::filesystem::path& path, const RawImage& img) {
    std::ofstream file(path, std::ios::binary);
    if (!file.is_open()) {
        throw Error(ErrorCode::OutputFailure, "Failed to create output PPM file: " + path.string());
    }

    std::string header = "P6\n" + std::to_string(img.width) + " " + std::to_string(img.height) + "\n255\n";
    file.write(header.data(), static_cast<std::streamsize>(header.size()));

    if (img.channels == 3) {
        file.write(reinterpret_cast<const char*>(img.pixels.data()), static_cast<std::streamsize>(img.pixels.size()));
    } else {
        // Strip alpha
        std::vector<uint8_t> rgb(img.width * img.height * 3);
        for (int i = 0; i < img.width * img.height; ++i) {
            rgb[i * 3 + 0] = img.pixels[i * img.channels + 0];
            rgb[i * 3 + 1] = img.pixels[i * img.channels + 1];
            rgb[i * 3 + 2] = img.pixels[i * img.channels + 2];
        }
        file.write(reinterpret_cast<const char*>(rgb.data()), static_cast<std::streamsize>(rgb.size()));
    }
}

// TGA Writer (Uncompressed 24-bit TrueColor)
static void write_tga(const std::filesystem::path& path, const RawImage& img) {
    std::ofstream file(path, std::ios::binary);
    if (!file.is_open()) {
        throw Error(ErrorCode::OutputFailure, "Failed to create output TGA file: " + path.string());
    }

    uint8_t header[18] = {0};
    header[2] = 2; // Uncompressed TrueColor
    header[12] = static_cast<uint8_t>(img.width);
    header[13] = static_cast<uint8_t>(img.width >> 8);
    header[14] = static_cast<uint8_t>(img.height);
    header[15] = static_cast<uint8_t>(img.height >> 8);
    header[16] = 24; // 24 bpp
    header[17] = 0x20; // Origin top-left

    file.write(reinterpret_cast<const char*>(header), 18);

    std::vector<uint8_t> bgr(img.width * img.height * 3);
    for (int i = 0; i < img.width * img.height; ++i) {
        bgr[i * 3 + 0] = img.pixels[i * img.channels + 2]; // B
        bgr[i * 3 + 1] = img.pixels[i * img.channels + 1]; // G
        bgr[i * 3 + 2] = img.pixels[i * img.channels + 0]; // R
    }
    file.write(reinterpret_cast<const char*>(bgr.data()), static_cast<std::streamsize>(bgr.size()));
}

// Simple nearest-neighbor resizer
static RawImage resize_image(const RawImage& src, int target_w, int target_h) {
    if (target_w <= 0 || target_h <= 0 || (target_w == src.width && target_h == src.height)) {
        return src;
    }
    RawImage dst;
    dst.width = target_w;
    dst.height = target_h;
    dst.channels = src.channels;
    dst.pixels.resize(target_w * target_h * src.channels);

    double x_ratio = static_cast<double>(src.width) / static_cast<double>(target_w);
    double y_ratio = static_cast<double>(src.height) / static_cast<double>(target_h);

    for (int y = 0; y < target_h; ++y) {
        int src_y = static_cast<int>(std::floor(y * y_ratio));
        if (src_y >= src.height) src_y = src.height - 1;
        for (int x = 0; x < target_w; ++x) {
            int src_x = static_cast<int>(std::floor(x * x_ratio));
            if (src_x >= src.width) src_x = src.width - 1;

            int src_idx = (src_y * src.width + src_x) * src.channels;
            int dst_idx = (y * target_w + x) * src.channels;

            for (int c = 0; c < src.channels; ++c) {
                dst.pixels[dst_idx + c] = src.pixels[src_idx + c];
            }
        }
    }
    return dst;
}

std::vector<Artifact> NativeImageEngine::execute(const ExecutionContext& ctx) {
    const auto& primary = ctx.primary_input();
    const auto& src = primary.path;
    const auto& dst = ctx.destination_path;
    const auto& to_fmt = ctx.output_format_id;

    std::error_code ec;
    std::filesystem::create_directories(dst.parent_path(), ec);

    // Read input image
    RawImage img;
    auto in_fmt = primary.format_id;
    if (in_fmt == "ppm" || src.extension() == ".ppm") {
        img = read_ppm(src);
    } else if (in_fmt == "bmp" || src.extension() == ".bmp") {
        img = read_bmp(src);
    } else {
        img = read_bmp(src);
    }

    // Check resize option
    auto it_resize = ctx.options.find("resize");
    if (it_resize != ctx.options.end()) {
        int w = 0, h = 0;
        if (sscanf(it_resize->second.c_str(), "%dx%d", &w, &h) == 2 && w > 0 && h > 0) {
            img = resize_image(img, w, h);
        }
    }

    if (ctx.progress_callback) {
        ctx.progress_callback(0.6);
    }

    // Encode to target format
    if (to_fmt == "bmp") {
        write_bmp(dst, img);
    } else if (to_fmt == "ppm") {
        write_ppm(dst, img);
    } else if (to_fmt == "tga") {
        write_tga(dst, img);
    } else {
        write_bmp(dst, img);
    }

    if (ctx.progress_callback) {
        ctx.progress_callback(1.0);
    }

    auto art = verify_single_output(dst, to_fmt, ctx.stage_index);
    return {art};
}

std::shared_ptr<BaseEngine> create_native_image_engine() {
    return std::make_shared<NativeImageEngine>();
}

} // namespace colossal
