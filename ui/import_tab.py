import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading


INDIA_AREAS = [
    "West Bengal", "Rajasthan", "Kerala", "Goa", "Himachal Pradesh",
    "Uttarakhand", "Tamil Nadu", "Gujarat", "Maharashtra", "Karnataka",
    "Odisha", "Assam", "Sikkim", "Meghalaya", "Andaman and Nicobar Islands",
    "Delhi", "Uttar Pradesh", "Madhya Pradesh", "Bihar", "Punjab",
    "Haryana", "Telangana", "Andhra Pradesh", "Jammu and Kashmir",
    "Arunachal Pradesh", "Mizoram", "Manipur", "Nagaland", "Tripura",
    "Chhattisgarh", "Jharkhand", "Lakshadweep", "Puducherry"
]

INDIA_CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Kolkata",
    "Pune", "Ahmedabad", "Jaipur", "Surat", "Lucknow", "Kanpur",
    "Nagpur", "Indore", "Bhopal", "Patna", "Vadodara", "Coimbatore",
    "Agra", "Varanasi", "Udaipur", "Jodhpur", "Kochi", "Goa",
    "Shimla", "Manali", "Darjeeling", "Ooty", "Rishikesh", "Haridwar",
    "Amritsar", "Chandigarh", "Mysuru", "Visakhapatnam", "Guwahati",
]

HOTEL_PLATFORMS = [
    'MakeMyTrip', 'Goibibo', 'Yatra', 'Booking.com', 'Agoda', 'Cleartrip'
]

DEFAULT_WIKI_QUERIES = """Darjeeling
Digha Beach
Sundarbans National Park
Hawah Mahal Jaipur
Taj Mahal Agra
Red Fort Delhi
Golden Temple Amritsar
Meenakshi Temple Madurai
Hampi Karnataka
Ajanta Caves
Ellora Caves
Konark Sun Temple
Khajuraho Temples
Gateway of India Mumbai
Victoria Memorial Kolkata
Dal Lake Srinagar
Manali
Shimla
Munnar Kerala
Alleppey Backwaters
Ooty Tamil Nadu
Gangtok Sikkim
Leh Ladakh
Coorg Karnataka
Pondicherry
Varanasi Ghats
Rishikesh Uttarakhand
Haridwar
Jaisalmer Fort
Udaipur Lake City"""

DEFAULT_RSS_FEEDS = """https://www.holidify.com/feed
https://www.thrillophilia.com/blog/feed
https://traveltriangle.com/blog/feed
https://www.goibibo.com/blog/feed"""

KAGGLE_DATASETS = [
    {'id': 'tourist_attractions', 'label': '🏛  Indian Tourist Attractions (~500 places)', 'description': 'dakshineswarm/indian-tourist-attraction-dataset'},
    {'id': 'top_places',          'label': '📍  Top Indian Places to Visit (Jan 2026)',     'description': 'dhrubangtalukdar/top-indian-places-to-visit-indian-tourism'},
    {'id': 'most_traveled_cities','label': '🏙  Most Traveled Cities in India (2025)',      'description': 'kirtandwivedi02/most-traveled-cities-in-india'},
    {'id': 'india_tourism_stats', 'label': '📊  India Tourism Statistics',                    'description': 'rajkumarl/india-tourism-statistics'},
    {'id': 'hotel_details',       'label': '🏨  Hotel Details Dataset — India',              'description': 'nehaprabhakar/hotel-details-dataset-india'},
    {'id': 'google_places_rating','label': '⭐  Google Places Rating for Indian Cities',       'description': 'chetanborse/google-places-rating-for-indian-cities'},
    {'id': 'india_tourism_datasets','label':'🗂  India Tourism Datasets (multi-file bundle)', 'description': 'rakkeshcase/india-tourism-datasets'},
]


class ImportTab:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self._build()

    def _build(self):
        ttk.Label(self.frame, text='Import Sources',
                  style='Title.TLabel').pack(pady=(18, 4))
        ttk.Label(self.frame,
                  text='Import data from OSM, Wikipedia, RSS, Kaggle & Hotel Portals',
                  style='Subtitle.TLabel').pack(pady=(0, 10))

        inner = ttk.Notebook(self.frame)
        inner.pack(fill='both', expand=True, padx=20, pady=6)

        self._build_osm_panel(inner)
        self._build_wiki_panel(inner)
        self._build_rss_panel(inner)
        self._build_kaggle_panel(inner)
        self._build_hotel_portals_panel(inner)   # ← NEW

        ttk.Label(self.frame, text='Import Log:', style='CardTitle.TLabel').pack(
            pady=(8, 2), anchor='w', padx=22)
        self.log_box = scrolledtext.ScrolledText(
            self.frame, height=8, bg='#0a0a1a', fg='#00ff88',
            font=('Consolas', 9), state='disabled')
        self.log_box.pack(fill='x', padx=22, pady=(0, 12))

    # ---- OSM Panel ----
    def _build_osm_panel(self, notebook):
        frm = ttk.Frame(notebook, padding=16)
        notebook.add(frm, text='  🗺 OpenStreetMap  ')
        ttk.Label(frm, text='OSM Overpass API - Hotels, attractions, restaurants',
                  style='CardSub.TLabel').grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 10))
        ttk.Label(frm, text='Select Area:').grid(row=1, column=0, sticky='w', padx=4)
        self.osm_area_var = tk.StringVar(value='West Bengal')
        ttk.Combobox(frm, textvariable=self.osm_area_var, values=INDIA_AREAS,
                     state='readonly', width=28).grid(row=1, column=1, padx=6, pady=4, sticky='w')
        ttk.Label(frm, text='Custom Area:').grid(row=2, column=0, sticky='w', padx=4)
        self.osm_custom_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.osm_custom_var, width=30).grid(row=2, column=1, padx=6, pady=4, sticky='w')
        ttk.Label(frm, text='(overrides dropdown)', style='CardSub.TLabel').grid(row=2, column=2, sticky='w')
        ttk.Label(frm, text='Record Limit:').grid(row=3, column=0, sticky='w', padx=4)
        self.osm_limit_var = tk.StringVar(value='200')
        ttk.Entry(frm, textvariable=self.osm_limit_var, width=10).grid(row=3, column=1, padx=6, pady=4, sticky='w')
        self.osm_status_var = tk.StringVar(value='')
        ttk.Label(frm, textvariable=self.osm_status_var, style='green.TLabel').grid(row=10, column=0, columnspan=3, pady=6)
        ttk.Button(frm, text='▶  Start OSM Import', command=self._run_osm).grid(
            row=11, column=0, columnspan=2, pady=10, sticky='w', padx=4)

    # ---- Wikipedia Panel ----
    def _build_wiki_panel(self, notebook):
        frm = ttk.Frame(notebook, padding=16)
        notebook.add(frm, text='  📖 Wikipedia  ')
        ttk.Label(frm, text='Wikipedia API - Summaries, coordinates for places & guides',
                  style='CardSub.TLabel').pack(anchor='w', pady=(0, 8))
        ttk.Label(frm, text='Queries (one per line):', style='CardTitle.TLabel').pack(anchor='w')
        self.wiki_text = scrolledtext.ScrolledText(
            frm, height=10, bg='#16213e', fg='white', insertbackground='white',
            font=('Consolas', 10), wrap='word')
        self.wiki_text.pack(fill='both', expand=True, pady=6)
        self.wiki_text.insert('end', DEFAULT_WIKI_QUERIES)
        self.wiki_status_var = tk.StringVar(value='')
        ttk.Label(frm, textvariable=self.wiki_status_var, style='green.TLabel').pack(pady=4)
        ttk.Button(frm, text='▶  Start Wikipedia Import', command=self._run_wikipedia).pack(pady=8, anchor='w')

    # ---- RSS Panel ----
    def _build_rss_panel(self, notebook):
        frm = ttk.Frame(notebook, padding=16)
        notebook.add(frm, text='  📡 RSS Feeds  ')
        ttk.Label(frm, text='RSS + newspaper3k - Fetch travel articles',
                  style='CardSub.TLabel').pack(anchor='w', pady=(0, 8))
        ttk.Label(frm, text='RSS Feed URLs (one per line):', style='CardTitle.TLabel').pack(anchor='w')
        self.rss_text = scrolledtext.ScrolledText(
            frm, height=8, bg='#16213e', fg='white', insertbackground='white',
            font=('Consolas', 10), wrap='word')
        self.rss_text.pack(fill='both', expand=True, pady=6)
        self.rss_text.insert('end', DEFAULT_RSS_FEEDS)
        row = ttk.Frame(frm)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text='Articles per feed:').pack(side='left', padx=4)
        self.rss_limit_var = tk.StringVar(value='10')
        ttk.Entry(row, textvariable=self.rss_limit_var, width=8).pack(side='left', padx=4)
        self.rss_status_var = tk.StringVar(value='')
        ttk.Label(frm, textvariable=self.rss_status_var, style='green.TLabel').pack(pady=4)
        ttk.Button(frm, text='▶  Start RSS Import', command=self._run_rss).pack(pady=8, anchor='w')

    # ---- Kaggle Panel ----
    def _build_kaggle_panel(self, notebook):
        frm = ttk.Frame(notebook, padding=16)
        notebook.add(frm, text='  📦 Kaggle Datasets  ')
        ttk.Label(frm, text='Download → Clean → Save to Database  (requires ~/.kaggle/kaggle.json)',
                  style='CardSub.TLabel').pack(anchor='w', pady=(0, 10))
        ttk.Label(frm, text='Select datasets to import:', style='CardTitle.TLabel').pack(anchor='w', pady=(0, 4))
        checkbox_frame = ttk.Frame(frm)
        checkbox_frame.pack(fill='x', padx=4, pady=(0, 10))
        self._kaggle_vars = {}
        for ds in KAGGLE_DATASETS:
            var = tk.BooleanVar(value=True)
            self._kaggle_vars[ds['id']] = var
            row = ttk.Frame(checkbox_frame)
            row.pack(fill='x', pady=2)
            ttk.Checkbutton(row, text=ds['label'], variable=var).pack(side='left', padx=4)
            ttk.Label(row, text=f"  ({ds['description']})", style='CardSub.TLabel').pack(side='left')
        btn_row = ttk.Frame(frm)
        btn_row.pack(fill='x', pady=(0, 8))
        ttk.Button(btn_row, text='✅ Select All',
                   command=lambda: [v.set(True) for v in self._kaggle_vars.values()]).pack(side='left', padx=4)
        ttk.Button(btn_row, text='☐ Deselect All',
                   command=lambda: [v.set(False) for v in self._kaggle_vars.values()]).pack(side='left', padx=4)
        self.kaggle_status_var = tk.StringVar(value='Ready')
        ttk.Label(frm, textvariable=self.kaggle_status_var, style='green.TLabel', wraplength=700).pack(anchor='w', pady=(4, 2))
        self.kaggle_progress = ttk.Progressbar(frm, mode='indeterminate', length=500)
        self.kaggle_progress.pack(fill='x', padx=4, pady=(0, 8))
        ttk.Label(frm, text='Kaggle Log:', style='CardTitle.TLabel').pack(anchor='w')
        self.kaggle_log = scrolledtext.ScrolledText(
            frm, height=8, bg='#0a0a1a', fg='#20d4ff', font=('Consolas', 9), state='disabled')
        self.kaggle_log.pack(fill='both', expand=True, pady=4)
        action_row = ttk.Frame(frm)
        action_row.pack(fill='x', pady=(6, 2))
        ttk.Button(action_row, text='🚀  Download → Clean → Save to DB',
                   command=self._run_kaggle_import).pack(side='left', padx=4)
        ttk.Button(action_row, text='🗑  Clear Log',
                   command=self._clear_kaggle_log).pack(side='left', padx=4)

    # ---- Hotel Portals Panel (NEW) ----
    def _build_hotel_portals_panel(self, notebook):
        frm = ttk.Frame(notebook, padding=16)
        notebook.add(frm, text='  🏨 Hotel Portals  ')

        ttk.Label(
            frm,
            text='Scrape hotel listings from MakeMyTrip, Goibibo, Yatra, Booking.com, Agoda & Cleartrip',
            style='CardSub.TLabel'
        ).pack(anchor='w', pady=(0, 10))

        # City + State row
        row1 = ttk.Frame(frm)
        row1.pack(fill='x', pady=4)
        ttk.Label(row1, text='City:').pack(side='left', padx=4)
        self.hotel_city_var = tk.StringVar(value='Mumbai')
        city_cb = ttk.Combobox(row1, textvariable=self.hotel_city_var,
                               values=INDIA_CITIES, width=22)
        city_cb.pack(side='left', padx=4)
        ttk.Label(row1, text='  State (optional):').pack(side='left', padx=4)
        self.hotel_state_var = tk.StringVar(value='Maharashtra')
        ttk.Combobox(row1, textvariable=self.hotel_state_var,
                     values=INDIA_AREAS, width=22).pack(side='left', padx=4)

        # Pages per platform
        row2 = ttk.Frame(frm)
        row2.pack(fill='x', pady=4)
        ttk.Label(row2, text='Pages per platform:').pack(side='left', padx=4)
        self.hotel_pages_var = tk.StringVar(value='2')
        ttk.Spinbox(row2, textvariable=self.hotel_pages_var, from_=1, to=10,
                    width=6).pack(side='left', padx=4)
        ttk.Label(row2, text='(more pages = more hotels, slower)',
                  style='CardSub.TLabel').pack(side='left', padx=8)

        # Platform checkboxes
        ttk.Label(frm, text='Platforms to scrape:', style='CardTitle.TLabel').pack(
            anchor='w', pady=(10, 4))
        plat_frame = ttk.Frame(frm)
        plat_frame.pack(fill='x', padx=4, pady=(0, 8))
        self._hotel_platform_vars = {}
        PLATFORM_ICONS = {
            'MakeMyTrip':  '🔴',
            'Goibibo':     '🟢',
            'Yatra':       '🔵',
            'Booking.com': '🔵',
            'Agoda':       '🟠',
            'Cleartrip':   '🟡',
        }
        for i, platform in enumerate(HOTEL_PLATFORMS):
            var = tk.BooleanVar(value=True)
            self._hotel_platform_vars[platform] = var
            col = i % 3
            row_idx = i // 3
            ttk.Checkbutton(
                plat_frame,
                text=f"{PLATFORM_ICONS.get(platform, '🏨')}  {platform}",
                variable=var
            ).grid(row=row_idx, column=col, sticky='w', padx=12, pady=3)

        # Select / Deselect All
        sb_row = ttk.Frame(frm)
        sb_row.pack(fill='x', pady=(0, 8))
        ttk.Button(sb_row, text='✅ All',
                   command=lambda: [v.set(True) for v in self._hotel_platform_vars.values()]
                   ).pack(side='left', padx=4)
        ttk.Button(sb_row, text='☐ None',
                   command=lambda: [v.set(False) for v in self._hotel_platform_vars.values()]
                   ).pack(side='left', padx=4)

        # Status + progress
        self.hotel_status_var = tk.StringVar(value='Ready — select a city and click Start')
        ttk.Label(frm, textvariable=self.hotel_status_var,
                  style='green.TLabel', wraplength=700).pack(anchor='w', pady=(4, 2))
        self.hotel_progress = ttk.Progressbar(frm, mode='indeterminate', length=500)
        self.hotel_progress.pack(fill='x', padx=4, pady=(0, 8))

        # Log
        ttk.Label(frm, text='Hotel Scrape Log:', style='CardTitle.TLabel').pack(anchor='w')
        self.hotel_log = scrolledtext.ScrolledText(
            frm, height=9, bg='#0a0a1a', fg='#ffcc44',
            font=('Consolas', 9), state='disabled')
        self.hotel_log.pack(fill='both', expand=True, pady=4)

        # Buttons
        btn_row = ttk.Frame(frm)
        btn_row.pack(fill='x', pady=(6, 2))
        ttk.Button(
            btn_row,
            text='🚀  Start Hotel Scrape → Save to DB',
            command=self._run_hotel_portals
        ).pack(side='left', padx=4)
        ttk.Button(
            btn_row, text='🗑  Clear Log',
            command=lambda: self._hlog_clear()
        ).pack(side='left', padx=4)

        ttk.Label(
            frm,
            text='💡 Duplicate hotels from multiple platforms are auto-merged (not duplicated)',
            style='CardSub.TLabel'
        ).pack(anchor='w', pady=(8, 2))

    # ---- Log helpers ----
    def _log(self, msg: str):
        self.log_box.config(state='normal')
        self.log_box.insert('end', msg + '\n')
        self.log_box.see('end')
        self.log_box.config(state='disabled')

    def _klog(self, msg: str):
        self.kaggle_log.config(state='normal')
        self.kaggle_log.insert('end', msg + '\n')
        self.kaggle_log.see('end')
        self.kaggle_log.config(state='disabled')
        self._log(f'[Kaggle] {msg}')

    def _clear_kaggle_log(self):
        self.kaggle_log.config(state='normal')
        self.kaggle_log.delete('1.0', 'end')
        self.kaggle_log.config(state='disabled')

    def _hlog(self, msg: str):
        self.hotel_log.config(state='normal')
        self.hotel_log.insert('end', msg + '\n')
        self.hotel_log.see('end')
        self.hotel_log.config(state='disabled')
        self._log(f'[Hotels] {msg}')

    def _hlog_clear(self):
        self.hotel_log.config(state='normal')
        self.hotel_log.delete('1.0', 'end')
        self.hotel_log.config(state='disabled')

    # ---- Runners ----
    def _run_osm(self):
        area = self.osm_custom_var.get().strip() or self.osm_area_var.get()
        try:
            limit = int(self.osm_limit_var.get())
        except ValueError:
            limit = 200
        self.osm_status_var.set('Running...')
        self._log(f'[OSM] Importing: {area} (limit={limit})')

        def run():
            from core.import_pipeline import ImportPipeline
            p = ImportPipeline(self.app.db, on_status=lambda m: (self._log(m), self.osm_status_var.set(m)))
            counts = p.import_osm(area, limit=limit)
            msg = f'✅ OSM Done: {sum(counts.values())} records'
            self.osm_status_var.set(msg)
            self._log(msg)
        threading.Thread(target=run, daemon=True).start()

    def _run_wikipedia(self):
        queries = [q.strip() for q in self.wiki_text.get('1.0', 'end').splitlines() if q.strip()]
        if not queries:
            messagebox.showwarning('No Queries', 'Enter at least one Wikipedia query.')
            return
        self.wiki_status_var.set('Running...')

        def run():
            from core.import_pipeline import ImportPipeline
            p = ImportPipeline(self.app.db, on_status=lambda m: (self._log(m), self.wiki_status_var.set(m)))
            counts = p.import_wikipedia(queries)
            msg = f'✅ Wikipedia Done: {counts["tourist_places"]} places + {counts["guides"]} guides'
            self.wiki_status_var.set(msg)
            self._log(msg)
        threading.Thread(target=run, daemon=True).start()

    def _run_rss(self):
        feeds = [f.strip() for f in self.rss_text.get('1.0', 'end').splitlines() if f.strip()]
        if not feeds:
            messagebox.showwarning('No Feeds', 'Enter at least one RSS feed URL.')
            return
        try:
            limit = int(self.rss_limit_var.get())
        except ValueError:
            limit = 10
        self.rss_status_var.set('Running...')

        def run():
            from core.import_pipeline import ImportPipeline
            p = ImportPipeline(self.app.db, on_status=lambda m: (self._log(m), self.rss_status_var.set(m)))
            counts = p.import_rss(feeds=feeds, limit_per_feed=limit)
            msg = f'✅ RSS Done: {counts["guides"]} articles'
            self.rss_status_var.set(msg)
            self._log(msg)
        threading.Thread(target=run, daemon=True).start()

    def _run_kaggle_import(self):
        selected = [ds_id for ds_id, var in self._kaggle_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning('No Datasets', 'Select at least one dataset.')
            return
        self.kaggle_status_var.set(f'⏳ Downloading {len(selected)} dataset(s)...')
        self.kaggle_progress.start(12)

        def run():
            try:
                from core.kaggle_importer import KaggleImporter
                ki = KaggleImporter(self.app.db)
                total = 0
                for ds_id in selected:
                    self._klog(f'⬇ {ds_id}')
                    try:
                        n = ki.run(ds_id)
                        self._klog(f'  ✅ {ds_id} → {n} records')
                        total += n
                    except Exception as e:
                        self._klog(f'  ❌ {ds_id}: {e}')
                self.kaggle_status_var.set(f'🎉 Done — {total} records added')
                self._klog(f'🎉 Total: {total} records')
                try:
                    self.app.refresh_dashboard()
                except Exception:
                    pass
            except Exception as e:
                self.kaggle_status_var.set(f'❌ {e}')
            finally:
                self.kaggle_progress.stop()
        threading.Thread(target=run, daemon=True).start()

    def _run_hotel_portals(self):
        city      = self.hotel_city_var.get().strip()
        state     = self.hotel_state_var.get().strip()
        platforms = [p for p, v in self._hotel_platform_vars.items() if v.get()]
        try:
            pages = int(self.hotel_pages_var.get())
        except ValueError:
            pages = 2

        if not city:
            messagebox.showwarning('No City', 'Please enter a city name.')
            return
        if not platforms:
            messagebox.showwarning('No Platforms', 'Select at least one platform.')
            return

        self.hotel_status_var.set(f'⏳ Scraping {len(platforms)} platforms for {city}...')
        self.hotel_progress.start(12)
        self._hlog(f'Starting hotel scrape: {city} | platforms: {", ".join(platforms)}')

        def run():
            try:
                from core.import_pipeline import ImportPipeline
                p = ImportPipeline(
                    self.app.db,
                    on_status=lambda m: (
                        self._hlog(m),
                        self.hotel_status_var.set(m)
                    )
                )
                counts = p.import_hotels_from_portals(
                    city=city, state=state,
                    platforms=platforms, pages=pages
                )
                saved = counts.get('hotels_saved', 0)
                raw   = counts.get('hotels_raw', 0)
                msg   = f'🎉 Done — {raw} raw → {saved} new hotels saved for {city}'
                self.hotel_status_var.set(msg)
                self._hlog(msg)
                self._hlog('💡 Platform breakdown:')
                for plat in platforms:
                    n = counts.get(plat, 0)
                    self._hlog(f'  {plat}: {n} hotels found')
                try:
                    self.app.refresh_dashboard()
                except Exception:
                    pass
            except Exception as e:
                self.hotel_status_var.set(f'❌ Error: {e}')
                self._hlog(f'❌ Error: {e}')
            finally:
                self.hotel_progress.stop()

        threading.Thread(target=run, daemon=True).start()