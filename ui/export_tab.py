import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os


FORMATS = ['csv', 'json', 'excel', 'parquet', 'markdown']
TABLES = ['hotels', 'tourist_places', 'restaurants', 'routes', 'events', 'guides']


class ExportTab:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self._build()

    def _build(self):
        ttk.Label(self.frame, text='Export & Clean Data',
                  style='Title.TLabel').pack(pady=(18, 4))
        ttk.Label(self.frame, text='Clean your data, remove duplicates, and export for AI training',
                  style='Subtitle.TLabel').pack(pady=(0, 16))

        # ──────────────────────────────────────────────────────────────
        # SECTION 1: AUTOMATIC CLEAN & EXPORT
        # ──────────────────────────────────────────────────────────────
        auto_frame = ttk.Frame(self.frame, style='Card.TFrame', padding=16)
        auto_frame.pack(padx=20, fill='x', pady=10)
        ttk.Label(auto_frame, text='🚀 Automatic Pipeline (Recommended)', 
                  style='CardTitle.TLabel').pack(anchor='w', pady=(0, 8))
        ttk.Label(auto_frame, text='1. Clean database (remove duplicates & garbage)\n2. Export clean data\n3. Build AI training dataset',
                  style='Subtitle.TLabel', wraplength=600, justify='left').pack(anchor='w', pady=(0, 10))
        
        btn_frame = ttk.Frame(auto_frame)
        btn_frame.pack(fill='x', pady=8)
        ttk.Button(btn_frame, text='✨ Clean & Export All', 
                   command=self._clean_and_export_all, width=20).pack(side='left', padx=4)
        ttk.Button(btn_frame, text='🤖 Export AI Training', 
                   command=self._export_ai_training, width=20).pack(side='left', padx=4)
        ttk.Button(btn_frame, text='🧹 Clean Database Only', 
                   command=self._clean_only, width=20).pack(side='left', padx=4)

        # Status
        self.auto_status = tk.StringVar(value='')
        ttk.Label(auto_frame, textvariable=self.auto_status, 
                  style='green.TLabel', wraplength=600).pack(anchor='w', pady=(8, 0))

        # ──────────────────────────────────────────────────────────────
        # SECTION 2: MANUAL EXPORT
        # ──────────────────────────────────────────────────────────────
        manual_frame = ttk.Frame(self.frame, style='Card.TFrame', padding=16)
        manual_frame.pack(padx=20, fill='x', pady=10)
        ttk.Label(manual_frame, text='📊 Manual Export (Custom Options)', 
                  style='CardTitle.TLabel').pack(anchor='w', pady=(0, 10))

        # Format selection
        fmt_frame = ttk.Frame(manual_frame)
        fmt_frame.pack(fill='x', pady=8)
        ttk.Label(fmt_frame, text='Formats:').pack(side='left', padx=4)
        self.fmt_vars = {}
        for fmt in FORMATS:
            var = tk.BooleanVar(value=(fmt in ['csv', 'json']))
            self.fmt_vars[fmt] = var
            ttk.Checkbutton(fmt_frame, text=fmt.upper(), variable=var).pack(side='left', padx=2)

        # Table selection
        tbl_frame = ttk.Frame(manual_frame)
        tbl_frame.pack(fill='x', pady=8)
        ttk.Label(tbl_frame, text='Tables:').pack(side='left', padx=4)
        self.tbl_vars = {}
        for tbl in TABLES[:3]:  # Show first 3 in main row
            var = tk.BooleanVar(value=True)
            self.tbl_vars[tbl] = var
            ttk.Checkbutton(tbl_frame, text=tbl.replace('_', ' ').title(), variable=var).pack(side='left', padx=2)

        # More tables in second row
        tbl_frame2 = ttk.Frame(manual_frame)
        tbl_frame2.pack(fill='x', pady=4)
        for tbl in TABLES[3:]:
            var = tk.BooleanVar(value=False)
            self.tbl_vars[tbl] = var
            ttk.Checkbutton(tbl_frame2, text=tbl.replace('_', ' ').title(), variable=var).pack(side='left', padx=2)

        # Clean checkbox
        self.clean_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(manual_frame, text='✓ Export clean (deduplicated) data', 
                        variable=self.clean_var).pack(anchor='w', pady=4)

        # Output dir
        dir_frame = ttk.Frame(manual_frame)
        dir_frame.pack(fill='x', pady=8)
        ttk.Label(dir_frame, text='Output Dir:').pack(side='left', padx=4, pady=4)
        self.dir_var = tk.StringVar(value='export')
        ttk.Entry(dir_frame, textvariable=self.dir_var, width=30).pack(side='left', padx=4, fill='x', expand=True)

        # Export button
        ttk.Button(manual_frame, text='📤  Export', 
                   command=self._export).pack(pady=10)

        # ──────────────────────────────────────────────────────────────
        # SECTION 3: LOG & FILES
        # ──────────────────────────────────────────────────────────────
        ttk.Label(self.frame, text='📋 Export Log:', style='CardTitle.TLabel').pack(
            pady=(16, 6), anchor='w', padx=20)
        
        self.file_list = tk.Listbox(self.frame, bg='#16213e', fg='#00ff88',
                                     font=('Consolas', 9), height=12)
        self.file_list.pack(fill='both', expand=True, padx=20, pady=(0, 14))

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.frame, orient='vertical', command=self.file_list.yview)
        scrollbar.pack(side='right', fill='y', padx=(0, 14), pady=(0, 14))
        self.file_list.config(yscrollcommand=scrollbar.set)

    def _clean_only(self):
        """Clean database only"""
        self.auto_status.set('Cleaning database...')
        self.file_list.delete(0, 'end')
        
        def run():
            try:
                from core.db_cleaner import DatabaseCleaner
                cleaner = DatabaseCleaner(self.app.db)
                report = cleaner.run()
                
                self.file_list.insert('end', '✅ DATABASE CLEANING COMPLETE')
                self.file_list.insert('end', '')
                for line in report.summary().split('\n'):
                    self.file_list.insert('end', line)
                
                self.auto_status.set('✅ Database cleaned successfully!')
            except Exception as e:
                self.file_list.insert('end', f'❌ Error: {e}')
                self.auto_status.set(f'❌ Error: {str(e)[:100]}')
        
        threading.Thread(target=run, daemon=True).start()

    def _clean_and_export_all(self):
        """Clean database and export all data"""
        self.auto_status.set('Starting clean & export pipeline...')
        self.file_list.delete(0, 'end')
        self.file_list.insert('end', '⏳ Step 1: Cleaning database...')
        self.frame.update()
        
        def run():
            try:
                from core.db_cleaner import DatabaseCleaner
                from core.exporter import Exporter
                
                # Step 1: Clean
                self.file_list.insert('end', '⏳ Step 1: Cleaning database...')
                self.frame.update()
                cleaner = DatabaseCleaner(self.app.db)
                report = cleaner.run()
                self.file_list.insert('end', '✅ Database cleaned')
                self.file_list.insert('end', f'   - Garbage removed: {sum(report.garbage_removed.values())}')
                self.file_list.insert('end', f'   - Duplicates merged: {sum(report.duplicates_merged.values())}')
                
                # Step 2: Export clean data
                self.file_list.insert('end', '⏳ Step 2: Exporting clean data...')
                self.frame.update()
                exporter = Exporter(self.app.db, output_dir='export')
                results = exporter.export_all(formats=['jsonl', 'json', 'csv'], clean=True)
                
                self.file_list.insert('end', '✅ Clean data exported')
                for table, exports in results.items():
                    for fmt, path in exports.items():
                        if path:
                            self.file_list.insert('end', f'   - {path}')
                
                # Step 3: Export AI training
                self.file_list.insert('end', '⏳ Step 3: Building AI training dataset...')
                self.frame.update()
                ai_results = exporter.export_all_ai_training()
                self.file_list.insert('end', '✅ AI training data exported')
                for fmt, path in ai_results.items():
                    self.file_list.insert('end', f'   - {path}')
                
                self.file_list.insert('end', '')
                self.file_list.insert('end', '✅ PIPELINE COMPLETE!')
                self.file_list.insert('end', f'   Output: {os.path.abspath("export")}')
                
                self.auto_status.set('✅ Complete! Data cleaned and exported for AI training')
                
            except Exception as e:
                self.file_list.insert('end', f'❌ Error: {e}')
                self.auto_status.set(f'❌ Error: {str(e)[:100]}')
        
        threading.Thread(target=run, daemon=True).start()

    def _export_ai_training(self):
        """Export data for AI training"""
        self.auto_status.set('Building AI training dataset...')
        self.file_list.delete(0, 'end')
        
        def run():
            try:
                from core.exporter import Exporter
                exporter = Exporter(self.app.db, output_dir='export')
                
                self.file_list.insert('end', '⏳ Building AI training dataset...')
                self.frame.update()
                
                results = exporter.export_all_ai_training()
                
                self.file_list.insert('end', '✅ AI TRAINING DATA EXPORTED')
                self.file_list.insert('end', '')
                for fmt, path in results.items():
                    self.file_list.insert('end', f'✅ {fmt.upper()}: {path}')
                
                self.file_list.insert('end', '')
                self.file_list.insert('end', 'Ready for fine-tuning with:')
                self.file_list.insert('end', '  • Llama2, Mistral, etc.')
                self.file_list.insert('end', '  • Hugging Face transformers')
                self.file_list.insert('end', '  • LlamaIndex, LangChain')
                
                self.auto_status.set('✅ AI training data ready!')
                
            except Exception as e:
                self.file_list.insert('end', f'❌ Error: {e}')
                self.auto_status.set(f'❌ Error: {str(e)[:100]}')
        
        threading.Thread(target=run, daemon=True).start()

    def _export(self):
        """Manual export with custom options"""
        formats = [f for f, v in self.fmt_vars.items() if v.get()]
        tables = [t for t, v in self.tbl_vars.items() if v.get()]
        if not formats:
            messagebox.showwarning('No Format', 'Select at least one export format.')
            return
        if not tables:
            messagebox.showwarning('No Table', 'Select at least one table to export.')
            return

        output_dir = self.dir_var.get().strip() or 'export'
        clean = self.clean_var.get()
        self.auto_status.set('Exporting...')
        self.file_list.delete(0, 'end')

        def run():
            from core.exporter import Exporter
            exp = Exporter(self.app.db, output_dir=output_dir)
            
            count = 0
            for table in tables:
                for fmt in formats:
                    try:
                        if fmt == 'csv':
                            path = exp.export_clean_csv(table) if clean else exp.export_csv(table)
                        elif fmt == 'json':
                            path = exp.export_clean_json(table) if clean else exp.export_json(table)
                        elif fmt == 'excel':
                            path = exp.export_excel(table)
                        elif fmt == 'parquet':
                            path = exp.export_parquet(table)
                        elif fmt == 'markdown':
                            path = exp.export_markdown(table)
                        else:
                            continue
                        if path:
                            self.file_list.insert('end', f'✅ {path}')
                            count += 1
                    except Exception as e:
                        self.file_list.insert('end', f'❌ {table}/{fmt}: {e}')
            
            self.auto_status.set(f'✅ Export complete! {count} files saved to: {os.path.abspath(output_dir)}')

        threading.Thread(target=run, daemon=True).start()

    def export_clean_csv(self, table):
        """Placeholder - exporter has this method"""
        pass

