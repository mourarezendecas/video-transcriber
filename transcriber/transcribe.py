"""Transcrição de áudio para texto usando faster-whisper (roda localmente)."""

from pathlib import Path

from faster_whisper import WhisperModel


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
    """
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    segments, _info = model.transcribe(str(audio_path), language=language)

    texto = " ".join(segment.text.strip() for segment in segments)
    return texto.strip()
