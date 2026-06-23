import json

workflow = {
  "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}},
  "2": {"class_type": "LoadImage", "inputs": {"image": "upload_your_restaurant_image.jpg"}},
  "3": {"class_type": "DepthAnythingPreprocessor", "inputs": {"image": ["2", 0], "resolution": 512}},
  "4": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "control_v11f1p_sd15_depth.pth"}},
  "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": "beautiful restaurant interior, warm lighting, elegant dining, high quality food photography"}},
  "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": "ugly, blurry, bad quality, people, text"}},
  "7": {"class_type": "ControlNetApply", "inputs": {"conditioning": ["5", 0], "control_net": ["4", 0], "image": ["3", 0], "strength": 0.8}},
  "8": {"class_type": "KSampler", "inputs": {
    "model": ["1", 0], "positive": ["7", 0], "negative": ["6", 0],
    "latent_image": ["9", 0], "seed": 42, "steps": 25,
    "cfg": 7.5, "sampler_name": "euler_ancestral", "scheduler": "karras",
    "denoise": 0.75
  }},
  "9": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}},
  "10": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["1", 2]}},
  "11": {"class_type": "SaveImage", "inputs": {"images": ["10", 0], "filename_prefix": "restaurant_output"}}
}

with open("/ComfyUI/workflows/restaurant_style.json", "w") as f:
    json.dump(workflow, f, indent=2)

print("✅ Saved: /ComfyUI/workflows/restaurant_style.json")