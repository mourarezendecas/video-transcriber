# video-transcriber

Extrai o áudio de vídeos `.mp4`, transcreve com Whisper (local, via
[faster-whisper](https://github.com/SYSTRAN/faster-whisper)) e, opcionalmente,
revisa o texto (pontuação, gramática, parágrafos) usando a API da OpenAI ou
da DeepSeek.

> OpenAI e DeepSeek aqui são modelos de texto — eles não fazem transcrição de
> áudio. Quem transcreve é o Whisper, rodando localmente na sua máquina. O
> modelo de texto entra só depois, para deixar o texto mais limpo e organizado
> em parágrafos.

## Requisitos

- Python 3.10 ou superior.
- Não é necessário instalar o ffmpeg manualmente: a biblioteca
  `imageio-ffmpeg` baixa um binário próprio automaticamente no primeiro uso,
  em qualquer sistema operacional.

## Setup

Clone o repositório e entre na pasta:

```bash
git clone https://github.com/mourarezendecas/video-transcriber.git
cd video-transcriber
```

### Ambiente virtual

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Se o PowerShell bloquear a ativação por política de execução de scripts,
rode uma vez (e confirme com `Y`): `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**Windows (cmd.exe)**

```bat
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
```

Em todos os casos, quando o ambiente estiver ativo o prompt mostra `(.venv)`
no início da linha. Para desativar, rode `deactivate`.

### Chave de API

Edite o `.env` e coloque sua chave de API (opcional, só necessário se você
quiser a etapa de revisão do texto):

```
OPENAI_API_KEY=sua_chave_aqui
DEEPSEEK_API_KEY=sua_chave_aqui
```

Só precisa configurar a chave do provedor que for usar (o padrão é OpenAI).
**Nunca commite o arquivo `.env`** — ele já está no `.gitignore`.

## Uso

1. Coloque um ou mais arquivos `.mp4` na pasta `input/`.
2. Rode:

```bash
python main.py
```

3. Os resultados aparecem em `output/`:
   - `<nome>.wav` — áudio extraído
   - `<nome>.txt` — transcrição bruta do Whisper
   - `<nome>_revisado.txt` — versão revisada e formatada em parágrafos pelo modelo de texto (se configurada)

### Opções

```bash
python main.py --model small          # modelo menor e mais rápido (tiny, base, small, medium, large-v3)
python main.py --language en          # idioma do áudio (padrão: pt)
python main.py --language auto        # detecção automática de idioma
python main.py --no-refine            # pula a revisão por LLM
python main.py --provider deepseek    # usa a DeepSeek em vez da OpenAI para revisar
```

Na primeira execução, o `faster-whisper` baixa o modelo escolhido (alguns
GBs para `medium`/`large`) e o `imageio-ffmpeg` baixa um binário do ffmpeg —
ambos ficam em cache local (fora do repositório) para as próximas execuções.

### Revisar um .txt já transcrito

Se a transcrição já rodou e você só quer (re)fazer a revisão por LLM, sem
rodar o Whisper de novo:

```bash
python refine_only.py "output/meu_video.txt"
python refine_only.py                     # revisa todos os .txt pendentes em output/
python refine_only.py --provider deepseek # usa a DeepSeek em vez da OpenAI
```

## Estrutura do projeto

```
video-transcriber/
├── input/              # coloque os .mp4 aqui (ignorado pelo git)
├── output/              # .wav, .txt e _revisado.txt saem aqui (ignorado pelo git)
├── transcriber/
│   ├── audio_extractor.py   # extrai áudio com ffmpeg (via imageio-ffmpeg)
│   ├── transcribe.py        # transcreve com faster-whisper, localmente
│   └── refine.py            # revisa/formata o texto via OpenAI ou DeepSeek
├── main.py               # pipeline completo: vídeo → áudio → transcrição → revisão
├── refine_only.py         # roda só a revisão em um .txt já existente
├── requirements.txt
└── .env.example
```

## Privacidade

Os vídeos (`input/`), áudios extraídos e transcrições (`output/`) ficam só na
sua máquina e nunca são commitados — ambas as pastas estão no `.gitignore`.
A única informação enviada para fora é o texto da transcrição, e só na etapa
de revisão (para a API da OpenAI ou DeepSeek, conforme o provedor escolhido).
