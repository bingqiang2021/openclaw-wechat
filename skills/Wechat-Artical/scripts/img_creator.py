#!/usr/bin/env python3
"""
封面图片生成器
用法: python img_creator.py <文章目录路径>
"""

import os
import sys
import re
import base64
import asyncio
import json
from pathlib import Path
from typing import List, Union
import aiohttp
from PIL import Image, ImageDraw, ImageFont


def _load_config():
    """从同目录下的配置文件读取配置"""
    config_path = Path(__file__).parent / "config.json"
    
    # 默认配置
    default_config = {
        "IMAGE_API_BASE_URL": "https://xxx.com/v1",
        "IMAGE_API_KEY": "sk-xxx",
        "IMAGE_MODEL_NAME": "gemini-3-pro-image-preview",
        "IMAGE_FALLBACK_MODEL_NAME": "gemini-2.0-flash-exp-image-generation"
    }
    
    try:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并配置，确保所有必需的键都存在
                return {**default_config, **config}
        else:
            print(f"警告: 配置文件不存在 - {config_path}，使用默认配置")
            return default_config
    except Exception as e:
        print(f"警告: 读取配置文件失败 - {e}，使用默认配置")
        return default_config


# API 配置（从同目录下的 config.json 文件读取）
_config = _load_config()
BASE_URL = _config["IMAGE_API_BASE_URL"]
API_KEY = _config["IMAGE_API_KEY"]
MODEL_NAME = _config["IMAGE_MODEL_NAME"]
FALLBACK_MODEL_NAME = _config["IMAGE_FALLBACK_MODEL_NAME"]


def create_cover_image(article_dir: str, cover_text: str = "") -> str:
    """
    根据文章目录生成封面图片

    Args:
        article_dir: 文章目录路径
        cover_text: 封面图上的文字（可选，如不提供则从artical.md中提取标题）

    Returns:
        成功返回图片路径，失败返回错误信息
    """
    return asyncio.run(_create_cover_image_async(article_dir, cover_text))


async def _create_cover_image_async(article_dir: str, cover_text: str = "") -> str:
    """异步生成封面图片"""
    try:
        article_path = Path(article_dir).resolve()

        # 检查目录是否存在
        if not article_path.exists():
            return f"错误: 目录不存在 - {article_path}"

        if not article_path.is_dir():
            return f"错误: 路径不是目录 - {article_path}"

        # 查找 cover_design.md
        cover_design_path = article_path / "cover_design.md"
        if not cover_design_path.exists():
            return f"错误: 找不到 cover_design.md - {cover_design_path}"

        # 读取提示词
        prompt = cover_design_path.read_text(encoding="utf-8").strip()
        if not prompt:
            return "错误: cover_design.md 内容为空"

        # 创建 assets 目录
        assets_dir = article_path / "assets"
        assets_dir.mkdir(exist_ok=True)

        # 设置输出路径
        output_path = assets_dir / "cover.png"

        # 生成图片
        try:
            result = await _generate(prompt, None, str(output_path))
        except Exception as e:
            return f"错误: {str(e)}"

        if result:
            # 如果没有提供文字，尝试从artical.md提取标题
            if not cover_text:
                cover_text = _extract_title_from_article(article_path)

            # 在图片上添加文字
            if cover_text:
                _add_text_to_image(str(output_path), cover_text)
                print(f"已在封面图上添加文字: {cover_text}")

            return result
        else:
            return "错误: 图片生成失败，请检查 API 配置或网络连接"

    except Exception as e:
        return f"错误: {str(e)}"


def _extract_title_from_article(article_path: Path) -> str:
    """从artical.md中提取文章标题"""
    artical_md = article_path / "artical.md"
    if not artical_md.exists():
        return ""

    try:
        content = artical_md.read_text(encoding="utf-8")
        # 查找【文章标题】行
        match = re.search(r'【文章标题】[#\s]*(.+)', content)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return ""


def _add_text_to_image(image_path: str, text: str) -> None:
    """
    在图片上添加文字

    Args:
        image_path: 图片路径
        text: 要添加的文字
    """
    try:
        # 打开图片
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)

        # 获取图片尺寸
        img_width, img_height = img.size

        # 尝试加载中文字体，按优先级尝试不同路径
        font_paths = [
            "/System/Library/Fonts/STHeiti Medium.ttc",  # macOS 黑体
            "/System/Library/Fonts/PingFang.ttc",  # macOS 苹方
            "/System/Library/Fonts/Hiragino Sans GB.ttc",  # macOS 冬青黑体
            "/Library/Fonts/Arial Unicode.ttf",  # Arial Unicode
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Linux Noto
            "C:/Windows/Fonts/msyh.ttc",  # Windows 微软雅黑
            "C:/Windows/Fonts/simhei.ttf",  # Windows 黑体
        ]

        font = None
        font_size = int(img_width * 0.06)  # 字体大小为图片宽度的6%

        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except Exception:
                    continue

        if font is None:
            # 使用默认字体
            font = ImageFont.load_default()
            print("警告: 未找到中文字体，使用默认字体")

        # 文字换行处理（如果文字太长）
        max_chars_per_line = 15  # 每行最大字符数
        lines = []
        current_line = ""

        for char in text:
            current_line += char
            if len(current_line) >= max_chars_per_line:
                lines.append(current_line)
                current_line = ""
        if current_line:
            lines.append(current_line)

        # 计算文字总高度
        line_height = font_size * 1.5
        total_text_height = len(lines) * line_height

        # 文字位置：底部居中，留一定边距
        y_start = img_height - total_text_height - int(img_height * 0.08)

        # 绘制半透明背景条
        bg_padding = 20
        bg_top = y_start - bg_padding
        bg_bottom = img_height - int(img_height * 0.05)

        # 创建半透明层
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(
            [(0, bg_top), (img_width, bg_bottom)],
            fill=(0, 0, 0, 140)  # 半透明黑色
        )

        # 合并图层
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)

        # 绘制文字（带描边效果）
        for i, line in enumerate(lines):
            # 计算每行文字宽度以居中
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (img_width - text_width) // 2
            y = y_start + i * line_height

            # 绘制文字描边
            stroke_color = (0, 0, 0)
            for dx in [-2, -1, 0, 1, 2]:
                for dy in [-2, -1, 0, 1, 2]:
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), line, font=font, fill=stroke_color)

            # 绘制白色文字
            draw.text((x, y), line, font=font, fill=(255, 255, 255))

        # 转换回RGB并保存
        if img.mode == 'RGBA':
            # 创建白色背景
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background

        img.save(image_path)

    except Exception as e:
        print(f"警告: 添加文字失败 - {str(e)}")


async def text2image(prompt: str, output_path: str = "./output/result.png") -> str:
    """
    文生图

    Args:
        prompt: 提示词
        output_path: 输出文件路径

    Returns:
        成功返回文件路径，失败返回空字符串
    """
    return await _generate(prompt, None, output_path)


async def image2image(
    prompt: str,
    images: Union[str, List[str]],
    output_path: str = "./output/result.png"
) -> str:
    """
    图生图

    Args:
        prompt: 提示词
        images: 参考图片路径（单个或列表）
        output_path: 输出文件路径

    Returns:
        成功返回文件路径，失败返回空字符串
    """
    if isinstance(images, str):
        images = [images]
    return await _generate(prompt, images, output_path)


# =============== 内部函数 ===============

async def _generate(prompt: str, images: List[str], output_path: str) -> str:
    """核心生成逻辑"""
    content = _build_content(prompt, images)

    models = [
        (MODEL_NAME, 300),
        (FALLBACK_MODEL_NAME, 45)
    ]

    errors = []
    async with aiohttp.ClientSession() as session:
        for model, timeout in models:
            try:
                print(f"尝试使用模型: {model} (超时: {timeout}秒)...")
                data = await _call_api(session, model, content, timeout)

                if "choices" in data and data["choices"]:
                    resp = data["choices"][0].get("message", {}).get("content", "")
                    img_data = _extract_image(resp)

                    if img_data:
                        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                        with open(output_path, "wb") as f:
                            f.write(base64.b64decode(img_data))
                        print(f"✓ 模型 {model} 成功生成图片")
                        return output_path
                    else:
                        error_msg = f"模型 {model} 返回的数据中未找到图片"
                        print(f"✗ {error_msg}")
                        errors.append(error_msg)
                else:
                    error_msg = f"模型 {model} 返回的数据格式异常: {data}"
                    print(f"✗ {error_msg}")
                    errors.append(error_msg)

            except Exception as e:
                error_msg = f"模型 {model} 失败: {e}"
                print(f"✗ {error_msg}")
                errors.append(error_msg)
                continue

    # 所有模型都失败，返回详细错误信息
    error_summary = "\n".join([f"  - {err}" for err in errors])
    raise Exception(f"所有模型都失败了:\n{error_summary}")


def _build_content(prompt: str, images: List[str]):
    """构建请求内容"""
    if not images:
        return prompt

    content = [{"type": "text", "text": prompt}]

    for img_path in images:
        if not os.path.exists(img_path):
            continue
        with open(img_path, "rb") as f:
            b64 = base64.standard_b64encode(f.read()).decode()

        suffix = Path(img_path).suffix.lower()
        media = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp", ".gif": "gif"}
        mtype = media.get(suffix, "png")

        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/{mtype};base64,{b64}"}
        })

    return content


def _extract_image(content) -> str:
    """从响应中提取base64图片"""
    if isinstance(content, str):
        match = re.search(r'data:image/\w+;base64,([A-Za-z0-9+/=]+)', content)
        if match:
            return match.group(1)
    elif isinstance(content, list):
        for item in content:
            if item.get("type") == "image_url":
                url = item.get("image_url", {}).get("url", "")
                if "base64," in url:
                    return url.split("base64,")[1]
            elif item.get("type") == "text":
                result = _extract_image(item.get("text", ""))
                if result:
                    return result
    return ""


async def _call_api(session, model: str, content, timeout: int) -> dict:
    """调用API"""
    async with session.post(
        f"{BASE_URL}/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 4096
        },
        timeout=aiohttp.ClientTimeout(total=timeout)
    ) as resp:
        if resp.status != 200:
            # 尝试读取响应体获取详细错误信息
            try:
                error_data = await resp.json()
                error_msg = error_data.get("error", {}).get("message", str(error_data))
                raise Exception(f"API错误 {resp.status}: {error_msg}")
            except:
                # 如果无法解析 JSON，使用状态码和文本
                try:
                    error_text = await resp.text()
                    raise Exception(f"API错误 {resp.status}: {error_text[:200]}")
                except:
                    raise Exception(f"API错误: HTTP {resp.status}")
        return await resp.json()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python img_creator.py <文章目录路径>")
        print("示例: python img_creator.py ./artical/我的文章")
        sys.exit(1)

    article_dir = sys.argv[1]
    result = create_cover_image(article_dir)
    print(result)

