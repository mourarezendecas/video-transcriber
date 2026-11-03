# video-transcriber

Extrai o áudio de vídeos, transcreve com Whisper (local, via
[faster-whisper](https://github.com/SYSTRAN/faster-whisper)) e, opcionalmente,
revisa o texto (pontuação, gramática, parágrafos) usando a API da OpenAI ou
da DeepSeek. Tem uma interface gráfica simples para quem não é técnico, e um
modo de linha de comando para uso mais avançado.

> OpenAI e DeepSeek aqui são modelos de texto — eles não fazem transcrição de
> áudio. Quem transcreve é o Whisper, rodando localmente na sua máquina. O
> modelo de texto entra só depois, para deixar o texto mais limpo e organizado
> em parágrafos.

---

## Para quem só vai usar o programa (sem conhecimento técnico)

Isso aqui pressupõe que alguém já fez a "Configuração inicial" (mais abaixo)
nesse computador uma vez. Se a pasta `.venv` já existe dentro da pasta do
projeto, está tudo pronto.

### 1. Abrir o programa

Dentro da pasta `video-transcriber`, dê **duplo-clique em `iniciar.bat`**.
Uma janela chamada "Transcritor de Vídeos" vai abrir.

### 2. Configurar as chaves de API (só na primeira vez)

No topo da janela, cole sua chave da OpenAI e/ou da DeepSeek nos campos
correspondentes e clique em **"Salvar chaves"**. Isso só precisa ser feito
uma vez — as chaves ficam salvas no computador para as próximas vezes que
você abrir o programa. Você só precisa preencher a chave do serviço que for
usar (o padrão é OpenAI).

Ao lado de cada campo aparece um indicador validando a chave de verdade
(faz uma chamadinha real à API, não só confere se o campo está preenchido):
🟡 verificando... → 🟢 válida ou 🔴 inválida. Isso acontece automaticamente
toda vez que o programa abre (para chaves já salvas) e toda vez que você
clica em "Salvar chaves". Se a chave usada para revisar o texto estiver
inválida, o programa também recusa iniciar o download/transcrição e avisa
o motivo, antes de gastar tempo processando o vídeo.

### 3. Escolher o vídeo

Você tem duas opções:

- **🔗 Usar link do Google Drive**: clique no botão, cole o link de
  compartilhamento do vídeo quando for solicitado, e confirme.
- **📁 Selecionar arquivo do computador**: clique no botão e escolha o
  arquivo de vídeo pelo explorador de arquivos do Windows que vai abrir.

O processamento começa automaticamente assim que você escolhe o vídeo. Você
pode acompanhar o andamento na caixa "Andamento", na parte de baixo da
janela. Vídeos mais longos podem demorar bastante — isso é esperado.

### 4. Pegar o resultado

Quando terminar, aparece um aviso na tela com o caminho do arquivo. A
transcrição final fica salva na pasta **Transcricoes**, dentro da pasta do
próprio programa (a mesma pasta onde está o `gui.py`), em qualquer sistema
(Windows, macOS ou Linux). A pasta é criada automaticamente se não existir.
Você também pode clicar em **"Abrir pasta de transcrições"**, no canto
inferior direito da janela, para chegar lá diretamente.

> **Importante sobre privacidade:** se você usar um link do Google Drive, o
> vídeo é baixado apenas temporariamente para processar o áudio, e é apagado
> automaticamente assim que a transcrição termina. Nada além do texto final
> fica salvo no computador. Se você escolher um arquivo já salvo no
> computador, o programa só lê esse arquivo — ele não é copiado nem apagado.

---

## Configuração inicial (técnica, feita uma vez por computador)

### Requisitos

- Python 3.10 ou superior.
- Não é necessário instalar o ffmpeg manualmente: a biblioteca
  `imageio-ffmpeg` baixa um binário próprio automaticamente no primeiro uso,
  em qualquer sistema operacional.

### Clonar e instalar

```bash
git clone https://github.com/mourarezendecas/video-transcriber.git
cd video-transcriber
```

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

A partir daqui, o programa já pode ser aberto com `iniciar.bat` (Windows) —
veja a seção "Para quem só vai usar o programa", acima — ou usado por linha
de comando, como descrito a seguir.

### Chave de API (opcional via `.env`)

As chaves também podem ser configuradas direto pela interface gráfica (veja
acima). Se preferir configurar por arquivo, edite o `.env`:

```
OPENAI_API_KEY=sua_chave_aqui
DEEPSEEK_API_KEY=sua_chave_aqui
```

Só precisa configurar a chave do provedor que for usar (o padrão é OpenAI).
**Nunca commite o arquivo `.env`** — ele já está no `.gitignore`.

---

## Uso por linha de comando (avançado)

Além da interface gráfica, dá para rodar tudo pelo terminal — útil para
processar vários vídeos de uma vez ou automatizar.

1. Coloque um ou mais arquivos `.mp4` na pasta `input/`.
2. Rode:

```bash
python main.py
```

3. Os resultados aparecem em `output/`:
   - `<nome>.wav` — áudio extraído
   - `<nome>.txt` — transcrição bruta do Whisper
   - `<nome>_revisado.txt` — versão revisada e formatada em parágrafos pelo modelo de texto (se configurada)

Diferente da interface gráfica, o modo de linha de comando **mantém** o
áudio extraído (`.wav`) em `output/` — útil para depuração. Se quiser o
comportamento "só o texto fica salvo", use a interface gráfica.

### Baixar o vídeo de uma URL (ex.: Google Drive)

Em vez de (ou além de) colocar o arquivo manualmente em `input/`, dá pra
passar a URL do vídeo e o script baixa antes de processar:

```bash
python main.py --url "https://drive.google.com/file/d/XXXXXXXXXXXX/view?usp=sharing"
```

O vídeo baixado é salvo em `input/` (com o nome original do arquivo) e é
processado normalmente pelo mesmo pipeline, junto com qualquer outro `.mp4`
que já esteja na pasta. Funciona com links de compartilhamento do Google
Drive (o arquivo precisa estar como "Qualquer pessoa com o link pode
visualizar") ou com uma URL direta de download de outro servidor.

### Opções

```bash
python main.py --model small          # modelo menor e mais rápido (tiny, base, small, medium, large-v3)
python main.py --language en          # idioma do áudio (padrão: pt)
python main.py --language auto        # detecção automática de idioma
python main.py --no-refine            # pula a revisão por LLM
python main.py --provider deepseek    # usa a DeepSeek em vez da OpenAI para revisar
python main.py --url "..."            # baixa um vídeo da URL antes de processar
```

Na primeira execução, o `faster-whisper` baixa o modelo escolhido (alguns
GBs para `medium`/`large`) e o `imageio-ffmpeg` baixa um binário do ffmpeg —
ambos ficam em cache local (fora do repositório) para as próximas execuções.
Isso vale tanto pela linha de comando quanto pela interface gráfica.

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
├── input/               # (modo linha de comando) coloque os .mp4 aqui — ignorado pelo git
├── output/               # (modo linha de comando) .wav, .txt e _revisado.txt saem aqui — ignorado pelo git
├── transcriber/
│   ├── downloader.py         # baixa vídeo de uma URL (ex.: Google Drive)
│   ├── audio_extractor.py   # extrai áudio com ffmpeg (via imageio-ffmpeg)
│   ├── transcribe.py        # transcreve com faster-whisper, localmente
│   ├── refine.py            # revisa/formata o texto via OpenAI ou DeepSeek
│   └── api_validator.py      # valida chaves de API com uma chamada mínima real
├── gui.py                 # interface gráfica (uso do dia a dia)
├── iniciar.bat             # atalho para abrir a interface gráfica no Windows
├── main.py               # pipeline por linha de comando: vídeo → áudio → transcrição → revisão
├── refine_only.py         # roda só a revisão em um .txt já existente
├── requirements.txt
└── .env.example
```

## Privacidade

- **Interface gráfica (`gui.py` / `iniciar.bat`)**: vídeo e áudio são
  processados numa pasta temporária que é apagada automaticamente ao final
  de cada transcrição — só o texto final é mantido, salvo em
  `Transcricoes/` dentro da pasta do projeto. Isso vale tanto para um arquivo baixado do
  Google Drive quanto para o áudio extraído de um arquivo local (o arquivo
  de vídeo local em si não é copiado nem apagado).
- **Linha de comando (`main.py`)**: os vídeos (`input/`), áudios extraídos e
  transcrições (`output/`) ficam salvos na sua máquina — nenhuma das duas
  pastas é commitada (estão no `.gitignore`).
- Em ambos os modos, a única informação enviada para fora da sua máquina é o
  texto da transcrição, e só na etapa de revisão (para a API da OpenAI ou
  DeepSeek, conforme o provedor escolhido).
