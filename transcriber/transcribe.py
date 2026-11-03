"""Transcrição de áudio para texto usando faster-whisper (roda localmente)."""

import wave
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel


def _carregar_wav(audio_path: Path) -> np.ndarray:
    """Lê o .wav mono 16kHz gerado por extract_audio como float32 em [-1, 1].

    Passar o áudio já decodificado evita o decodificador interno do
    faster-whisper (PyAV), que quebra com versões novas do pacote `av`
    (TypeError: open() got an unexpected keyword argument 'metadata_errors').
    """
    with wave.open(str(audio_path), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getframerate() != 16000:
            raise ValueError(
                f"{audio_path.name} precisa ser um .wav mono, 16 bits, 16kHz (use extract_audio)."
            )
        frames = wav.readframes(wav.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe_audio(
    audio_path: Path,
    model_size: str = "medium",
    language: str | None = "pt",
    device: str = "cpu",
    compute_type: str = "int8",
) -> str:
    """Transcreve um arquivo de áudio e retorna o texto completo.

    model_size: tiny, base, small, medium, large-v3 (maior = mais preciso e mais lento).
    language: código do idioma (ex.: "pt"). Use None para detecção automática.
    audio_path deve ser o .wav gerado por extract_audio.
    """
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    segments, _info = model.transcribe(_carregar_wav(audio_path), language=language)

    texto = " ".join(segment.text.strip() for segment in segments)
    return texto.strip()
