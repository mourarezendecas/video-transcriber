"""Extração de áudio de arquivos de vídeo usando ffmpeg."""

import subprocess
from pathlib import Path

import imageio_ffmpeg


def extract_audio(video_path: Path, output_dir: Path) -> Path:
    """Extrai o áudio de um vídeo para um .wav mono 16kHz (formato ideal pro Whisper).

    Usa o binário do ffmpeg baixado automaticamente pelo imageio-ffmpeg,
    então não é necessário ter o ffmpeg instalado no sistema.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / f"{video_path.stem}.wav"

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg_exe,
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Falha ao extrair áudio de {video_path.name}:\n{result.stderr}"
        )

    return audio_path
