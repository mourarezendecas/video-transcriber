"""Ponto de entrada: extrai áudio de vídeos em input/, transcreve e (opcionalmente)
revisa o texto com a DeepSeek. Resultado salvo em output/.

Uso:
    python main.py
    python main.py --model small --no-refine
    python main.py --language en
"""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from transcriber.audio_extractor import extract_audio
from transcriber.transcribe import transcribe_audio
from transcriber.refine import refine_transcript

INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"
VIDEO_EXTENSIONS = {".mp4"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcreve vídeos da pasta input/")
    parser.add_argument(
        "--model",
        default="medium",
        help="Tamanho do modelo Whisper: tiny, base, small, medium, large-v3 (padrão: medium)",
    )
    parser.add_argument(
        "--language",
        default="pt",
        help="Código do idioma do áudio (padrão: pt). Use 'auto' para detecção automática.",
    )
    parser.add_argument(
        "--no-refine",
        action="store_true",
        help="Pula a etapa de revisão do texto.",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "deepseek"],
        default="openai",
        help="Provedor usado para revisar o texto (padrão: openai).",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    language = None if args.language == "auto" else args.language

    videos = sorted(
        p for p in INPUT_DIR.iterdir() if p.suffix.lower() in VIDEO_EXTENSIONS
    )
    if not videos:
        print(f"Nenhum arquivo .mp4 encontrado em {INPUT_DIR}")
        return

    fazer_refino = not args.no_refine
    env_key = f"{args.provider.upper()}_API_KEY"
    api_key = os.getenv(env_key)
    if fazer_refino and not api_key:
        print(
            f"Aviso: {env_key} não encontrada no .env. "
            "A etapa de revisão será pulada."
        )
        fazer_refino = False

    for video_path in videos:
        print(f"\n=== Processando {video_path.name} ===")

        print("Extraindo áudio...")
        audio_path = extract_audio(video_path, OUTPUT_DIR)

        print(f"Transcrevendo com Whisper ({args.model})...")
        texto_bruto = transcribe_audio(audio_path, model_size=args.model, language=language)

        bruto_path = OUTPUT_DIR / f"{video_path.stem}.txt"
        bruto_path.write_text(texto_bruto, encoding="utf-8")
        print(f"Transcrição salva em {bruto_path}")

        if fazer_refino:
            print(f"Revisando texto com {args.provider}...")
            texto_revisado = refine_transcript(texto_bruto, api_key, provider=args.provider)
            revisado_path = OUTPUT_DIR / f"{video_path.stem}_revisado.txt"
            revisado_path.write_text(texto_revisado, encoding="utf-8")
            print(f"Texto revisado salvo em {revisado_path}")


if __name__ == "__main__":
    main()
