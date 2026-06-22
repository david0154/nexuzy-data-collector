import tkinter as tk
from tkinter import ttk
import threading
import os


class DatasetTab:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self._build()

    def _build(self):
        ttk.Label(self.frame, text='AI Training Dataset Builder',
                  style='Title.TLabel').pack(pady=(18, 4))
        ttk.Label(self.frame,
                  text='Generate Atithi AI training data (instruction-output JSONL format)',
                  style='Subtitle.TLabel').pack(pady=(0, 18))

        info_frame = ttk.Frame(self.frame, style='Card.TFrame', padding=18)
        info_frame.pack(padx=40, fill='x', pady=6)
        ttk.Label(info_frame, text='Dataset Format (Alpaca-style JSONL):',
                  style='CardTitle.TLabel').pack(anchor='w')
        example = (
            '{"instruction": "Best hotels in Darjeeling", "input": "", "output": "Windamere Hotel - ..."}'  
            '\n{"instruction": "Places to visit in Digha", "input": "", "output": "Digha Beach - ..."}'  
        )
        tk.Text(info_frame, height=4, bg='#0a0a1a', fg='#00ff88',
                font=('Consolas', 9), state='normal').insert('end', example)

        dir_frame = ttk.Frame(self.frame)
        dir_frame.pack(padx=40, fill='x', pady=10)
        ttk.Label(dir_frame, text='Output Directory:').grid(row=0, column=0, sticky='w', padx=4)
        self.dir_var = tk.StringVar(value='export')
        ttk.Entry(dir_frame, textvariable=self.dir_var, width=36).grid(row=0, column=1, padx=6)

        ttk.Button(self.frame, text='🤖  Build Training Dataset',
                   command=self._build_dataset).pack(pady=14)

        self.status_var = tk.StringVar(value='')
        ttk.Label(self.frame, textvariable=self.status_var,
                  style='green.TLabel').pack(pady=6)

        ttk.Label(self.frame, text='Preview (first 50 samples):',
                  style='CardTitle.TLabel').pack(pady=(14, 4), anchor='w', padx=40)
        from tkinter import scrolledtext
        self.preview = scrolledtext.ScrolledText(
            self.frame, height=16, bg='#0a0a1a', fg='#e0e0e0',
            font=('Consolas', 9), state='disabled'
        )
        self.preview.pack(fill='both', expand=True, padx=40, pady=(0, 14))

    def _build_dataset(self):
        output_dir = self.dir_var.get().strip() or 'export'
        self.status_var.set('Building dataset...')

        def run():
            import json
            from core.dataset_builder import DatasetBuilder
            builder = DatasetBuilder(self.app.db, output_dir=output_dir)
            dataset = builder.build_training_dataset()
            path = builder.save_jsonl(dataset)
            self.status_var.set(f'Done! {len(dataset)} samples saved to {path}')
            self.preview.config(state='normal')
            self.preview.delete('1.0', 'end')
            for item in dataset[:50]:
                self.preview.insert('end', json.dumps(item, ensure_ascii=False) + '\n')
            self.preview.config(state='disabled')

        threading.Thread(target=run, daemon=True).start()
