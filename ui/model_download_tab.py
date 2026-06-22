import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import os
from core.model_downloader import MODEL_OPTIONS, MODEL_CACHE_DIR


class ModelDownloadTab:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self._build()
        self._check_existing()

    def _build(self):
        ttk.Label(self.frame, text='AI Model Manager',
                  style='Title.TLabel').pack(pady=(18, 4))
        ttk.Label(self.frame,
                  text='Auto-download AI model from HuggingFace  —  Pure Python, no C++ needed',
                  style='Subtitle.TLabel').pack(pady=(0, 16))

        # Status card
        card = ttk.Frame(self.frame, style='Card.TFrame', padding=16)
        card.pack(padx=40, fill='x', pady=6)
        ttk.Label(card, text='Model Status:',
                  style='CardTitle.TLabel').grid(row=0, column=0, sticky='w')
        self.status_var = tk.StringVar(value='⏳ Checking...')
        ttk.Label(card, textvariable=self.status_var,
                  style='green.TLabel').grid(row=0, column=1, sticky='w', padx=12)
        ttk.Label(card, text='Cache Dir:',
                  style='CardTitle.TLabel').grid(row=1, column=0, sticky='w', pady=(6, 0))
        ttk.Label(card, text=os.path.abspath(MODEL_CACHE_DIR),
                  style='CardSub.TLabel').grid(row=1, column=1, sticky='w', padx=12)

        # Model selection
        sel = ttk.Frame(self.frame, style='Card.TFrame', padding=16)
        sel.pack(padx=40, fill='x', pady=8)
        ttk.Label(sel, text='Select Model:',
                  style='CardTitle.TLabel').pack(anchor='w', pady=(0, 8))

        self.model_var = tk.StringVar(value=MODEL_OPTIONS[0]['label'])
        for opt in MODEL_OPTIONS:
            row = ttk.Frame(sel)
            row.pack(fill='x', pady=2)
            ttk.Radiobutton(row, text=opt['label'],
                            variable=self.model_var,
                            value=opt['label']).pack(side='left')
            ttk.Label(row, text=opt['size'],
                      style='CardSub.TLabel').pack(side='left', padx=12)

        # Info box
        info = ttk.Frame(self.frame, style='Card.TFrame', padding=12)
        info.pack(padx=40, fill='x', pady=4)
        ttk.Label(info,
                  text='ℹ️  Pure Python via HuggingFace Transformers — No C++, no GGUF, no Visual Studio needed',
                  style='CardSub.TLabel').pack(anchor='w')
        ttk.Label(info,
                  text='ℹ️  Model is downloaded once and cached in models/hf_cache/ for reuse',
                  style='CardSub.TLabel').pack(anchor='w', pady=2)
        ttk.Label(info,
                  text='ℹ️  No HuggingFace token needed for public models (Gemma, TinyLlama, Phi)',
                  style='CardSub.TLabel').pack(anchor='w')

        # Token
        tok_frame = ttk.Frame(self.frame)
        tok_frame.pack(padx=40, fill='x', pady=8)
        ttk.Label(tok_frame, text='HuggingFace Token (optional):').grid(
            row=0, column=0, sticky='w', padx=4)
        self.token_var = tk.StringVar()
        ttk.Entry(tok_frame, textvariable=self.token_var,
                  width=44, show='*').grid(row=0, column=1, padx=6)

        # Progress
        prog = ttk.Frame(self.frame)
        prog.pack(padx=40, fill='x', pady=8)
        self.progress_var = tk.DoubleVar(value=0)
        ttk.Progressbar(prog, variable=self.progress_var,
                        maximum=100, length=600,
                        mode='determinate').pack(fill='x')
        self.prog_label_var = tk.StringVar(value='')
        ttk.Label(prog, textvariable=self.prog_label_var,
                  style='CardSub.TLabel').pack(anchor='w', pady=2)

        # Buttons
        btns = ttk.Frame(self.frame)
        btns.pack(pady=10)
        self.dl_btn = ttk.Button(btns, text='⬇  Download Model',
                                  command=self._start_download)
        self.dl_btn.grid(row=0, column=0, padx=10)
        ttk.Button(btns, text='🔍  Check Status',
                   command=self._check_existing).grid(row=0, column=1, padx=10)
        ttk.Button(btns, text='📁  Open Cache Folder',
                   command=self._open_folder).grid(row=0, column=2, padx=10)

        # Log
        ttk.Label(self.frame, text='Download Log:',
                  style='CardTitle.TLabel').pack(pady=(10, 4), anchor='w', padx=40)
        self.log_box = scrolledtext.ScrolledText(
            self.frame, height=10, bg='#0a0a1a', fg='#00ff88',
            font=('Consolas', 9), state='disabled')
        self.log_box.pack(fill='both', expand=True, padx=40, pady=(0, 14))

    def _log(self, msg):
        self.log_box.config(state='normal')
        self.log_box.insert('end', msg + '\n')
        self.log_box.see('end')
        self.log_box.config(state='disabled')

    def _check_existing(self):
        from core.model_downloader import ModelDownloader
        dl = ModelDownloader()
        selected = self.model_var.get() if hasattr(self, 'model_var') else MODEL_OPTIONS[0]['label']
        model_id = next((o['model_id'] for o in MODEL_OPTIONS if o['label'] == selected),
                        MODEL_OPTIONS[0]['model_id'])
        if dl.model_exists(model_id):
            self.status_var.set('✅ Model Cached & Ready')
            self._log(f'✅ Model found in cache: {MODEL_CACHE_DIR}/{model_id.replace("/", "--")}')
        else:
            self.status_var.set('❌ Not Downloaded Yet')
            self._log('Model not cached. Click Download to fetch from HuggingFace.')

    def _start_download(self):
        selected = self.model_var.get()
        model_id = next((o['model_id'] for o in MODEL_OPTIONS if o['label'] == selected),
                        MODEL_OPTIONS[0]['model_id'])
        hf_token = self.token_var.get().strip() or None
        self.dl_btn.config(state='disabled')
        self.progress_var.set(0)
        self._log(f'Starting download: {model_id}')

        def on_progress(pct, msg):
            self.progress_var.set(pct)
            self.prog_label_var.set(f'{pct}%  —  {msg}')

        def run():
            from core.model_downloader import ModelDownloader
            dl = ModelDownloader(
                on_progress=on_progress,
                on_status=self._log
            )
            path = dl.download(model_id=model_id, hf_token=hf_token)
            if path:
                self.app.config.setdefault('model', {})['hf_model'] = model_id
                self._check_existing()
            self.dl_btn.config(state='normal')

        threading.Thread(target=run, daemon=True).start()

    def _open_folder(self):
        import subprocess, platform
        folder = os.path.abspath(MODEL_CACHE_DIR)
        os.makedirs(folder, exist_ok=True)
        if platform.system() == 'Windows':
            subprocess.Popen(f'explorer "{folder}"')
        elif platform.system() == 'Darwin':
            subprocess.Popen(['open', folder])
        else:
            subprocess.Popen(['xdg-open', folder])
