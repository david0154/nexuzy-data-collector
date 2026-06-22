import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import os


class LogsTab:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self._build()
        app.log_widget = self  # register for loguru sink

    def _build(self):
        ttk.Label(self.frame, text='Application Logs',
                  style='Title.TLabel').pack(pady=(18, 4))
        ttk.Label(self.frame, text='Real-time logs from all system components',
                  style='Subtitle.TLabel').pack(pady=(0, 12))

        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill='x', padx=30, pady=4)
        ttk.Button(btn_frame, text='🗑  Clear Logs',
                   command=self._clear).pack(side='left', padx=6)
        ttk.Button(btn_frame, text='💾  Save Logs',
                   command=self._save).pack(side='left', padx=6)
        self.level_var = tk.StringVar(value='ALL')
        ttk.Combobox(btn_frame, textvariable=self.level_var,
                     values=['ALL', 'INFO', 'WARNING', 'ERROR', 'DEBUG'],
                     state='readonly', width=10).pack(side='left', padx=10)

        self.log_box = scrolledtext.ScrolledText(
            self.frame, bg='#0a0a1a', fg='#c0c0e0',
            font=('Consolas', 9), state='disabled', wrap='word'
        )
        self.log_box.pack(fill='both', expand=True, padx=30, pady=(4, 14))

        self.log_box.tag_config('INFO', foreground='#00ff88')
        self.log_box.tag_config('WARNING', foreground='#ffcc00')
        self.log_box.tag_config('ERROR', foreground='#ff4444')
        self.log_box.tag_config('DEBUG', foreground='#8080c0')

    def append(self, message: str, level: str = 'INFO'):
        self.log_box.config(state='normal')
        self.log_box.insert('end', message + '\n', level)
        self.log_box.see('end')
        self.log_box.config(state='disabled')

    def _clear(self):
        self.log_box.config(state='normal')
        self.log_box.delete('1.0', 'end')
        self.log_box.config(state='disabled')

    def _save(self):
        path = filedialog.asksaveasfilename(
            defaultextension='.txt',
            filetypes=[('Text files', '*.txt'), ('All files', '*.*')]
        )
        if path:
            content = self.log_box.get('1.0', 'end')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
