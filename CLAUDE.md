# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A video transcription pipeline: extracts audio from a video, transcribes it locally with Whisper (`faster-whisper`), and optionally sends the transcript to an LLM (OpenAI or DeepSeek) to fix punctuation/grammar and format it into paragraphs. Two entry points share the same `transcriber/` package but differ in behavior — see Architecture below.

The target audience is mixed: `gui.py` is built for non-technical end users (interview transcription, Portuguese-language prompts throughout), while `main.py`/`refine_only.py` are for technical/batch use.

## Commands

Setup (create `.venv`, not `venv` — required by convention here):

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1 (or activate.bat for cmd.exe)
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # copy on Windows
```

Run the GUI (primary entry point, Windows-first):

```bash
python gui.py          # or double-click iniciar.bat on Windows
```

Run the CLI pipeline:

```bash
python main.py                                  # processes every video in input/
python main.py --model small --no-refine         # faster Whisper model, skip LLM revision
python main.py --provider deepseek               # use DeepSeek instead of OpenAI for revision
python main.py --url "https://drive.google.com/..."  # download a video first, then process
python refine_only.py "output/some_video.txt"    # re-run only the LLM revision on an existing transcript
```

There is no test suite, linter, or build step in this repo.

## Architecture

### Two entry points, different privacy/storage behavior

- **`gui.py`** (Tkinter, no extra dependency): always downloads/reads the video into a `tempfile.TemporaryDirectory()` that is deleted when the job finishes — video and extracted `.wav` never persist. Only the final `.txt`/`_revisado.txt` is kept, written to `Transcricoes/` inside the project folder (`PROJECT_DIR / "Transcricoes"`, gitignored) — deliberately not the OS "Documents" folder, to behave the same on Windows/macOS/Linux. `garantir_pasta_saida()` checks/creates that folder and tests that it's writable as an early step in the worker thread, before any download/transcription.
- **`main.py`** (CLI): reads/downloads videos into `input/` and writes `.wav` + `.txt` + `_revisado.txt` into `output/` — both are permanent and gitignored. This is intentional (useful for debugging/batch runs); don't "fix" it to match the GUI's temp-dir behavior without being asked.

Both entry points call the same functions in `transcriber/`, so a change there affects both flows — check `main.py` and `gui.py` when changing a `transcriber/*` function signature.

### `transcriber/` package

- `downloader.py` — `download_video(url, dest_dir)`. Detects Google Drive URLs and uses `gdown`, else falls back to a generic streamed `requests` download. **`gdown`'s `download()` dropped the `fuzzy` kwarg in v6** (URL auto-detection became default behavior); the code tries `fuzzy=True` first and falls back to no-`fuzzy` on `TypeError` to support both API shapes — keep that pattern if touching this function.
- `audio_extractor.py` — `extract_audio(video_path, output_dir)`. Shells out to the `ffmpeg` binary that `imageio_ffmpeg.get_ffmpeg_exe()` downloads automatically, so there's no system-level ffmpeg dependency on any OS.
- `transcribe.py` — `transcribe_audio(audio_path, model_size, language, ...)`. Thin wrapper over `faster_whisper.WhisperModel`, CPU/int8 by default. It reads the 16kHz mono `.wav` from `extract_audio` itself (stdlib `wave` + numpy) and passes the array to Whisper, instead of a file path — faster-whisper's own PyAV decoder breaks with newer `av` releases (`open() got an unexpected keyword argument 'metadata_errors'`), so don't switch back to passing the path. GUI defaults to the `small` model (speed), CLI defaults to `medium` (accuracy) — both are user-overridable, that split is intentional.
- `refine.py` — `refine_transcript(text, api_key, provider)`. The `PROVIDERS` dict here (`base_url`, `model`, `env_key` per provider) is the single source of truth for OpenAI vs. DeepSeek config and is imported by `api_validator.py` too — add new providers here, not in the GUI. Long transcripts are split into ~8000-char chunks (`_split_in_chunks`, word-boundary safe) and revised one chunk at a time, then rejoined with `"\n\n"`.
  - `SYSTEM_PROMPT` is deliberately strict: no inventing/adding content, no summarizing/dropping content, no turning the output into a Q&A/dialogue format (plain flowing prose in paragraphs only). This was tuned after real failures (the model inventing clarifying questions for ambiguous fragments, and occasionally dropping content) — if asked to adjust the tone/formatting of revised transcripts, preserve these anti-hallucination/anti-truncation constraints unless explicitly told to relax them.
  - After each chunk, checks `finish_reason == "length"` and output/input length ratio, printing a warning (not an exception) if a chunk looks truncated.
- `api_validator.py` — `validar_api_key(api_key, provider)`. Validates a key with a real 1-token chat completion call (not just a format/presence check), reusing `PROVIDERS` from `refine.py`. Returns `(bool, message)`, distinguishing auth failure / no permission / no balance / connection error.

### GUI threading model (`gui.py`)

Tkinter runs on the main thread; downloads/transcription/revision run in a background `threading.Thread` (`_executar_pipeline`) so the window doesn't freeze. Progress reaches the UI via a `queue.Queue` (`self.fila_log`) drained every 150ms by `root.after`. Two mechanisms feed that queue:
- `sys.stdout` is globally redirected to a `TextoRedirecionado` wrapper for the duration of the worker thread, so any `print()` in `transcriber/*` shows up in the "Andamento" log box automatically — don't assume `print()` in those modules goes to a real console.
- Special tuples (`("__sucesso__", path)`, `("__erro__", msg)`, `("__validacao__", provider, valid, msg)`) are pushed to signal state changes back to the UI thread; `_drenar_fila_log` dispatches on the tuple's first element.

Before `revisar` (LLM revision) is allowed to run, the GUI validates the selected provider's key synchronously as the first step inside the worker thread — if invalid, it raises before any download/extraction/transcription happens (aborting early is the point; don't move validation after the download step).

### API key config

Both `.env` (loaded via `python-dotenv`) and the GUI's own key fields work; the GUI reads/writes `.env` via `dotenv_values`/`set_key`, prefilling fields on startup and creating `.env` on first save if it doesn't exist yet. `main.py`/`refine_only.py` only read from `.env`/environment (`{PROVIDER}_API_KEY`), no in-app key management.
