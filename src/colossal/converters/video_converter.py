from pathlib import Path
import shutil
import subprocess
from typing import Optional, Dict, Any

from colossal.core.base_converter import BaseConverter
from colossal.models.conversion_task import ConversionTask


def _report(cb, task, value: float):
    try:
        task.progress = float(value)
        if cb:
            cb(float(value))
    except (AttributeError, TypeError, ValueError):
        pass


def _ensure_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required tool '{name}' not found in PATH. Install {name}.")
    return path


class FFmpegVideoConverter(BaseConverter):
    category = "video"
    options_schema = {
        "preset": {"type": "string", "default": None},
        "resolution": {"type": "string", "default": None},
        "video_codec": {"type": "string", "default": None},
        "audio_codec": {"type": "string", "default": None},
        "bitrate": {"type": "string", "default": None}
    }

    default_preset: Optional[str] = None

    PRESETS: Dict[str, Dict[str, Any]] = {
        "mobile": {"resolution": "1280x720", "video_codec": "h264", "audio_codec": "aac", "bitrate": "2M"},
        "desktop": {"resolution": "1920x1080", "video_codec": "h264", "audio_codec": "aac", "bitrate": "5M"},
        "archive": {"resolution": "source", "video_codec": "hevc", "audio_codec": "aac", "bitrate": "auto"},
        "web": {"resolution": "1920x1080", "video_codec": "vp9", "audio_codec": "opus", "bitrate": "auto"}
    }

    @classmethod
    def _build_cmd(cls, src: Path, dst: Path, task: ConversionTask) -> list:
        ffmpeg = _ensure_tool("ffmpeg")
        cmd = [ffmpeg, '-y', '-i', str(src)]

        opts = task.options or {}
        preset = opts.get('preset') or cls.default_preset
        settings = cls.PRESETS.get(preset, {}) if preset else {}

        resolution = opts.get('resolution') or settings.get('resolution')
        vcodec = opts.get('video_codec') or settings.get('video_codec')
        acodec = opts.get('audio_codec') or settings.get('audio_codec')
        bitrate = opts.get('bitrate') or settings.get('bitrate')

        # Resolution
        if resolution and resolution != 'source':
            cmd += ['-s', resolution]

        # Video codec
        if vcodec:
            cmd += ['-c:v', vcodec]

        # Audio codec
        if acodec:
            cmd += ['-c:a', acodec]

        # Bitrate
        if bitrate and bitrate != 'auto':
            cmd += ['-b:v', bitrate]

        # Output file
        cmd += [str(dst)]
        return cmd

    @classmethod
    def factory(cls, task: ConversionTask, report_progress=None):
        _report(report_progress, task, 0.0)

        src = Path(task.input_path)
        dst = Path(task.output_path)
        dst.parent.mkdir(parents=True, exist_ok=True)

        cmd = cls._build_cmd(src, dst, task)

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except OSError as e:
            raise RuntimeError(f"Failed to execute ffmpeg: {e}") from e

        if res.returncode != 0:
            stderr = res.stderr or ''
            raise RuntimeError(f"ffmpeg failed: {stderr}")

        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask):
        return self.factory(task, None)


# Concrete converters based on video.json
class ToMP4(FFmpegVideoConverter):
    id = 'video-to-mp4'
    name = 'Video to MP4'
    category = 'video'
    input_formats = ['mp4', 'mov', 'avi', 'mkv', 'flv', 'wmv']
    output_formats = ['mp4']
    default_preset = 'desktop'


class ToMKV(FFmpegVideoConverter):
    id = 'video-to-mkv'
    name = 'Video to MKV'
    category = 'video'
    input_formats = ['mp4', 'mov', 'avi', 'flv', 'wmv']
    output_formats = ['mkv']
    default_preset = None


class ToWEBM(FFmpegVideoConverter):
    id = 'video-to-webm'
    name = 'Video to WEBM'
    category = 'video'
    input_formats = ['mp4', 'mkv', 'mov']
    output_formats = ['webm']
    default_preset = 'web'


class ToAVI(FFmpegVideoConverter):
    id = 'video-to-avi'
    name = 'Video to AVI'
    category = 'video'
    input_formats = ['mp4', 'mkv', 'mov']
    output_formats = ['avi']
    default_preset = 'archive'


class ToFLV(FFmpegVideoConverter):
    id = 'video-to-flv'
    name = 'Video to FLV'
    category = 'video'
    input_formats = ['mp4', 'mkv', 'mov']
    output_formats = ['flv']
    default_preset = 'archive'


class ToWMV(FFmpegVideoConverter):
    id = 'video-to-wmv'
    name = 'Video to WMV'
    category = 'video'
    input_formats = ['mp4', 'mkv', 'mov']
    output_formats = ['wmv']
    default_preset = 'archive'


__all__ = ['ToMP4', 'ToMKV', 'ToWEBM', 'ToAVI', 'ToFLV', 'ToWMV']

