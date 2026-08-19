#include "colossal/audio_engine.hpp"
#include "colossal/error.hpp"

#include <cmath>
#include <cstring>
#include <fstream>
#include <vector>

namespace colossal {

struct PcmAudio {
    int num_channels{2};
    int sample_rate{44100};
    int bits_per_sample{16};
    std::vector<int16_t> samples; // Interleaved 16-bit PCM
};

static PcmAudio read_wav(const std::filesystem::path& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        throw Error(ErrorCode::ExecutionFailed, "Failed to open WAV audio file: " + path.string());
    }

    uint8_t header[44];
    file.read(reinterpret_cast<char*>(header), 44);
    if (file.gcount() < 44 || memcmp(header, "RIFF", 4) != 0 || memcmp(header + 8, "WAVE", 4) != 0) {
        throw Error(ErrorCode::ExecutionFailed, "Invalid WAV audio header");
    }

    int channels = header[22] | (header[23] << 8);
    int sample_rate = header[24] | (header[25] << 8) | (header[26] << 16) | (header[27] << 24);
    int bits_per_sample = header[34] | (header[35] << 8);
    int data_size = header[40] | (header[41] << 8) | (header[42] << 16) | (header[43] << 24);

    if (channels <= 0 || sample_rate <= 0 || bits_per_sample != 16) {
        throw Error(ErrorCode::UnsupportedFormat, "Unsupported WAV format: only 16-bit PCM is currently supported natively");
    }

    size_t sample_count = data_size / sizeof(int16_t);
    PcmAudio audio;
    audio.num_channels = channels;
    audio.sample_rate = sample_rate;
    audio.bits_per_sample = bits_per_sample;
    audio.samples.resize(sample_count);

    file.read(reinterpret_cast<char*>(audio.samples.data()), data_size);
    return audio;
}

static void write_wav(const std::filesystem::path& path, const PcmAudio& audio) {
    std::ofstream file(path, std::ios::binary);
    if (!file.is_open()) {
        throw Error(ErrorCode::OutputFailure, "Failed to create output WAV file: " + path.string());
    }

    int data_size = static_cast<int>(audio.samples.size() * sizeof(int16_t));
    int file_size = 36 + data_size;
    int byte_rate = audio.sample_rate * audio.num_channels * (audio.bits_per_sample / 8);
    int block_align = audio.num_channels * (audio.bits_per_sample / 8);

    uint8_t header[44] = {0};
    memcpy(header, "RIFF", 4);
    header[4] = static_cast<uint8_t>(file_size);
    header[5] = static_cast<uint8_t>(file_size >> 8);
    header[6] = static_cast<uint8_t>(file_size >> 16);
    header[7] = static_cast<uint8_t>(file_size >> 24);
    memcpy(header + 8, "WAVEfmt ", 8);

    header[16] = 16; // Subchunk1Size (16 for PCM)
    header[20] = 1;  // AudioFormat (1 = PCM)
    header[22] = static_cast<uint8_t>(audio.num_channels);
    header[23] = static_cast<uint8_t>(audio.num_channels >> 8);

    header[24] = static_cast<uint8_t>(audio.sample_rate);
    header[25] = static_cast<uint8_t>(audio.sample_rate >> 8);
    header[26] = static_cast<uint8_t>(audio.sample_rate >> 16);
    header[27] = static_cast<uint8_t>(audio.sample_rate >> 24);

    header[28] = static_cast<uint8_t>(byte_rate);
    header[29] = static_cast<uint8_t>(byte_rate >> 8);
    header[30] = static_cast<uint8_t>(byte_rate >> 16);
    header[31] = static_cast<uint8_t>(byte_rate >> 24);

    header[32] = static_cast<uint8_t>(block_align);
    header[33] = static_cast<uint8_t>(block_align >> 8);

    header[34] = static_cast<uint8_t>(audio.bits_per_sample);
    header[35] = static_cast<uint8_t>(audio.bits_per_sample >> 8);

    memcpy(header + 36, "data", 4);
    header[40] = static_cast<uint8_t>(data_size);
    header[41] = static_cast<uint8_t>(data_size >> 8);
    header[42] = static_cast<uint8_t>(data_size >> 16);
    header[43] = static_cast<uint8_t>(data_size >> 24);

    file.write(reinterpret_cast<const char*>(header), 44);
    file.write(reinterpret_cast<const char*>(audio.samples.data()), data_size);
}

std::vector<Artifact> NativeAudioEngine::execute(const ExecutionContext& ctx) {
    const auto& primary = ctx.primary_input();
    const auto& src = primary.path;
    const auto& dst = ctx.destination_path;
    const auto& to_fmt = ctx.output_format_id;

    std::error_code ec;
    std::filesystem::create_directories(dst.parent_path(), ec);

    PcmAudio audio = read_wav(src);

    // Channel modification (e.g. stereo to mono or mono to stereo)
    auto it_ch = ctx.options.find("channels");
    if (it_ch != ctx.options.end()) {
        int target_ch = std::atoi(it_ch->second.c_str());
        if (target_ch == 1 && audio.num_channels == 2) {
            // Downmix stereo to mono
            std::vector<int16_t> mono(audio.samples.size() / 2);
            for (size_t i = 0; i < mono.size(); ++i) {
                mono[i] = static_cast<int16_t>((static_cast<int>(audio.samples[i * 2]) + static_cast<int>(audio.samples[i * 2 + 1])) / 2);
            }
            audio.samples = std::move(mono);
            audio.num_channels = 1;
        } else if (target_ch == 2 && audio.num_channels == 1) {
            // Upmix mono to stereo
            std::vector<int16_t> stereo(audio.samples.size() * 2);
            for (size_t i = 0; i < audio.samples.size(); ++i) {
                stereo[i * 2 + 0] = audio.samples[i];
                stereo[i * 2 + 1] = audio.samples[i];
            }
            audio.samples = std::move(stereo);
            audio.num_channels = 2;
        }
    }

    if (ctx.progress_callback) {
        ctx.progress_callback(0.7);
    }

    write_wav(dst, audio);

    if (ctx.progress_callback) {
        ctx.progress_callback(1.0);
    }

    auto art = verify_single_output(dst, to_fmt, ctx.stage_index);
    return {art};
}

std::shared_ptr<BaseEngine> create_native_audio_engine() {
    return std::make_shared<NativeAudioEngine>();
}

} // namespace colossal
