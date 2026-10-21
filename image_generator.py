import re
import random
import urllib.parse
import logging
from typing import Dict, Any, Tuple, Optional
import requests

logger = logging.getLogger("antigravity-image")

IMAGE_KEYWORDS = [
    r"^vẽ\s+",
    r"^tạo\s+ảnh\s+",
    r"^tạo\s+hình\s+",
    r"^sinh\s+ảnh\s+",
    r"^hãy\s+vẽ\s+",
    r"^vẽ\s+cho\s+tôi\s+",
    r"^tạo\s+cho\s+tôi\s+(một\s+)?(bức\s+)?ảnh\s+",
    r"^chụp\s+(cho\s+tôi\s+)?(một\s+)?(bức\s+)?ảnh\s+",
    r"^hãy\s+chụp\s+",
    r"^chụp\s+ảnh\s+",
    r"^ảnh\s+chụp\s+",
    r"^bức\s+ảnh\s+chụp\s+",
    r"^/image\s+",
    r"^/draw\s+",
    r"^generate\s+image\s+",
    r"^draw\s+",
    r"^create\s+image\s+",
    r"^photo\s+of\s+",
    r"^photograph\s+of\s+",
    r"^picture\s+of\s+"
]

STYLE_MODIFIERS = {
    "photorealistic": "authentic candid raw photograph, shot on 50mm f/1.4 lens Sony A7 IV, realistic natural daylight, subtle skin pores and authentic micro-textures, natural depth of field, real life documentary photography, unedited, no CGI, no 3D render, no plastic skin, 8k resolution",
    "anime": "anime aesthetic, Studio Ghibli style, vibrant colors, clean lineart, highly detailed illustration, 4k resolution",
    "cyberpunk": "cyberpunk style, neon lights, glowing volumetric fog, futuristic city, highly detailed, octane render, 8k",
    "oil_painting": "classic oil painting, visible canvas texture, rich oil brushstrokes, dramatic chiaroscuro lighting, masterpiece",
    "3d_render": "3D digital art, Unreal Engine 5 render, cinematic lighting, ultra-detailed textures, Pixar style, ray tracing 8k",
    "fantasy": "epic high fantasy illustration, mystical atmosphere, magical particles, concept art, dynamic composition, masterpiece"
}

ASPECT_RATIOS = {
    "1:1": (1024, 1024),
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "4:3": (1024, 768),
    "3:4": (768, 1024)
}

def is_image_request(prompt: str, model: Optional[str] = None) -> bool:
    if not prompt:
        return False
    p = prompt.strip().lower()
    if model and any(k in model.lower() for k in ["image", "flux", "draw", "diffusion"]):
        return True
    for pat in IMAGE_KEYWORDS:
        if re.search(pat, p, re.IGNORECASE):
            return True
    return False

def clean_image_prompt(prompt: str) -> str:
    cleaned = prompt.strip()
    for pat in IMAGE_KEYWORDS:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else prompt.strip()

def enhance_prompt_with_gemini(client, raw_prompt: str, style: Optional[str] = None) -> str:
    try:
        style_hint = f" Artistic style preference: {style}." if style else ""
        system_instruction = (
            "You are an expert AI prompt engineer for text-to-image models (Flux.1, Midjourney, Stable Diffusion). "
            "Your job is to translate Vietnamese or short user requests into an exquisite, highly detailed English prompt. "
            "REALISM DIRECTIVE: If the user request mentions real life, photo, chụp ảnh, đời thật, or photorealistic style: "
            "make the prompt describe an authentic, real-world photograph. Specify professional camera gear (e.g. shot on Sony A7 IV or Canon EOS R5, 50mm f/1.4 or 85mm lens), natural ambient daylight or soft golden hour lighting, authentic skin textures with subtle pores and natural imperfections, detailed fabric and surroundings, and realistic depth of field. "
            "Strictly avoid CGI, 3D render, smooth plastic skin, artificial airbrushing, or cartoon tropes. "
            "Output ONLY the final English prompt string, with NO introductory text, NO quotes, and NO explanations."
        )
        user_message = f"Create a text-to-image prompt for: '{raw_prompt}'.{style_hint}"
        enhanced_text, _ = client.generate(
            prompt=user_message,
            system_prompt=system_instruction,
            thinking=False,
            web_search=False
        )
        res = enhanced_text.strip().strip('"').strip("'").replace("\n", " ")
        if len(res) > 20:
            return res
    except Exception as e:
        logger.warning(f"Lỗi khi tối ưu prompt bằng Gemini: {e}")

    # Fallback prompt enhancement
    mod = STYLE_MODIFIERS.get(style, "authentic raw photograph, shot on 35mm lens, natural daylight, realistic details")
    return f"{raw_prompt}, {mod}"

def build_image_url(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    model: str = "flux",
    seed: Optional[int] = None,
    nologo: bool = True
) -> Tuple[str, int]:
    if seed is None or seed <= 0:
        seed = random.randint(100000, 99999999)
    encoded = urllib.parse.quote(prompt)
    model_param = f"&model={model}" if model and model != "default" else ""
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}{model_param}&seed={seed}&nologo={'true' if nologo else 'false'}"
    return url, seed

def generate_image_markdown(
    user_prompt: str,
    enhanced_prompt: str,
    image_url: str,
    width: int,
    height: int,
    seed: int,
    model: str = "Flux.1"
) -> str:
    return (
        f"### 🎨 Tác Phẩm AI Vừa Tạo\n\n"
        f"![{user_prompt}]({image_url})\n\n"
        f"> **💡 Mô tả ban đầu:** {user_prompt}\n\n"
        f"---\n"
        f"- **✨ Prompt tiếng Anh tối ưu:** *{enhanced_prompt}*\n"
        f"- **📐 Kích thước:** `{width}x{height}` | **Mô hình:** `{model}` | **Seed:** `{seed}`\n"
        f"- 🔗 [🔍 Xem kích thước đầy đủ]({image_url}) &nbsp;•&nbsp; [📥 Tải ảnh chất lượng cao]({image_url})\n"
    )
