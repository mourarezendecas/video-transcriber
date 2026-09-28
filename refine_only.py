"""Roda só a etapa de revisão pela DeepSeek em um .txt já transcrito,
sem precisar rodar o Whisper de novo.

Uso:
    python refine_only.py "output\\meu_video.txt"
    python refine_only.py            # revisa todos os .txt em output/ que ainda não têm _revisado
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from transcriber.refine import refine_transcript

OUTPUT_DIR = Path(__file__).parent / "output"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Revisa uma transcrição existente com a DeepSeek")
    parser.add_argument(
        "arquivo",
        nargs="?",
        default=None,
        help="Caminho do .txt a revisar. Se omitido, revisa todos os .txt pendentes em output/.",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "deepseek"],
        default="openai",
        help="Provedor usado para revisar o texto (padrão: openai).",
    )
    return parser.parse_args()


def encontrar_pendentes() -> list[Path]:
    pendentes = []
    for txt_path in sorted(OUTPUT_DIR.glob("*.txt")):
        if txt_path.stem.endswith("_revisado"):
            continue
        revisado_path = OUTPUT_DIR / f"{txt_path.stem}_revisado.txt"
        if not revisado_path.exists():
            pendentes.append(txt_path)
    return pendentes


def main() -> None:
    load_dotenv()
    args = parse_args()

    env_key = f"{args.provider.upper()}_API_KEY"
    api_key = os.getenv(env_key)
    if not api_key:
        print(f"Erro: {env_key} não encontrada no .env")
        sys.exit(1)

    if args.arquivo:
        arquivos = [Path(args.arquivo)]
    else:
        arquivos = encontrar_pendentes()
        if not arquivos:
            print("Nenhum .txt pendente de revisão encontrado em output/")
            return

    for bruto_path in arquivos:
        if not bruto_path.exists():
            print(f"Arquivo não encontrado: {bruto_path}")
            continue

        print(f"\n=== Revisando {bruto_path.name} ===")
        texto_bruto = bruto_path.read_text(encoding="utf-8")

        texto_revisado = refine_transcript(texto_bruto, api_key, provider=args.provider)

        revisado_path = bruto_path.parent / f"{bruto_path.stem}_revisado.txt"
        revisado_path.write_text(texto_revisado, encoding="utf-8")
        print(f"Texto revisado salvo em {revisado_path}")


if __name__ == "__main__":
    main()
