import os
import time
import shutil
import subprocess

from processed_file_data import ProcessedFileData

_CACHED_ENCODER = None
_CACHED_ENCODER_NAME = None


def detect_best_video_encoder():
    """
    Detects the best available hardware GPU encoder supported by the system's FFmpeg,
    falling back to standard CPU encoding (libx264) if no GPU encoder is supported.
    """
    global _CACHED_ENCODER, _CACHED_ENCODER_NAME
    if _CACHED_ENCODER is not None:
        return _CACHED_ENCODER, _CACHED_ENCODER_NAME

    # Candidates in order of hardware preference
    candidates = [
        ("h264_nvenc", "NVIDIA NVENC (GPU)"),
        ("h264_qsv", "Intel Quick Sync (GPU)"),
        ("h264_amf", "AMD AMF (GPU)"),
        ("h264_mf", "MediaFoundation (Hardware)"),
        ("libx264", "Software CPU (libx264)")
    ]

    for encoder, display_name in candidates:
        test_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "nullsrc=s=64x64:d=0.05",
            "-c:v", encoder,
            "-f", "null", "-"
        ]
        try:
            res = subprocess.run(test_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                _CACHED_ENCODER = encoder
                _CACHED_ENCODER_NAME = display_name
                return _CACHED_ENCODER, _CACHED_ENCODER_NAME
        except Exception:
            continue

    _CACHED_ENCODER = "libx264"
    _CACHED_ENCODER_NAME = "Software CPU (libx264)"
    return _CACHED_ENCODER, _CACHED_ENCODER_NAME


def get_encoder_flags(encoder):
    """Returns the optimal quality and rate-control flags for the selected encoder."""
    if encoder == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-cq", "28", "-preset", "p4", "-pix_fmt", "yuv420p"]
    elif encoder == "h264_qsv":
        return ["-c:v", "h264_qsv", "-global_quality", "28", "-preset", "medium", "-pix_fmt", "nv12"]
    elif encoder == "h264_amf":
        return ["-c:v", "h264_amf", "-rc", "cqp", "-qp_p", "28", "-pix_fmt", "yuv420p"]
    elif encoder == "h264_mf":
        return ["-c:v", "h264_mf", "-ratecontrol", "0", "-quality", "70", "-pix_fmt", "yuv420p"]
    else:
        # Default CPU x264
        return ["-c:v", "libx264", "-crf", "26", "-preset", "medium", "-pix_fmt", "yuv420p"]


def compress_video(input_path, output_path, start_spacing):
    """
    Compresses a video file using FFmpeg with automatic GPU acceleration.
    Falls back to CPU encoding if GPU encoding encounters an issue.
    Returns ProcessedFileData containing duration, sizes, and status.
    """
    start = time.time()
    encoder, encoder_name = detect_best_video_encoder()
    original_size = round(os.path.getsize(input_path) / 1024, 2) if os.path.exists(input_path) else 0

    encoder_args = get_encoder_flags(encoder)

    # Base FFmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        *encoder_args,
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, Exception) as e:
        # If GPU encoding failed, attempt fallback to CPU libx264
        if encoder != "libx264":
            fallback_args = get_encoder_flags("libx264")
            fallback_cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                *fallback_args,
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                output_path
            ]
            try:
                subprocess.run(fallback_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as cpu_err:
                return ProcessedFileData(
                    file_name=os.path.basename(output_path),
                    original_size=original_size,
                    compressed_size=0,
                    compression_duration=time.time() - start,
                    compression_success=False,
                    error_message=cpu_err,
                    start_spacing=start_spacing + "  "
                )
        else:
            return ProcessedFileData(
                file_name=os.path.basename(output_path),
                original_size=original_size,
                compressed_size=0,
                compression_duration=time.time() - start,
                compression_success=False,
                error_message=e,
                start_spacing=start_spacing + "  "
            )

    compressed_size = round(os.path.getsize(output_path) / 1024, 2) if os.path.exists(output_path) else 0

    # Safety check: if compression did not reduce the file size, retain the original
    if compressed_size > original_size and original_size > 0:
        shutil.copy2(input_path, output_path)
        compressed_size = original_size

    return ProcessedFileData(
        file_name=os.path.basename(output_path),
        original_size=original_size,
        compressed_size=compressed_size,
        compression_duration=time.time() - start,
        compression_success=True,
        start_spacing=start_spacing + "  "
    )
