import tkinter as tk
from tkinter import ttk, scrolledtext
import threading


class CrawlerTab:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self._build()

    def _build(self):
        ttk.Label(self.frame, text='Web Crawler Control',
                  style='Title.TLabel').pack(pady=(18, 4))
        ttk.Label(self.frame, text='Discover and extract India travel data from the web',
                  style='Subtitle.TLabel').pack(pady=(0, 14))

        # URL input
        url_frame = ttk.Frame(self.frame)
        url_frame.pack(fill='x', padx=30, pady=4)
        ttk.Label(url_frame, text='Seed URLs (one per line):').pack(anchor='w')
        self.url_text = scrolledtext.ScrolledText(
            url_frame, height=7, bg='#16213e', fg='white',
            insertbackground='white', font=('Consolas', 10), wrap='word'
        )
        self.url_text.pack(fill='x', pady=4)
        seed_urls = self.app.config.get('sources', {}).get('seed_urls', [])
        self.url_text.insert('end', '\n'.join(seed_urls))

        # Options
        opt_frame = ttk.Frame(self.frame)
        opt_frame.pack(fill='x', padx=30, pady=8)
        ttk.Label(opt_frame, text='Max Pages:').grid(row=0, column=0, sticky='w', padx=4)
        self.max_pages_var = tk.StringVar(value='50')
        ttk.Entry(opt_frame, textvariable=self.max_pages_var, width=8).grid(row=0, column=1, padx=4)
        ttk.Label(opt_frame, text='Delay (sec):').grid(row=0, column=2, sticky='w', padx=4)
        self.delay_var = tk.StringVar(value='1.5')
        ttk.Entry(opt_frame, textvariable=self.delay_var, width=8).grid(row=0, column=3, padx=4)
        self.dynamic_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_frame, text='Dynamic (JS) Scraping',
                        variable=self.dynamic_var).grid(row=0, column=4, padx=12)

        # Buttons
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(pady=10)
        self.start_btn = ttk.Button(btn_frame, text='▶  Start Crawler',
                                     command=self._start_crawler)
        self.start_btn.grid(row=0, column=0, padx=8)
        self.stop_btn = ttk.Button(btn_frame, text='⏹  Stop Crawler',
                                    command=self._stop_crawler, state='disabled')
        self.stop_btn.grid(row=0, column=1, padx=8)

        # Status label
        self.status_var = tk.StringVar(value='Idle')
        ttk.Label(self.frame, textvariable=self.status_var,
                  style='green.TLabel').pack(pady=4)

        # Live log
        ttk.Label(self.frame, text='Crawler Log:', style='CardTitle.TLabel').pack(
            pady=(10, 4), anchor='w', padx=30)
        self.log_box = scrolledtext.ScrolledText(
            self.frame, height=14, bg='#0a0a1a', fg='#00ff88',
            insertbackground='white', font=('Consolas', 9), state='disabled'
        )
        self.log_box.pack(fill='both', expand=True, padx=30, pady=(0, 12))

    def _append_log(self, msg: str):
        self.log_box.config(state='normal')
        self.log_box.insert('end', msg + '\n')
        self.log_box.see('end')
        self.log_box.config(state='disabled')

    def _start_crawler(self):
        urls = [u.strip() for u in self.url_text.get('1.0', 'end').splitlines() if u.strip()]
        if not urls:
            from tkinter import messagebox
            messagebox.showwarning('No URLs', 'Please enter at least one seed URL.')
            return
        try:
            self.app.config['crawler']['max_pages_per_domain'] = int(self.max_pages_var.get())
            self.app.config['crawler']['delay_between_requests'] = float(self.delay_var.get())
        except ValueError:
            pass
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_var.set('Running...')
        self._append_log(f'Starting crawler with {len(urls)} seed URLs...')

        def on_status(msg):
            self._append_log(msg)
            self.status_var.set(msg)

        def run():
            from core.crawler_pipeline import CrawlerPipeline
            self.app.pipeline = CrawlerPipeline(self.app.config, self.app.db, on_status=on_status)
            self.app.pipeline.start(urls)
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            self.status_var.set('Finished')

        threading.Thread(target=run, daemon=True).start()

    def _stop_crawler(self):
        try:
            self.app.pipeline.stop()
        except Exception:
            pass
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_var.set('Stopped')
        self._append_log('Crawler stopped by user.')
