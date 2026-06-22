"""
Nexuzy Data Collector - AI Model Manager
Supports:
  1. Local GGUF file (gemma-4b-it-q4_k_m.gguf) — your existing file, no download needed
  2. HuggingFace pure-Python fallback models (no C++, no token needed for public models)
"""

import os
from loguru import logger
from typing import Callable, Optional


# Your local GGUF file path (already downloaded by you)
LOCAL_GGUF_PATH = 'models/gemma-4b-it-q4_k_m.gguf'

MODEL_OPTIONS = [
    {
        'label': '⭐ Gemma 4B GGUF (Your Local File — Recommended)',
        'model_id': 'local/gemma-4b-it-q4_k_m',
        'size': 'Already on disk'
    },
    {
        'label': 'TinyLlama 1.1B (Lightweight, ~2GB RAM)',
        'model_id': 'TinyLlama/TinyLlama-1.1B-Chat-v1.0',
        'size': '~1.1 GB download'
    },
    {
        'label': 'Qwen2 0.5B (Ultra Light, ~1GB RAM — No token needed)',
        'model_id': 'Qwen/Qwen2-0.5B-Instruct',
        'size': '~0.5 GB download'
    },
    {
        'label': 'Phi-2 (Microsoft, ~4GB RAM — No token needed)',
        'model_id': 'microsoft/phi-2',
        'size': '~2.7 GB download'
    },
]

DEFAULT_MODEL_ID = 'local/gemma-4b-it-q4_k_m'
MODEL_CACHE_DIR = 'models/hf_cache'


class ModelDownloader:
    def __init__(self,
                 model_dir: str = MODEL_CACHE_DIR,
                 on_progress: Callable = None,
                 on_status: Callable = None):
        self.model_dir = model_dir
        self.on_progress = on_progress or (lambda pct, msg: None)
        self.on_status = on_status or (lambda msg: print(msg))
        os.makedirs(model_dir, exist_ok=True)

    def model_exists(self, model_id: str = DEFAULT_MODEL_ID) -> bool:
        """Check if model is available locally."""
        # Check local GGUF file first
        if model_id == 'local/gemma-4b-it-q4_k_m':
            return os.path.exists(LOCAL_GGUF_PATH)
        # Check HuggingFace cache
        try:
            cache_path = os.path.join(self.model_dir, model_id.replace('/', '--'))
            return os.path.exists(cache_path) and len(os.listdir(cache_path)) > 0
        except Exception:
            return False

    def download(self, model_id: str = DEFAULT_MODEL_ID,
                 hf_token: str = None) -> Optional[str]:
        """
        Download HuggingFace model — pure Python, no C++.
        If local GGUF selected, just verify it exists.
        """
        # Local GGUF — no download needed
        if model_id == 'local/gemma-4b-it-q4_k_m':
            if os.path.exists(LOCAL_GGUF_PATH):
                self.on_status(f'✅ Using local GGUF: {LOCAL_GGUF_PATH}')
                self.on_progress(100, 'Ready')
                return LOCAL_GGUF_PATH
            else:
                self.on_status(
                    f'❌ GGUF not found at: {LOCAL_GGUF_PATH}\n'
                    f'Download manually from: https://huggingface.co/google/gemma-4b-it-GGUF\n'
                    f'Save as: {LOCAL_GGUF_PATH}'
                )
                return None

        # HuggingFace download
        self.on_status(f'Downloading model: {model_id}')
        self.on_progress(5, f'Starting: {model_id}')
        try:
            from huggingface_hub import snapshot_download
            local_dir = os.path.join(self.model_dir, model_id.replace('/', '--'))
            path = snapshot_download(
                repo_id=model_id,
                local_dir=local_dir,
                token=hf_token,
                ignore_patterns=['*.msgpack', '*.h5', 'flax_*', 'tf_*'],
            )
            self.on_progress(100, 'Download complete')
            self.on_status(f'✅ Model ready at: {path}')
            logger.success(f'Model downloaded: {path}')
            return path
        except Exception as e:
            self.on_status(f'❌ Download failed: {e}')
            logger.error(f'Model download failed: {e}')
            return None

    def auto_download(self, hf_token: str = None) -> Optional[str]:
        if self.model_exists(DEFAULT_MODEL_ID):
            self.on_status('✅ Model already available locally')
            return LOCAL_GGUF_PATH if DEFAULT_MODEL_ID == 'local/gemma-4b-it-q4_k_m' else \
                os.path.join(self.model_dir, DEFAULT_MODEL_ID.replace('/', '--'))
        return self.download(hf_token=hf_token)


def get_or_download_model(config: dict,
                           on_progress: Callable = None,
                           on_status: Callable = None,
                           hf_token: str = None) -> Optional[str]:
    model_id = config.get('model', {}).get('hf_model', DEFAULT_MODEL_ID)
    dl = ModelDownloader(
        model_dir=MODEL_CACHE_DIR,
        on_progress=on_progress or (lambda p, m: None),
        on_status=on_status or (lambda m: print(m))
    )
    if dl.model_exists(model_id):
        if model_id == 'local/gemma-4b-it-q4_k_m':
            return LOCAL_GGUF_PATH
        return os.path.join(MODEL_CACHE_DIR, model_id.replace('/', '--'))
    return dl.download(model_id=model_id, hf_token=hf_token)
