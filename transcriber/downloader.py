"""Download de um vídeo a partir de uma URL (ex.: Google Drive) para a pasta input/."""

from pathlib import Path

import gdown
import requests


def _is_google_drive_url(url: str) -> bool:
    return "drive.google.com" in url or "docs.google.com" in url


def download_video(url: str, dest_dir: Path) -> Path:
    """Baixa um vídeo de uma URL para dest_dir e retorna o caminho local do arquivo.

    Suporta links de compartilhamento do Google Drive (ex.:
    https://drive.google.com/file/d/<id>/view) e URLs diretas de download de
    outros servidores.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    if _is_google_drive_url(url):
        destino_str = gdown.download(url=url, output=f"{dest_dir}/", quiet=False, fuzzy=True)
        if not destino_str:
            raise RuntimeError(
                f"Falha ao baixar do Google Drive: {url}\n"
                "Verifique se o link está compartilhado como "
                "'Qualquer pessoa com o link' pode visualizar."
            )
        destino = Path(destino_str)
    else:
        destino = _download_http(url, dest_dir)

    if not destino.exists() or destino.stat().st_size < 10_000:
        raise RuntimeError(
            f"O arquivo baixado parece inválido ou incompleto ({destino}). "
            "Verifique se a URL é pública e aponta diretamente para um arquivo de vídeo."
        )

    return destino


def _download_http(url: str, dest_dir: Path) -> Path:
    nome_arquivo = url.split("?")[0].rstrip("/").split("/")[-1] or "video_baixado.mp4"
    if not nome_arquivo.lower().endswith((".mp4", ".mov", ".mkv", ".avi", ".webm")):
        nome_arquivo += ".mp4"

    destino = dest_dir / nome_arquivo

    with requests.get(url, stream=True, timeout=60) as resposta:
        resposta.raise_for_status()
        with open(destino, "wb") as arquivo:
            for chunk in resposta.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    arquivo.write(chunk)

    return destino
