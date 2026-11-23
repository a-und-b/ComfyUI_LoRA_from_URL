import os
import hashlib
from urllib.parse import urlparse

import requests
import folder_paths
import comfy.utils
import comfy.sd
from tqdm import tqdm

# (connect, read) seconds; read is per chunk, so large files are fine.
TIMEOUT = (10, 60)


class LoadLoraFromURL:
    """Load a LoRA model from a URL"""

    def __init__(self):
        self.cache_dir = os.path.join(folder_paths.get_input_directory(), "url_loras")
        os.makedirs(self.cache_dir, exist_ok=True)

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "url": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Direct download URL to a .safetensors LoRA file",
                    },
                ),
                "model": ("MODEL",),
                "strength": (
                    "FLOAT",
                    {
                        "default": 1.0,
                        "min": 0.0,
                        "max": 10.0,
                        "step": 0.01,
                        "tooltip": "LoRA strength applied to the model",
                    },
                ),
            }
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "load_lora"
    CATEGORY = "loaders"
    DESCRIPTION = (
        "Downloads a LoRA from a URL (cached under input/url_loras) and applies "
        "it to the given model."
    )

    def download_if_needed(self, url):
        """Download the file if not in cache"""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Load LoRA From URL: expected an http(s) URL, got {url!r}")

        filename = hashlib.md5(url.encode()).hexdigest() + ".safetensors"
        local_path = os.path.join(self.cache_dir, filename)

        if os.path.exists(local_path):
            return local_path

        # Download to .part and rename on success, so a broken download is never
        # picked up from the cache by a later run.
        part_path = local_path + ".part"
        print(f"Downloading LoRA from {url}")
        try:
            with requests.get(url, stream=True, timeout=TIMEOUT) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))
                with open(part_path, "wb") as f, tqdm(
                    desc=filename,
                    total=total_size,
                    unit="iB",
                    unit_scale=True,
                ) as pbar:
                    for data in response.iter_content(chunk_size=8192):
                        pbar.update(f.write(data))
            os.replace(part_path, local_path)
        except BaseException:
            if os.path.exists(part_path):
                os.remove(part_path)
            raise

        return local_path

    def load_lora(self, url, model, strength):
        # Errors propagate so ComfyUI shows them on the node instead of
        # silently running the model without the LoRA.
        lora_path = self.download_if_needed(url)
        lora = comfy.utils.load_torch_file(lora_path)
        model_lora, _ = comfy.sd.load_lora_for_models(model, None, lora, strength, 0)
        return (model_lora,)


NODE_CLASS_MAPPINGS = {
    "Load LoRA From URL": LoadLoraFromURL
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Load LoRA From URL": "Load LoRA From URL"
}
