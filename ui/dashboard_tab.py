import tkinter as tk
from tkinter import ttk
import threading


class DashboardTab:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self._build()
        self._refresh()

    def _build(self):
        # Title
        ttk.Label(self.frame, text='Knowledge Database Overview',
                  style='Title.TLabel').pack(pady=(22, 4))
        ttk.Label(self.frame, text='Live stats from your India travel database',
                  style='Subtitle.TLabel').pack(pady=(0, 18))

        # Cards row
        cards_frame = ttk.Frame(self.frame)
        cards_frame.pack(fill='x', padx=30)

        self.card_vars = {}
        card_defs = [
            ('hotels', '🏨', 'Hotels'),
            ('tourist_places', '🏛', 'Tourist Places'),
            ('restaurants', '🍽', 'Restaurants'),
            ('routes', '🗺', 'Routes'),
            ('events', '🎉', 'Events'),
            ('guides', '📖', 'Guides'),
            ('crawl_log', '🔗', 'URLs Crawled'),
        ]
        for i, (key, icon, label) in enumerate(card_defs):
            card = ttk.Frame(cards_frame, style='Card.TFrame', padding=14)
            card.grid(row=0, column=i, padx=8, pady=4, sticky='nsew')
            cards_frame.columnconfigure(i, weight=1)
            ttk.Label(card, text=icon, style='CardTitle.TLabel',
                      font=('Segoe UI', 18)).pack()
            var = tk.StringVar(value='0')
            self.card_vars[key] = var
            ttk.Label(card, textvariable=var, style='CardValue.TLabel').pack()
            ttk.Label(card, text=label, style='CardSub.TLabel').pack()

        # Recent crawl log
        ttk.Label(self.frame, text='Recent Crawl Activity',
                  style='CardTitle.TLabel').pack(pady=(26, 6), anchor='w', padx=30)
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill='both', expand=True, padx=30, pady=(0, 10))
        self.tree = ttk.Treeview(tree_frame,
                                  columns=('url', 'status', 'records', 'time'),
                                  show='headings', height=12)
        for col, width, label in [
            ('url', 520, 'URL'), ('status', 90, 'Status'),
            ('records', 90, 'Records'), ('time', 160, 'Time')
        ]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width)
        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        ttk.Button(self.frame, text='🔄  Refresh Stats',
                   command=self._refresh).pack(pady=10)

    def _refresh(self):
        try:
            stats = self.app.db.get_stats()
            for key, var in self.card_vars.items():
                var.set(str(stats.get(key, 0)))
            rows = self.app.db.conn.execute(
                "SELECT url, status, records_extracted, crawled_at FROM crawl_log ORDER BY id DESC LIMIT 50"
            ).fetchall()
            self.tree.delete(*self.tree.get_children())
            for r in rows:
                self.tree.insert('', 'end', values=(
                    r['url'][:80], r['status'], r['records_extracted'], r['crawled_at'][:19]
                ))
        except Exception:
            pass
