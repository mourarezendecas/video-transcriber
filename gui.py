"""Interface gráfica simples do video-transcriber, para usuários não técnicos.

Permite configurar as chaves de API (OpenAI/DeepSeek), escolher entre um
vídeo do Google Drive (por link) ou um arquivo local, e acompanhar o
andamento da transcrição. Nenhum vídeo ou áudio fica salvo permanentemente —
apenas o texto final, em Documentos\\Transcricoes.

Uso: python gui.py  (ou dando duplo-clique em iniciar.bat)
"""

import os
import queue
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

from dotenv import dotenv_values, load_dotenv, set_key

from transcriber.audio_extractor import extract_audio
from transcriber.downloader import download_video
from transcriber.refine import refine_transcript
from transcriber.transcribe import transcribe_audio

PROJECT_DIR = Path(__file__).parent
ENV_PATH = PROJECT_DIR / ".env"

MODELOS_WHISPER = ["tiny", "base", "small", "medium", "large-v3"]
PROVEDORES = ["openai", "deepseek"]


def get_documents_folder() -> Path:
    """Retorna a pasta 'Documentos' do usuário (funciona mesmo em Windows em português)."""
    if sys.platform == "win32":
        try:
            import ctypes

            CSIDL_PERSONAL = 5
            SHGFP_TYPE_CURRENT = 0
            buf = ctypes.create_unicode_buffer(260)
            ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
            if buf.value:
                return Path(buf.value)
        except Exception:
            pass
    return Path.home() / "Documents"


OUTPUT_DIR = get_documents_folder() / "Transcricoes"


class TextoRedirecionado:
    """Redireciona print() para uma fila, lida periodicamente pela thread da GUI."""

    def __init__(self, fila: queue.Queue):
        self.fila = fila

    def write(self, mensagem: str):
        if mensagem.strip():
            self.fila.put(mensagem)

    def flush(self):
        pass


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Transcritor de Vídeos")
        self.root.geometry("640x580")
        self.root.resizable(False, False)

        self.fila_log = queue.Queue()
        self.processando = False

        self._montar_layout()
        self._carregar_chaves_salvas()
        self.root.after(150, self._drenar_fila_log)

    # ---------- layout ----------

    def _montar_layout(self):
        pad = {"padx": 12, "pady": 6}

        config = ttk.LabelFrame(self.root, text="Configuração das chaves de API")
        config.pack(fill="x", **pad)

        ttk.Label(config, text="OpenAI API Key:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.var_openai = tk.StringVar()
        ttk.Entry(config, textvariable=self.var_openai, show="*", width=45).grid(
            row=0, column=1, padx=6, pady=4
        )

        ttk.Label(config, text="DeepSeek API Key:").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.var_deepseek = tk.StringVar()
        ttk.Entry(config, textvariable=self.var_deepseek, show="*", width=45).grid(
            row=1, column=1, padx=6, pady=4
        )

        ttk.Button(config, text="Salvar chaves", command=self._salvar_chaves).grid(
            row=0, column=2, rowspan=2, padx=8
        )

        opcoes = ttk.LabelFrame(self.root, text="Opções da transcrição")
        opcoes.pack(fill="x", **pad)

        ttk.Label(opcoes, text="Revisar texto com:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.var_provider = tk.StringVar(value="openai")
        ttk.Combobox(
            opcoes, textvariable=self.var_provider, values=PROVEDORES, state="readonly", width=12
        ).grid(row=0, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(opcoes, text="Qualidade da transcrição:").grid(row=0, column=2, sticky="w", padx=6, pady=4)
        self.var_modelo = tk.StringVar(value="small")
        ttk.Combobox(
            opcoes, textvariable=self.var_modelo, values=MODELOS_WHISPER, state="readonly", width=12
        ).grid(row=0, column=3, sticky="w", padx=6, pady=4)

        self.var_revisar = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            opcoes, text="Revisar e formatar o texto com IA", variable=self.var_revisar
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=4)

        fonte = ttk.LabelFrame(self.root, text="Vídeo a transcrever")
        fonte.pack(fill="x", **pad)

        ttk.Label(fonte, text="Escolha uma das opções abaixo:").pack(anchor="w", padx=6, pady=(6, 2))

        botoes = ttk.Frame(fonte)
        botoes.pack(fill="x", padx=6, pady=6)

        self.btn_url = ttk.Button(
            botoes, text="🔗  Usar link do Google Drive", command=self._iniciar_por_url
        )
        self.btn_url.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_arquivo = ttk.Button(
            botoes, text="📁  Selecionar arquivo do computador", command=self._iniciar_por_arquivo
        )
        self.btn_arquivo.pack(side="left", expand=True, fill="x", padx=(4, 0))

        status = ttk.Frame(self.root)
        status.pack(fill="x", **pad)
        self.var_status = tk.StringVar(value="Aguardando...")
        ttk.Label(status, textvariable=self.var_status, font=("Segoe UI", 9, "bold")).pack(anchor="w")

        log_frame = ttk.LabelFrame(self.root, text="Andamento")
        log_frame.pack(fill="both", expand=True, **pad)
        self.txt_log = scrolledtext.ScrolledText(log_frame, height=14, state="disabled", wrap="word")
        self.txt_log.pack(fill="both", expand=True, padx=6, pady=6)

        rodape = ttk.Frame(self.root)
        rodape.pack(fill="x", **pad)
        ttk.Button(rodape, text="Abrir pasta de transcrições", command=self._abrir_pasta_saida).pack(
            side="right"
        )

    # ---------- chaves de API ----------

    def _carregar_chaves_salvas(self):
        if ENV_PATH.exists():
            valores = dotenv_values(ENV_PATH)
            self.var_openai.set(valores.get("OPENAI_API_KEY") or "")
            self.var_deepseek.set(valores.get("DEEPSEEK_API_KEY") or "")

    def _salvar_chaves(self):
        if not ENV_PATH.exists():
            ENV_PATH.touch()
        set_key(str(ENV_PATH), "OPENAI_API_KEY", self.var_openai.get().strip())
        set_key(str(ENV_PATH), "DEEPSEEK_API_KEY", self.var_deepseek.get().strip())
        messagebox.showinfo("Chaves salvas", "As chaves de API foram salvas com sucesso.")

    # ---------- seleção da fonte do vídeo ----------

    def _iniciar_por_url(self):
        if self.processando:
            return
        url = simpledialog.askstring(
            "Link do Google Drive",
            "Cole aqui o link de compartilhamento do vídeo no Google Drive:",
            parent=self.root,
        )
        if not url:
            return
        self._iniciar_processamento(origem_url=url.strip(), caminho_local=None)

    def _iniciar_por_arquivo(self):
        if self.processando:
            return
        caminho = filedialog.askopenfilename(
            title="Selecione o vídeo",
            filetypes=[
                ("Arquivos de vídeo", "*.mp4 *.mov *.mkv *.avi *.webm"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not caminho:
            return
        self._iniciar_processamento(origem_url=None, caminho_local=Path(caminho))

    # ---------- execução ----------

    def _iniciar_processamento(self, origem_url, caminho_local):
        provider = self.var_provider.get()
        api_key = (self.var_openai.get() if provider == "openai" else self.var_deepseek.get()).strip()
        revisar = self.var_revisar.get()

        if revisar and not api_key:
            prosseguir = messagebox.askyesno(
                "Chave de API não configurada",
                f"A chave de {provider} não foi configurada, então o texto não será "
                "revisado — só a transcrição bruta será salva. Deseja continuar assim mesmo?",
            )
            if not prosseguir:
                return
            revisar = False

        self.processando = True
        self._alternar_botoes(ativo=False)
        self.var_status.set("Processando... isso pode levar alguns minutos.")
        self._log("--- Iniciando novo processamento ---")

        thread = threading.Thread(
            target=self._executar_pipeline,
            args=(origem_url, caminho_local, self.var_modelo.get(), provider, api_key, revisar),
            daemon=True,
        )
        thread.start()

    def _executar_pipeline(self, origem_url, caminho_local, modelo, provider, api_key, revisar):
        stdout_original = sys.stdout
        sys.stdout = TextoRedirecionado(self.fila_log)
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

            with tempfile.TemporaryDirectory(prefix="video_transcriber_") as tmp:
                tmp_dir = Path(tmp)

                if origem_url:
                    print(f"Baixando vídeo de: {origem_url}")
                    video_path = download_video(origem_url, tmp_dir)
                    print("Vídeo baixado temporariamente (será apagado ao final).")
                else:
                    video_path = caminho_local
                    print(f"Usando arquivo local: {video_path.name}")

                print("Extraindo áudio...")
                audio_path = extract_audio(video_path, tmp_dir)

                print(f"Transcrevendo com Whisper ({modelo})... isso pode demorar.")
                texto_bruto = transcribe_audio(audio_path, model_size=modelo, language="pt")

                bruto_path = OUTPUT_DIR / f"{video_path.stem}.txt"
                bruto_path.write_text(texto_bruto, encoding="utf-8")
                print(f"Transcrição salva em {bruto_path}")

                caminho_final = bruto_path

                if revisar:
                    print(f"Revisando texto com {provider}...")
                    texto_revisado = refine_transcript(texto_bruto, api_key, provider=provider)
                    revisado_path = OUTPUT_DIR / f"{video_path.stem}_revisado.txt"
                    revisado_path.write_text(texto_revisado, encoding="utf-8")
                    print(f"Texto revisado salvo em {revisado_path}")
                    caminho_final = revisado_path

            print("Vídeo e áudio temporários apagados. Apenas o texto foi mantido.")
            self.fila_log.put(("__sucesso__", str(caminho_final)))

        except Exception as exc:
            mensagem = f"{type(exc).__name__}: {exc}"
            self.fila_log.put(f"❌ ERRO: {mensagem}")
            self.fila_log.put(("__erro__", mensagem))
        finally:
            sys.stdout = stdout_original

    # ---------- utilidades de UI ----------

    def _alternar_botoes(self, ativo: bool):
        estado = "normal" if ativo else "disabled"
        self.btn_url.config(state=estado)
        self.btn_arquivo.config(state=estado)

    def _drenar_fila_log(self):
        try:
            while True:
                item = self.fila_log.get_nowait()
                if isinstance(item, tuple) and item[0] == "__sucesso__":
                    self._finalizar(sucesso=True, caminho=item[1])
                elif isinstance(item, tuple) and item[0] == "__erro__":
                    self._finalizar(sucesso=False, mensagem_erro=item[1])
                else:
                    self._log(item)
        except queue.Empty:
            pass
        self.root.after(150, self._drenar_fila_log)

    def _log(self, mensagem: str):
        self.txt_log.config(state="normal")
        self.txt_log.insert("end", mensagem if mensagem.endswith("\n") else mensagem + "\n")
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    def _finalizar(self, sucesso: bool, caminho: str = "", mensagem_erro: str = ""):
        self.processando = False
        self._alternar_botoes(ativo=True)
        if sucesso:
            self._log("--- Concluído ---")
            self.var_status.set("Concluído!")
            messagebox.showinfo("Concluído", f"Transcrição salva em:\n{caminho}")
        else:
            self._log("--- Processamento interrompido por erro ---")
            self.var_status.set("❌ Ocorreu um erro. Veja o Andamento ou a mensagem abaixo.")
            messagebox.showerror("Erro", f"Ocorreu um erro durante o processamento:\n\n{mensagem_erro}")

    def _abrir_pasta_saida(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(OUTPUT_DIR)
        else:
            messagebox.showinfo("Pasta de transcrições", str(OUTPUT_DIR))


def main():
    load_dotenv(ENV_PATH)
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
