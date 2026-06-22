import tkinter as tk
from tkinter import ttk, messagebox
from loguru import logger
from ui.dashboard_tab import DashboardTab
from ui.crawler_tab import CrawlerTab
from ui.database_tab import DatabaseTab
from ui.import_tab import ImportTab
from ui.export_tab import ExportTab
from ui.dataset_tab import DatasetTab
from ui.kaggle_tab import KaggleTab
from ui.settings_tab import SettingsTab
from ui.logs_tab import LogsTab
from ui.model_download_tab import ModelDownloadTab


class MainWindow:
    def __init__(self, app):
        self.app = app
        self.root = tk.Tk()
        self.root.title("Nexuzy Data Collector v1.2")
        self.root.geometry("1280x820")
        self.root.minsize(1000, 650)
        self.root.configure(bg="#1a1a2e")
        self._setup_style()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background='#1a1a2e', borderwidth=0)
        style.configure('TNotebook.Tab', background='#16213e', foreground='#e0e0e0',
                        padding=[12, 8], font=('Segoe UI', 9, 'bold'))
        style.map('TNotebook.Tab',
                  background=[('selected', '#0f3460')],
                  foreground=[('selected', '#e94560')])
        style.configure('TFrame', background='#1a1a2e')
        style.configure('TLabel', background='#1a1a2e', foreground='#e0e0e0',
                        font=('Segoe UI', 10))
        style.configure('TButton', background='#0f3460', foreground='white',
                        font=('Segoe UI', 10, 'bold'), borderwidth=0, padding=8)
        style.map('TButton', background=[('active', '#e94560')])
        style.configure('TEntry', fieldbackground='#16213e', foreground='white',
                        insertcolor='white', font=('Segoe UI', 10))
        style.configure('TRadiobutton', background='#16213e', foreground='#e0e0e0',
                        font=('Segoe UI', 10))
        style.configure('Treeview', background='#16213e', foreground='#e0e0e0',
                        fieldbackground='#16213e', rowheight=26, font=('Segoe UI', 9))
        style.configure('Treeview.Heading', background='#0f3460', foreground='#e94560',
                        font=('Segoe UI', 10, 'bold'))
        style.configure('TScrollbar', background='#16213e', troughcolor='#1a1a2e')
        style.configure('TProgressbar', troughcolor='#16213e',
                        background='#e94560', borderwidth=0)
        style.configure('green.TLabel', background='#1a1a2e', foreground='#00ff88',
                        font=('Segoe UI', 10, 'bold'))
        style.configure('red.TLabel', background='#1a1a2e', foreground='#e94560',
                        font=('Segoe UI', 10, 'bold'))
        style.configure('Title.TLabel', background='#1a1a2e', foreground='#e94560',
                        font=('Segoe UI', 18, 'bold'))
        style.configure('Subtitle.TLabel', background='#1a1a2e', foreground='#a0a0c0',
                        font=('Segoe UI', 10))
        style.configure('Card.TFrame', background='#16213e', relief='flat')
        style.configure('CardTitle.TLabel', background='#16213e', foreground='#e94560',
                        font=('Segoe UI', 11, 'bold'))
        style.configure('CardValue.TLabel', background='#16213e', foreground='#00ff88',
                        font=('Segoe UI', 18, 'bold'))
        style.configure('CardSub.TLabel', background='#16213e', foreground='#a0a0c0',
                        font=('Segoe UI', 9))

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg='#0f3460', height=56)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text='🌍  NEXUZY DATA COLLECTOR',
                 bg='#0f3460', fg='#e94560',
                 font=('Segoe UI', 16, 'bold')).pack(side='left', padx=20, pady=12)
        tk.Label(header, text='AI-Powered India Travel Knowledge System',
                 bg='#0f3460', fg='#a0a0c0',
                 font=('Segoe UI', 10)).pack(side='left', padx=8, pady=12)
        tk.Label(header, text='v1.2  •  Nexuzy Tech',
                 bg='#0f3460', fg='#606080',
                 font=('Segoe UI', 9)).pack(side='right', padx=20)

        # Notebook Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True)

        self.dashboard      = DashboardTab(self.notebook, self.app)
        self.model_dl       = ModelDownloadTab(self.notebook, self.app)
        self.crawler        = CrawlerTab(self.notebook, self.app)
        self.import_sources = ImportTab(self.notebook, self.app)
        self.database       = DatabaseTab(self.notebook, self.app)
        self.export         = ExportTab(self.notebook, self.app)
        self.dataset        = DatasetTab(self.notebook, self.app)
        self.kaggle         = KaggleTab(self.notebook, self.app)   # ← NEW
        self.settings       = SettingsTab(self.notebook, self.app)
        self.logs           = LogsTab(self.notebook, self.app)

        self.notebook.add(self.dashboard.frame,        text='  📊 Dashboard  ')
        self.notebook.add(self.model_dl.frame,         text='  🤖 AI Model  ')
        self.notebook.add(self.crawler.frame,          text='  🕷 Crawler  ')
        self.notebook.add(self.import_sources.frame,   text='  📥 Import Sources  ')
        self.notebook.add(self.database.frame,         text='  🗄 Database  ')
        self.notebook.add(self.export.frame,           text='  📤 Export  ')
        self.notebook.add(self.dataset.frame,          text='  🤖 Training Dataset  ')
        self.notebook.add(self.kaggle.frame,           text='  📦 Kaggle + AI Clean  ')   # ← NEW
        self.notebook.add(self.settings.frame,         text='  ⚙ Settings  ')
        self.notebook.add(self.logs.frame,             text='  📋 Logs  ')

        # Status bar
        self.status_var = tk.StringVar(value='Ready')
        status_bar = tk.Frame(self.root, bg='#0f3460', height=28)
        status_bar.pack(fill='x', side='bottom')
        status_bar.pack_propagate(False)
        tk.Label(status_bar, textvariable=self.status_var,
                 bg='#0f3460', fg='#a0a0c0',
                 font=('Segoe UI', 9)).pack(side='left', padx=12, pady=5)

    def set_status(self, msg: str):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def _on_close(self):
        if messagebox.askokcancel('Quit', 'Stop all tasks and exit?'):
            try:
                self.app.pipeline.stop()
            except Exception:
                pass
            self.root.destroy()

    def run(self):
        self.root.mainloop()