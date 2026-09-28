"""Validação de chaves de API (OpenAI/DeepSeek) via uma chamada mínima e real à API.

Diferente de só checar se o campo está preenchido, isso confirma que a chave
realmente funciona (autenticação aceita, sem bloqueio de saldo/permissão).
"""

from openai import (
    APIConnectionError,
    AuthenticationError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from transcriber.refine import PROVIDERS


def validar_api_key(api_key: str, provider: str) -> tuple[bool, str]:
    """Testa se uma chave de API é válida.

    Faz uma chamada de chat mínima (1 token de resposta) para confirmar que a
    chave é aceita pelo provedor. Retorna (valida, mensagem).
    """
    if provider not in PROVIDERS:
        return False, f"Provedor desconhecido: {provider!r}."

    api_key = (api_key or "").strip()
    if not api_key:
        return False, "Nenhuma chave informada."

    cfg = PROVIDERS[provider]
    client_kwargs = {"api_key": api_key, "timeout": 15.0}
    if cfg["base_url"]:
        client_kwargs["base_url"] = cfg["base_url"]
    client = OpenAI(**client_kwargs)

    try:
        client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": "oi"}],
            max_tokens=1,
        )
        return True, "Chave válida."
    except AuthenticationError:
        return False, "Chave inválida (autenticação recusada pelo provedor)."
    except PermissionDeniedError:
        return False, "Chave sem permissão para usar este modelo/conta."
    except RateLimitError:
        return False, "Chave aceita, mas sem saldo/limite disponível na conta."
    except APIConnectionError:
        return False, "Não foi possível conectar à API (verifique sua internet/VPN)."
    except Exception as exc:
        return False, f"Erro ao validar: {exc}"
