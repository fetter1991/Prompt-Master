# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

import base64
import mimetypes
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent
_ = load_dotenv(BASE_DIR / '.env')


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f'缺少环境变量: {name}')
    return value


client = OpenAI(
    base_url=get_required_env('MODELSCOPE_BASE_URL'),
    api_key=get_required_env('MODELSCOPE_API_KEY'),
)

def image_to_data_url(image_path: str | Path) -> str:
    path = Path(image_path)
    if not path.is_absolute():
        path = BASE_DIR / path

    if not path.is_file():
        raise FileNotFoundError(f'Image file not found: {path}')

    image_data = path.read_bytes()
    mime_type, _ = mimetypes.guess_type(path.as_posix())
    if mime_type is None or not mime_type.startswith('image/'):
        mime_type = 'image/png'

    base64_encoded = base64.b64encode(image_data).decode('utf-8')
    return f'data:{mime_type};base64,{base64_encoded}'


IMAGE_PATH = BASE_DIR / 'static/uploads/7d5411e30e71405c8a0a184595e8318c_thumb.jpg'
MODEL_ID = 'Qwen/Qwen3.5-35B-A3B'
PROMPT = (
    '仔细分析这张图片的内容、构成及表达的意图，提炼分析结果，为图片生成一个标题和5个精准中文标签：'
    '每个标签不超过5个字，用英文逗号分隔，包含主体、服装、风格、场景等信息；'
    '标题不超过10个字，最终严格以 JSON 对象格式输出，'
    '如：{"title":"标题","tags":"标签1,标签2,标签3,标签4,标签5"}'
)

response = client.chat.completions.create(
    model=MODEL_ID,
    messages=[
        {
            'role': 'user',
            'content': [
                {
                    'type': 'text',
                    'text': PROMPT,
                },
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': image_to_data_url(IMAGE_PATH),
                    },
                },
            ],
        }
    ],
    stream=True,
)

for chunk in response:
    if chunk.choices:
        content = chunk.choices[0].delta.content
        if content:
            print(content, end='', flush=True)
