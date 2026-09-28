"""Revisão do texto transcrito usando um modelo de texto (OpenAI ou DeepSeek).

O modelo de texto melhora pontuação, gramática e clareza do texto que o
Whisper já transcreveu — ele não faz reconhecimento de fala.
"""

from openai import OpenAI

# Tamanho máximo de caracteres por pedaço enviado à API, para textos longos.
CHUNK_SIZE = 8000

PROVIDERS = {
    "openai": {
        "base_url": None,  # usa o endpoint padrão da OpenAI
        "model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
}

SYSTEM_PROMPT = (
    "Você é um revisor de transcrições em português. Você recebe um texto "
    "transcrito automaticamente do áudio de uma entrevista/conversa, que pode "
    "ter erros de pontuação, acentuação, grafia e pequenos erros de "
    "reconhecimento de fala, e vem como um bloco de texto corrido, sem "
    "nenhuma quebra de parágrafo.\n"
    "\n"
    "Sua tarefa:\n"
    "1. Corrija pontuação, acentuação, grafia e pequenos erros de reconhecimento, "
    "mantendo o sentido original e o estilo de fala (não reescreva o discurso, "
    "não resuma e não adicione informações novas).\n"
    "2. Organize o texto em parágrafos, quebrando a cada mudança de assunto, "
    "ideia ou pausa natural na fala — mantendo tudo como texto corrido "
    "(prosa), não como diálogo com rótulos de quem fala. NÃO use rótulos como "
    "'Entrevistador:'/'Entrevistado:', travessões de diálogo, nem qualquer "
    "outra marcação de troca de interlocutor, mesmo que o conteúdo pareça "
    "alternar entre pergunta e resposta.\n"
    "\n"
    "Responda apenas com o texto formatado em parágrafos, sem comentários "
    "adicionais, sem markdown e sem títulos."
)


def _split_in_chunks(text: str, chunk_size: int) -> list[str]:
    palavras = text.split(" ")
    chunks: list[str] = []
    atual: list[str] = []
    tamanho = 0

    for palavra in palavras:
        tamanho += len(palavra) + 1
        if tamanho > chunk_size and atual:
            chunks.append(" ".join(atual))
            atual = []
            tamanho = len(palavra) + 1
        atual.append(palavra)

    if atual:
        chunks.append(" ".join(atual))

    return chunks


def refine_transcript(text: str, api_key: str, provider: str = "openai") -> str:
    """Envia o texto (em pedaços, se necessário) para o modelo revisar.

    provider: "openai" ou "deepseek".
    """
    if provider not in PROVIDERS:
        raise ValueError(f"Provider desconhecido: {provider!r}. Use 'openai' ou 'deepseek'.")

    cfg = PROVIDERS[provider]
    client_kwargs = {"api_key": api_key, "timeout": 90.0}
    if cfg["base_url"]:
        client_kwargs["base_url"] = cfg["base_url"]
    client = OpenAI(**client_kwargs)

    chunks = _split_in_chunks(text, CHUNK_SIZE)
    partes_revisadas = []

    for i, chunk in enumerate(chunks, start=1):
        print(f"  Revisando parte {i}/{len(chunks)}...")

        response = client.chat.completions.create(
            model=cfg["model"],
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": chunk},
            ],
            temperature=0.2,
        )

        if not response.choices:
            raise RuntimeError(
                f"Resposta inesperada da API ({provider}), sem 'choices'. "
                f"Resposta bruta: {response}"
            )

        partes_revisadas.append(response.choices[0].message.content.strip())

    return "\n\n".join(partes_revisadas)
