import tkinter as tk
from tkinter import ttk, messagebox


TABLES = ['hotels', 'tourist_places', 'restaurants', 'routes', 'events', 'guides']

TABLE_COLUMNS = {
    'hotels': ['id', 'name', 'city', 'district', 'state', 'category', 'price_min', 'rating', 'verified', 'confidence'],
    'tourist_places': ['id', 'name', 'city', 'district', 'state', 'category', 'entry_fee', 'best_time_to_visit', 'verified'],
    'restaurants': ['id', 'name', 'city', 'district', 'cuisine', 'price_range', 'rating', 'verified'],
    'routes': ['id', 'from_city', 'to_city', 'distance_km', 'travel_time', 'transport_modes', 'cost_estimate'],
    'events': ['id', 'name', 'city', 'district', 'category', 'month', 'season'],
    'guides': ['id', 'title', 'city', 'category', 'source_url'],
}


class DatabaseTab:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self._build()

    def _build(self):
        ttk.Label(self.frame, text='Database Browser',
                  style='Title.TLabel').pack(pady=(18, 4))
        ttk.Label(self.frame, text='Browse, search, and inspect your collected travel data',
                  style='Subtitle.TLabel').pack(pady=(0, 12))

        # Controls
        ctrl = ttk.Frame(self.frame)
        ctrl.pack(fill='x', padx=30, pady=6)

        ttk.Label(ctrl, text='Table:').grid(row=0, column=0, padx=4)
        self.table_var = tk.StringVar(value='hotels')
        ttk.Combobox(ctrl, textvariable=self.table_var, values=TABLES,
                     state='readonly', width=18).grid(row=0, column=1, padx=4)

        ttk.Label(ctrl, text='Search:').grid(row=0, column=2, padx=8)
        self.search_var = tk.StringVar()
        ttk.Entry(ctrl, textvariable=self.search_var, width=24).grid(row=0, column=3, padx=4)

        ttk.Button(ctrl, text='🔍  Search', command=self._search).grid(row=0, column=4, padx=6)
        ttk.Button(ctrl, text='📄  Load All', command=self._load_all).grid(row=0, column=5, padx=6)

        # Count label
        self.count_var = tk.StringVar(value='Records: 0')
        ttk.Label(ctrl, textvariable=self.count_var, style='green.TLabel').grid(row=0, column=6, padx=12)

        # Tree
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill='both', expand=True, padx=30, pady=8)
        self.tree = ttk.Treeview(tree_frame, show='headings', height=22)
        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self._load_all()

    def _setup_columns(self, table: str):
        cols = TABLE_COLUMNS.get(table, ['id', 'name', 'city'])
        self.tree.config(columns=cols)
        for col in cols:
            self.tree.heading(col, text=col.replace('_', ' ').title())
            w = 180 if col in ('name', 'title', 'description') else 100
            self.tree.column(col, width=w, anchor='w')

    def _populate(self, rows: list):
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            cols = TABLE_COLUMNS.get(self.table_var.get(), list(row.keys()))
            vals = [str(row.get(c, ''))[:80] for c in cols]
            self.tree.insert('', 'end', values=vals)
        self.count_var.set(f'Records: {len(rows)}')

    def _load_all(self):
        table = self.table_var.get()
        self._setup_columns(table)
        rows = self.app.db.get_all(table, limit=500)
        self._populate(rows)

    def _search(self):
        table = self.table_var.get()
        kw = self.search_var.get().strip()
        self._setup_columns(table)
        if kw:
            rows = self.app.db.search(table, kw, limit=200)
        else:
            rows = self.app.db.get_all(table, limit=500)
        self._populate(rows)
