import tkinter as tk
from tkinter import ttk, messagebox
import yaml
import os


class SettingsTab:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self._build()

    def _build(self):
        ttk.Label(self.frame, text='Settings',
                  style='Title.TLabel').pack(pady=(18, 4))
        ttk.Label(self.frame, text='Configure crawler, AI model, verification parameters',
                  style='Subtitle.TLabel').pack(pady=(0, 16))

        canvas = tk.Canvas(self.frame, bg='#1a1a2e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.frame, orient='vertical', command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind('<Configure>',
                          lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True, padx=30)
        scrollbar.pack(side='right', fill='y')

        self.vars = {}

        sections = [
            ('Crawler Settings', [
                ('crawler.max_pages_per_domain', 'Max Pages Per Domain', '50'),
                ('crawler.delay_between_requests', 'Delay Between Requests (sec)', '1.5'),
                ('crawler.timeout', 'Request Timeout (sec)', '30'),
                ('crawler.max_retries', 'Max Retries', '3'),
                ('crawler.user_agent', 'User Agent', 'NexuzyDataCollector/1.0'),
            ]),
            ('AI Model Settings', [
                ('model.path', 'Model Path (.gguf)', 'models/gemma-4b-it-q4_k_m.gguf'),
                ('model.n_ctx', 'Context Length', '4096'),
                ('model.n_threads', 'CPU Threads', '4'),
                ('model.temperature', 'Temperature', '0.1'),
            ]),
            ('Verification Settings', [
                ('verification.min_sources', 'Min Sources for Verification', '2'),
                ('verification.confidence_threshold', 'Confidence Threshold (%)', '70'),
            ]),
            ('Database Settings', [
                ('database.path', 'Database Path', 'data/nexuzy_travel.db'),
            ]),
            ('Export Settings', [
                ('export.output_dir', 'Export Output Directory', 'export'),
            ]),
        ]

        for section_title, fields in sections:
            sec_frame = ttk.Frame(scroll_frame, style='Card.TFrame', padding=14)
            sec_frame.pack(fill='x', padx=10, pady=8)
            ttk.Label(sec_frame, text=section_title, style='CardTitle.TLabel').grid(
                row=0, column=0, columnspan=2, sticky='w', pady=(0, 8))
            for i, (key, label, default) in enumerate(fields, start=1):
                ttk.Label(sec_frame, text=label).grid(row=i, column=0, sticky='w', pady=3, padx=4)
                keys = key.split('.')
                current = self.app.config
                for k in keys:
                    current = current.get(k, {}) if isinstance(current, dict) else default
                val = current if isinstance(current, (str, int, float)) else default
                var = tk.StringVar(value=str(val))
                self.vars[key] = var
                ttk.Entry(sec_frame, textvariable=var, width=42).grid(
                    row=i, column=1, sticky='w', pady=3, padx=8)

        ttk.Button(self.frame, text='💾  Save Settings',
                   command=self._save).pack(pady=14)

    def _save(self):
        for key, var in self.vars.items():
            keys = key.split('.')
            cfg = self.app.config
            for k in keys[:-1]:
                cfg = cfg.setdefault(k, {})
            val = var.get()
            try:
                val = int(val)
            except ValueError:
                try:
                    val = float(val)
                except ValueError:
                    pass
            cfg[keys[-1]] = val
        try:
            with open('config.yaml', 'w') as f:
                yaml.dump(self.app.config, f, default_flow_style=False)
            messagebox.showinfo('Saved', 'Settings saved to config.yaml')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to save: {e}')
