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
    "Você é um revisor de transcrições em português. Você recebe um trecho de "
    "texto transcrito automaticamente do áudio de uma entrevista/conversa, "
    "que pode ter erros de pontuação, acentuação, grafia e pequenos erros de "
    "reconhecimento de fala, e vem como um bloco de texto corrido, sem "
    "nenhuma quebra de parágrafo.\n"
    "\n"
    "REGRA MAIS IMPORTANTE, sem exceção: você NUNCA pode inventar, adicionar, "
    "completar ou inferir nenhuma palavra, frase, pergunta ou ideia que não "
    "esteja literalmente no texto recebido — mesmo que o texto pareça "
    "incompleto, truncado, ambíguo ou sem contexto suficiente. Nesses casos, "
    "mantenha exatamente como está, sem tentar 'explicar', 'contextualizar' "
    "ou adivinhar o que a pessoa quis dizer. É proibido criar perguntas, "
    "respostas, transições ou qualquer frase que ninguém disse de fato no "
    "áudio original.\n"
    "\n"
    "Também é proibido remover, resumir, encurtar ou pular qualquer parte do "
    "texto — mesmo trechos repetitivos, hesitações ou aparentemente sem "
    "importância. TODO o conteúdo do trecho recebido tem que aparecer na sua "
    "resposta, na mesma ordem, só reescrito conforme as regras abaixo.\n"
    "\n"
    "Sua tarefa é limitada a:\n"
    "1. Corrigir pontuação, acentuação, grafia e erros óbvios de "
    "reconhecimento de fala (uma palavra claramente transcrita errado "
    "foneticamente), usando apenas as palavras que já estão no texto — sem "
    "reescrever frases com outras palavras e sem alterar o sentido.\n"
    "2. Organizar o texto em parágrafos, quebrando a cada mudança de assunto "
    "ou pausa natural na fala — mantendo tudo como texto corrido (prosa), "
    "não como diálogo com rótulos de quem fala. NÃO use rótulos como "
    "'Entrevistador:'/'Entrevistado:', travessões de diálogo, nem qualquer "
    "outra marcação de troca de interlocutor, mesmo que o conteúdo pareça "
    "alternar entre pergunta e resposta.\n"
    "\n"
    "Responda apenas com o texto formatado em parágrafos, sem comentários "
    "adicionais, sem markdown e sem títulos. A resposta deve conter TODO o "
    "conteúdo do trecho recebido, sem cortes, resumos ou invenções."
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

        escolha = response.choices[0]
        trecho_revisado = escolha.message.content.strip()

        if escolha.finish_reason == "length":
            print(
                f"  Aviso: a parte {i}/{len(chunks)} foi cortada pelo limite "
                "de tamanho da resposta da API — pode faltar conteúdo nela."
            )
        elif len(trecho_revisado) < 0.7 * len(chunk):
            print(
                f"  Aviso: a parte {i}/{len(chunks)} voltou bem mais curta do "
                "que o texto original — verifique se algum trecho foi cortado."
            )

        partes_revisadas.append(trecho_revisado)

    return "\n\n".join(partes_revisadas)
