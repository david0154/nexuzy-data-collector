# ui/kaggle_tab.py  —  Kaggle & Open Datasets browser + Download→DB + AI Cleaner + Dup Guard
# Dataset list  : kaggle_datasets.py  (single source of truth, no duplicates)
# Download engine: core/kaggle_importer.py  (uses ~/.kaggle/kaggle.json automatically)

import io
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

from kaggle_datasets import ALL_DATASETS, CATEGORY_COLORS


def _db_path(app) -> str:
    return getattr(app, 'db_path', 'data/nexuzy_travel.db')


class KaggleTab:
    """Tab: browse all curated datasets + Download→DB + AI Cleaner + Dup Guard."""

    def __init__(self, notebook, app):
        self.app = app
        self.frame = ttk.Frame(notebook)
        self._selected_ds: dict | None = None
        self._dl_running = False
        self._build()

    # ── UI build ──────────────────────────────────────────────────────────────
    def _build(self):
        # toolbar
        tb = tk.Frame(self.frame, bg='#0f3460', height=48)
        tb.pack(fill='x')
        tb.pack_propagate(False)
        tk.Label(tb, text='📦  Kaggle & Open Datasets   ·   🤖 AI Cleaner   ·   🔍 Dup Guard',
                 bg='#0f3460', fg='#e94560',
                 font=('Segoe UI', 11, 'bold')).pack(side='left', padx=14, pady=10)
        btn_area = tk.Frame(tb, bg='#0f3460')
        btn_area.pack(side='right', padx=10)
        tk.Button(btn_area, text='  🔍  Scan ALL Duplicates  ',
                  bg='#ffd166', fg='#0a0a1e', font=('Segoe UI', 9, 'bold'),
                  relief='flat', cursor='hand2',
                  command=self._run_dup_check).pack(side='left', padx=4, pady=8)
        tk.Button(btn_area, text='  🤖  Clean Entire DB  ',
                  bg='#e94560', fg='white', font=('Segoe UI', 9, 'bold'),
                  relief='flat', cursor='hand2',
                  command=self._run_ai_cleaner).pack(side='left', padx=4, pady=8)

        # category filter
        fbar = tk.Frame(self.frame, bg='#16213e')
        fbar.pack(fill='x')
        tk.Label(fbar, text='Filter:', bg='#16213e', fg='#a0a0c0',
                 font=('Segoe UI', 9)).pack(side='left', padx=(12, 4), pady=5)
        self._cat_var = tk.StringVar(value='All')
        for cat in ['All'] + sorted(CATEGORY_COLORS.keys()):
            fg = CATEGORY_COLORS.get(cat, '#e0e0e0')
            tk.Radiobutton(
                fbar, text=cat, variable=self._cat_var, value=cat,
                bg='#16213e', fg=fg, selectcolor='#0f3460',
                activebackground='#16213e', font=('Segoe UI', 8),
                command=self._refresh_list,
            ).pack(side='left', padx=3, pady=5)

        # split pane
        pane = tk.PanedWindow(self.frame, orient='horizontal',
                              bg='#1a1a2e', sashwidth=5)
        pane.pack(fill='both', expand=True)

        # LEFT: dataset tree
        lf = tk.Frame(pane, bg='#16213e')
        pane.add(lf, minsize=430)
        cols = ('cat', 'name', 'records')
        self.tree = ttk.Treeview(lf, columns=cols, show='headings', selectmode='browse')
        self.tree.heading('cat',     text='Category')
        self.tree.heading('name',    text='Dataset')
        self.tree.heading('records', text='Records')
        self.tree.column('cat',     width=145, minwidth=120)
        self.tree.column('name',    width=310, minwidth=200)
        self.tree.column('records', width=85,  minwidth=60, anchor='center')
        vsb = ttk.Scrollbar(lf, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        for cat, colour in CATEGORY_COLORS.items():
            self.tree.tag_configure(cat, foreground=colour)

        # RIGHT: detail panel
        rf = tk.Frame(pane, bg='#16213e', padx=16, pady=14)
        pane.add(rf, minsize=380)
        tk.Label(rf, text='Dataset Details', bg='#16213e', fg='#e94560',
                 font=('Segoe UI', 13, 'bold')).pack(anchor='w')
        ttk.Separator(rf).pack(fill='x', pady=(5, 10))
        self._d_name = self._lbl(rf, '', bold=True,  sz=11, fg='#e0e0e0')
        self._d_cat  = self._lbl(rf, '', bold=False, sz=9,  fg='#a0a0c0')
        self._d_recs = self._lbl(rf, '', bold=False, sz=9,  fg='#00ff88')
        tk.Frame(rf, bg='#16213e', height=6).pack()
        self._d_desc = self._lbl(rf, '', bold=False, sz=10, fg='#c0c0d0', wrap=360)
        tk.Frame(rf, bg='#16213e', height=10).pack()

        # row 1: open + import tab
        row1 = tk.Frame(rf, bg='#16213e')
        row1.pack(anchor='w', pady=(0, 6))
        self._open_btn = tk.Button(
            row1, text='  🌐  Open on Kaggle  ',
            bg='#20beff', fg='#0a0a1e', font=('Segoe UI', 9, 'bold'),
            relief='flat', cursor='hand2', command=self._open_url, state='disabled')
        self._open_btn.pack(side='left', padx=(0, 8))
        self._import_tab_btn = tk.Button(
            row1, text='  📥  Import Tab  ',
            bg='#0f3460', fg='white', font=('Segoe UI', 9, 'bold'),
            relief='flat', cursor='hand2', command=self._goto_import, state='disabled')
        self._import_tab_btn.pack(side='left')

        # row 2: DOWNLOAD → DB
        row2 = tk.Frame(rf, bg='#16213e')
        row2.pack(anchor='w', pady=(0, 4))
        self._dl_btn = tk.Button(
            row2, text='  ⬇️  Download & Save to Database  ',
            bg='#00b894', fg='white', font=('Segoe UI', 10, 'bold'),
            relief='flat', cursor='hand2', command=self._download_and_store,
            state='disabled')
        self._dl_btn.pack(side='left')
        self._dl_status = tk.Label(
            row2, text='', bg='#16213e', fg='#00ff88', font=('Segoe UI', 9))
        self._dl_status.pack(side='left', padx=(10, 0))

        # progress bar (hidden by default)
        self._progress = ttk.Progressbar(rf, mode='indeterminate', length=340)
        self._progress.pack(anchor='w', pady=(0, 8))
        self._progress.pack_forget()

        # row 3: DB tools
        row3 = tk.Frame(rf, bg='#16213e')
        row3.pack(anchor='w', pady=(0, 10))
        tk.Button(row3, text='  🔍  Check Duplicates in DB  ',
                  bg='#ffd166', fg='#0a0a1e', font=('Segoe UI', 9, 'bold'),
                  relief='flat', cursor='hand2',
                  command=self._run_dup_check).pack(side='left', padx=(0, 8))
        tk.Button(row3, text='  🤖  Clean DB (AI)  ',
                  bg='#e94560', fg='white', font=('Segoe UI', 9, 'bold'),
                  relief='flat', cursor='hand2',
                  command=self._run_ai_cleaner).pack(side='left')

        # output log
        log_hdr = tk.Frame(rf, bg='#16213e')
        log_hdr.pack(fill='x', anchor='w')
        tk.Label(log_hdr, text='🖥️  Output Log', bg='#16213e', fg='#e94560',
                 font=('Segoe UI', 10, 'bold')).pack(side='left')
        tk.Button(log_hdr, text='Clear', bg='#16213e', fg='#606080',
                  font=('Segoe UI', 8), relief='flat', cursor='hand2',
                  command=self._clear_log).pack(side='right')
        self._log_box = tk.Text(
            rf, height=14, bg='#0a0a1e', fg='#00ff88',
            font=('Consolas', 9), relief='flat', state='disabled', wrap='word')
        self._log_box.pack(fill='both', expand=True, pady=(4, 0))

        self._refresh_list()

    # ── label helper ──────────────────────────────────────────────────────────
    def _lbl(self, parent, text, bold=False, sz=10, fg='#e0e0e0', wrap=None):
        kw = dict(bg='#16213e', fg=fg,
                  font=('Segoe UI', sz, 'bold' if bold else 'normal'),
                  anchor='w', justify='left')
        if wrap:
            kw['wraplength'] = wrap
        lbl = tk.Label(parent, text=text, **kw)
        lbl.pack(fill='x', anchor='w')
        return lbl

    # ── list / selection ──────────────────────────────────────────────────────
    def _refresh_list(self):
        cat_filter = self._cat_var.get()
        self.tree.delete(*self.tree.get_children())
        seen: set[str] = set()
        for ds in ALL_DATASETS:
            if ds['url'] in seen:
                continue
            seen.add(ds['url'])
            if cat_filter != 'All' and ds['category'] != cat_filter:
                continue
            self.tree.insert('', 'end',
                             values=(ds['category'], ds['name'], ds['records']),
                             tags=(ds['category'],),
                             iid=ds['url'])

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        url = sel[0]
        ds = next((d for d in ALL_DATASETS if d['url'] == url), None)
        if not ds:
            return
        self._selected_ds = ds
        self._d_name.config(text=ds['name'])
        self._d_cat.config(text=ds['category'])
        self._d_recs.config(text=f"Records: {ds['records']}")
        self._d_desc.config(text=ds['desc'])
        self._dl_status.config(text='')
        for btn in (self._open_btn, self._import_tab_btn, self._dl_btn):
            btn.config(state='normal')

    def _open_url(self):
        if self._selected_ds:
            webbrowser.open(self._selected_ds['url'])

    def _goto_import(self):
        try:
            nb = self.frame.master
            for idx in range(nb.index('end')):
                if 'Import' in nb.tab(idx, 'text'):
                    nb.select(idx)
                    return
        except Exception:
            pass
        messagebox.showinfo('Import', 'Open the "📥 Import Sources" tab to import a Kaggle CSV.')

    # ── DOWNLOAD & SAVE TO DATABASE ───────────────────────────────────────────
    def _download_and_store(self):
        if self._dl_running:
            self._log('⏳  Download already in progress...\n')
            return
        ds = self._selected_ds
        if not ds:
            return
        self._dl_running = True
        self._dl_btn.config(state='disabled', text='  ⏳  Downloading...  ')
        self._dl_status.config(text='')
        self._progress.pack(anchor='w', pady=(0, 8))
        self._progress.start(12)
        self._log(f'\n⬇️  Starting: {ds["name"]}\n')
        threading.Thread(target=self._dl_thread, args=(ds,), daemon=True).start()

    def _dl_thread(self, ds: dict):
        """
        Priority logic:
          1. If the selected URL slug matches an entry in core.kaggle_importer.DATASETS
             → use that entry directly (correct col_map, correct target_table, dedup logic)
          2. Otherwise build a generic descriptor and run via KaggleImporter
          3. Non-Kaggle URL → open browser
        """
        rows = 0
        try:
            url = ds['url']

            # Non-Kaggle (Geofabrik, data.gov.in, etc.) → open browser
            if 'kaggle.com' not in url:
                self._log('ℹ️  Non-Kaggle source — opening in browser.\n')
                webbrowser.open(url)
                self._finish_download(-1)
                return

            # Extract slug:  kaggle.com/datasets/owner/name  →  owner/name
            parts = url.rstrip('/').split('/')
            try:
                idx  = parts.index('datasets')
                slug = f"{parts[idx+1]}/{parts[idx+2]}"
            except (ValueError, IndexError):
                raise ValueError(f'Cannot parse Kaggle slug from URL: {url}')

            self._log(f'🔑  Auth via ~/.kaggle/kaggle.json\n')
            self._log(f'📡  Slug: {slug}\n')

            from core.kaggle_importer import KaggleImporter, DATASETS as _REGISTRY
            ki = KaggleImporter(self.app.db)

            # ── Priority 1: slug already in the KaggleImporter registry ─────────
            registry_entry = next(
                (d for d in _REGISTRY if d['slug'] == slug), None
            )

            if registry_entry:
                self._log(
                    f'✅  Matched registry entry: [{registry_entry["id"]}]\n'
                    f'    table → [{registry_entry["target_table"]}]  '
                    f'(using existing col_map)\n'
                )
                rows = ki.run(registry_entry['id'])

            else:
                # ── Priority 2: not in registry — build generic descriptor ───
                self._log('ℹ️  Not in registry — using generic col_map\n')
                from core import kaggle_importer as _ki_mod
                ds_def = {
                    'id':           slug.replace('/', '_'),
                    'slug':         slug,
                    'description':  ds['name'],
                    'target_table': _guess_table(ds.get('category', '')),
                    'col_map':      _generic_col_map(),
                }
                self._log(
                    f'    table → [{ds_def["target_table"]}]\n'
                )
                original = _ki_mod.DATASETS[:]
                _ki_mod.DATASETS = [ds_def]
                try:
                    result = ki.run_all()
                    rows = result.get(ds_def['id'], 0)
                finally:
                    _ki_mod.DATASETS = original

            self._log(f'✅  {rows:,} new rows saved to database.\n')

        except Exception as e:
            self._log(f'\n❌  Error: {e}\n')
            rows = -1
        finally:
            self._finish_download(rows)

    def _finish_download(self, rows: int):
        def _ui():
            self._progress.stop()
            self._progress.pack_forget()
            self._dl_running = False
            self._dl_btn.config(state='normal', text='  ⬇️  Download & Save to Database  ')
            if rows >= 0:
                self._dl_status.config(
                    text=f'✅ {rows:,} rows saved' if rows > 0 else '✅ Already up to date',
                    fg='#00ff88')
                self._log(f'\n🎉  Done — {rows:,} rows added to database.\n')
            else:
                self._dl_status.config(text='⚠️ Check log', fg='#ffd166')
        self.frame.after(0, _ui)

    # ── Duplicate check ───────────────────────────────────────────────────────
    def _run_dup_check(self):
        self._log('\n🔍  Scanning database for duplicates...\n')
        threading.Thread(target=self._dup_thread, daemon=True).start()

    def _dup_thread(self):
        try:
            # Safe import — handles stale .pyc that may not export DupReport
            try:
                from duplicate_guard import scan_all_tables, DupReport
            except ImportError:
                from duplicate_guard import scan_all_tables
                DupReport = None  # type: ignore[assignment]

            results = scan_all_tables(_db_path(self.app))
            any_found = False
            for table, report in results.items():
                # Gracefully handles both DupReport (new) and plain int (old .pyc)
                if DupReport is not None and isinstance(report, DupReport):
                    total    = report.total
                    exact    = report.exact_dups
                    semantic = report.semantic_dups
                    detail   = f'{exact} exact + {semantic} semantic'
                elif hasattr(report, 'total'):
                    total  = report.total
                    detail = f'{report.exact_dups} exact + {report.semantic_dups} semantic'
                else:
                    total  = int(report)
                    detail = f'{total} duplicates'

                if total > 0:
                    any_found = True
                    self._log(f'  ⚠️  {table}: {detail}\n')
                else:
                    self._log(f'  ✅  {table}: clean\n')

            if not any_found:
                self._log('🎉  Database is 100% duplicate-free!\n')
            self._log('\n🔍  Scan complete.\n')
        except Exception as e:
            self._log(f'\n❌  Duplicate check error: {e}\n')

    # ── AI cleaner ────────────────────────────────────────────────────────────
    def _run_ai_cleaner(self):
        self._log('\n🤖  Starting AI Cleaner on entire database...\n')
        threading.Thread(target=self._cleaner_thread, daemon=True).start()

    def _cleaner_thread(self):
        old = sys.stdout
        sys.stdout = buf = io.StringIO()
        try:
            from ai_cleaner import clean_database
            clean_database(_db_path(self.app))
        except Exception as e:
            sys.stdout = old
            self._log(f'\n❌  Error: {e}\n')
            return
        finally:
            sys.stdout = old
        for line in buf.getvalue().splitlines():
            self._log(line + '\n')
        self._log('\n✅  AI Cleaner finished.\n')

    # ── Log helpers ────────────────────────────────────────────────────────────
    def _log(self, text: str):
        def _a():
            self._log_box.config(state='normal')
            self._log_box.insert('end', text)
            self._log_box.see('end')
            self._log_box.config(state='disabled')
        self.frame.after(0, _a)

    def _clear_log(self):
        self._log_box.config(state='normal')
        self._log_box.delete('1.0', 'end')
        self._log_box.config(state='disabled')


# ── module-level helpers ──────────────────────────────────────────────────────────

def _guess_table(category: str) -> str:
    cat = category.lower()
    if 'hotel' in cat:
        return 'hotels'
    if 'restaurant' in cat or 'food' in cat:
        return 'restaurants'
    if 'flight' in cat or 'airline' in cat:
        return 'flights'
    if 'rail' in cat or 'train' in cat:
        return 'railways'
    if 'bus' in cat:
        return 'bus_routes'
    return 'tourist_places'


def _generic_col_map() -> dict:
    """Broad column mapping covering most Kaggle CSVs (fallback for non-registry datasets)."""
    return {
        'Name': 'name', 'name': 'name', 'Place': 'name', 'place': 'name',
        'Title': 'name', 'title': 'name', 'Attraction': 'name',
        'Hotel': 'name', 'Hotel Name': 'name', 'Hotel_Name': 'name',
        'City': 'city', 'city': 'city', 'Town': 'city',
        'State': 'state', 'state': 'state', 'Province': 'state',
        'Country': 'state', 'District': 'district', 'Zone': 'district',
        'Address': 'address', 'address': 'address', 'Location': 'address',
        'Latitude': 'latitude', 'latitude': 'latitude', 'Lat': 'latitude',
        'Longitude': 'longitude', 'longitude': 'longitude',
        'Lon': 'longitude', 'Long': 'longitude', 'Lng': 'longitude',
        'Category': 'category', 'category': 'category', 'Type': 'category',
        'Description': 'description', 'description': 'description',
        'Significance': 'description', 'About': 'description',
        'Rating': 'rating', 'rating': 'rating',
        'Google review rating': 'rating', 'Stars': 'rating',
        'Google_Rating': 'rating',
        'Entry_Fee': 'entry_fee', 'entry_fee': 'entry_fee',
        'Entrance Fee in INR': 'entry_fee', 'Price': 'entry_fee',
        'Timings': 'timings', 'timings': 'timings', 'Hours': 'timings',
        'Best_Time': 'best_time_to_visit',
        'Best Time to visit': 'best_time_to_visit',
        'Best_Time_to_Visit': 'best_time_to_visit',
        'best_time': 'best_time_to_visit',
        'From': 'origin', 'To': 'destination', 'Source': 'origin',
        'Destination': 'destination', 'Route': 'route_name',
        'Train No': 'train_number', 'Train Name': 'name',
        'Airline': 'airline', 'Flight': 'name',
        'Departure': 'departure_time', 'Arrival': 'arrival_time',
        'Dep_Time': 'departure_time', 'Arrival_Time': 'arrival_time',
        'Duration': 'duration', 'Distance': 'distance_km',
        'Fare': 'fare', 'Price_INR': 'fare',
        'Total_Stops': 'description', 'Additional_Info': 'description',
    }