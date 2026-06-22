import os
import json
import csv
from loguru import logger
from core.database import Database
from core.cleaner import DataCleaner

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class Exporter:
    def __init__(self, db: Database, output_dir: str = "export"):
        self.db = db
        self.output_dir = output_dir
        self.cleaner = DataCleaner()
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "ai_training"), exist_ok=True)

    def _get_data(self, table: str, limit: int = 100000) -> list:
        return self.db.get_all(table, limit=limit)

    def export_csv(self, table: str) -> str:
        data = self._get_data(table)
        if not data:
            logger.warning(f"No data in {table}")
            return ''
        path = os.path.join(self.output_dir, f"{table}.csv")
        if PANDAS_AVAILABLE:
            import pandas as pd
            pd.DataFrame(data).to_csv(path, index=False, encoding='utf-8')
        else:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
        logger.info(f"Exported {len(data)} records to {path}")
        return path

    def export_json(self, table: str) -> str:
        data = self._get_data(table)
        path = os.path.join(self.output_dir, f"{table}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Exported {len(data)} records to {path}")
        return path

    def export_clean_csv(self, table: str) -> str:
        """Export cleaned data as CSV"""
        data = self._get_data(table)
        if not data:
            logger.warning(f"No data in {table}")
            return ''
        
        clean_data = []
        for record in data:
            if table == 'hotels':
                cleaned = self.cleaner.clean_hotel(record)
            elif table == 'tourist_places':
                cleaned = self.cleaner.clean_tourist_place(record)
            elif table == 'restaurants':
                cleaned = self.cleaner.clean_restaurant(record)
            else:
                cleaned = record
            
            if cleaned and any(cleaned.get(k) for k in ['name', 'description']):
                clean_data.append(cleaned)
        
        path = os.path.join(self.output_dir, f"{table}_clean.csv")
        if PANDAS_AVAILABLE:
            import pandas as pd
            pd.DataFrame(clean_data).to_csv(path, index=False, encoding='utf-8')
        else:
            if clean_data:
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=clean_data[0].keys())
                    writer.writeheader()
                    writer.writerows(clean_data)
        
        logger.info(f"Exported {len(clean_data)} cleaned records to {path}")
        return path



    def export_clean_json(self, table: str) -> str:
        """Export cleaned data as JSON"""
        data = self._get_data(table)
        if not data:
            logger.warning(f"No data in {table}")
            return ''
        
        clean_data = []
        for record in data:
            if table == 'hotels':
                cleaned = self.cleaner.clean_hotel(record)
            elif table == 'tourist_places':
                cleaned = self.cleaner.clean_tourist_place(record)
            elif table == 'restaurants':
                cleaned = self.cleaner.clean_restaurant(record)
            else:
                cleaned = record
            
            if cleaned and any(cleaned.get(k) for k in ['name', 'description']):
                clean_data.append(cleaned)
        
        path = os.path.join(self.output_dir, f"{table}_clean.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Exported {len(clean_data)} cleaned records to {path}")
        return path

    def export_jsonl(self, table: str, clean: bool = False) -> str:
        """Export data as JSONL (one JSON per line) - ideal for AI training"""
        data = self._get_data(table)
        if not data:
            logger.warning(f"No data in {table}")
            return ''
        
        processed_data = []
        for record in data:
            if clean:
                if table == 'hotels':
                    cleaned = self.cleaner.clean_hotel(record)
                elif table == 'tourist_places':
                    cleaned = self.cleaner.clean_tourist_place(record)
                elif table == 'restaurants':
                    cleaned = self.cleaner.clean_restaurant(record)
                else:
                    cleaned = record
            else:
                cleaned = record
            
            if cleaned and any(cleaned.get(k) for k in ['name', 'description']):
                processed_data.append(cleaned)
        
        suffix = "_clean" if clean else ""
        path = os.path.join(self.output_dir, f"{table}{suffix}.jsonl")
        with open(path, 'w', encoding='utf-8') as f:
            for item in processed_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        logger.info(f"Exported {len(processed_data)} JSONL records to {path}")
        return path

    def export_excel(self, table: str) -> str:
        if not PANDAS_AVAILABLE:
            logger.error("Pandas required for Excel export")
            return ''
        import pandas as pd
        data = self._get_data(table)
        path = os.path.join(self.output_dir, f"{table}.xlsx")
        pd.DataFrame(data).to_excel(path, index=False)
        logger.info(f"Exported to {path}")
        return path

    def export_parquet(self, table: str) -> str:
        if not PANDAS_AVAILABLE:
            logger.error("Pandas required for Parquet export")
            return ''
        import pandas as pd
        data = self._get_data(table)
        path = os.path.join(self.output_dir, f"{table}.parquet")
        pd.DataFrame(data).to_parquet(path, index=False)
        logger.info(f"Exported to {path}")
        return path

    def export_markdown(self, table: str) -> str:
        data = self._get_data(table)
        if not data:
            return ''
        path = os.path.join(self.output_dir, f"{table}.md")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"# {table.replace('_', ' ').title()}\n\n")
            keys = list(data[0].keys())
            f.write('| ' + ' | '.join(keys) + ' |\n')
            f.write('| ' + ' | '.join(['---'] * len(keys)) + ' |\n')
            for row in data[:500]:
                vals = [str(row.get(k, '')).replace('|', ',')[:80] for k in keys]
                f.write('| ' + ' | '.join(vals) + ' |\n')
        logger.info(f"Exported Markdown to {path}")
        return path

    def build_training_dataset(self, dataset_limit: int = 10000) -> list:
        """Build comprehensive training dataset for AI models"""
        dataset = []
        
        # Hotels training data
        hotels = self._get_data('hotels', limit=dataset_limit)
        for h in hotels:
            if not h.get('name') or not h.get('description'):
                continue
            dataset.append({
                "type": "hotel_info",
                "instruction": f"Tell me about {h['name']} hotel",
                "input": "",
                "output": f"{h.get('name', '')}\nCity: {h.get('city', '')}\nState: {h.get('state', '')}\n{h.get('description', '')}\nRating: {h.get('rating', 'N/A')}"
            })
            
            if h.get('city'):
                dataset.append({
                    "type": "hotel_city_query",
                    "instruction": f"Best hotels in {h['city']}",
                    "input": "",
                    "output": f"{h.get('name', '')} - {h.get('description', '')}. Price: ₹{h.get('price_min', 'N/A')} - ₹{h.get('price_max', 'N/A')}"
                })
        
        # Tourist Places training data
        places = self._get_data('tourist_places', limit=dataset_limit)
        for p in places:
            if not p.get('name') or not p.get('description'):
                continue
            dataset.append({
                "type": "place_info",
                "instruction": f"Tell me about {p['name']}",
                "input": "",
                "output": f"{p.get('name', '')}\nLocation: {p.get('city', '')}, {p.get('state', '')}\n{p.get('description', '')}\nBest Time: {p.get('best_time_to_visit', 'N/A')}"
            })
            
            if p.get('city'):
                dataset.append({
                    "type": "place_city_query",
                    "instruction": f"Places to visit in {p['city']}",
                    "input": "",
                    "output": f"{p.get('name', '')} - {p.get('description', '')}"
                })
        
        # Restaurants training data
        restaurants = self._get_data('restaurants', limit=dataset_limit)
        for r in restaurants:
            if not r.get('name') or not r.get('city'):
                continue
            dataset.append({
                "type": "restaurant_info",
                "instruction": f"Best restaurants in {r['city']}",
                "input": "",
                "output": f"{r['name']} ({r.get('cuisine', 'Indian')} cuisine) - {r.get('description', 'Popular dining destination')}"
            })
        
        logger.info(f"Built training dataset with {len(dataset)} samples")
        return dataset

    def save_training_data(self, dataset: list, format: str = "jsonl") -> str:
        """Save training dataset in specified format"""
        os.makedirs(os.path.join(self.output_dir, "ai_training"), exist_ok=True)
        
        if format == "jsonl":
            path = os.path.join(self.output_dir, "ai_training", "training_data.jsonl")
            with open(path, 'w', encoding='utf-8') as f:
                for item in dataset:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
        elif format == "json":
            path = os.path.join(self.output_dir, "ai_training", "training_data.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, ensure_ascii=False, indent=2)
        elif format == "csv" and PANDAS_AVAILABLE:
            import pandas as pd
            path = os.path.join(self.output_dir, "ai_training", "training_data.csv")
            pd.DataFrame(dataset).to_csv(path, index=False, encoding='utf-8')
        else:
            logger.error(f"Unsupported format: {format}")
            return ''
        
        logger.info(f"Saved training data ({format}) to {path}")
        return path

    def export_all(self, formats: list = None, clean: bool = True) -> dict:
        if formats is None:
            formats = ['csv', 'json', 'jsonl']
        tables = ['hotels', 'tourist_places', 'restaurants', 'routes', 'events', 'guides']
        results = {}
        
        for table in tables:
            results[table] = {}
            for fmt in formats:
                try:
                    if fmt == 'csv':
                        results[table][fmt] = self.export_csv(table)
                    elif fmt == 'json':
                        results[table][fmt] = self.export_clean_json(table) if clean else self.export_json(table)
                    elif fmt == 'jsonl':
                        results[table][fmt] = self.export_jsonl(table, clean=clean)
                    elif fmt == 'excel':
                        results[table][fmt] = self.export_excel(table)
                    elif fmt == 'parquet':
                        results[table][fmt] = self.export_parquet(table)
                except Exception as e:
                    logger.error(f"Error exporting {table} as {fmt}: {e}")
                    results[table][fmt] = None
        
        return results

    def export_all_ai_training(self) -> dict:
        """Export complete AI training dataset in multiple formats"""
        logger.info("Building AI training dataset...")
        dataset = self.build_training_dataset()
        
        results = {
            'jsonl': self.save_training_data(dataset, format='jsonl'),
            'json': self.save_training_data(dataset, format='json'),
        }
        
        if PANDAS_AVAILABLE:
            results['csv'] = self.save_training_data(dataset, format='csv')
        
        logger.info(f"AI training exports complete: {results}")
        return results
                    elif fmt == 'parquet':
                        results[table][fmt] = self.export_parquet(table)
                    elif fmt == 'markdown':
                        results[table][fmt] = self.export_markdown(table)
                except Exception as e:
                    logger.error(f"Export {table}/{fmt} failed: {e}")
        return results
