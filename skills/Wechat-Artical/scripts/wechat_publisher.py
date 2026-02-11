#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号一键发布脚本

用法：
    python wechat_publisher.py <文章目录路径>

示例：
    python wechat_publisher.py ./artical/artical1
"""

import os
import sys
import re
import json
import requests
from pathlib import Path


def _load_config():
    """从同目录下的配置文件读取配置"""
    config_path = Path(__file__).parent / "config.json"
    
    # 默认配置
    default_config = {
        "WECHAT_APPID": "wxxxxx",
        "WECHAT_APPSECRET": "0axxxx",
        "WECHAT_AUTHOR": "xxxx",
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


# ============== 配置（从同目录下的 config.json 文件读取）==============
_config = _load_config()
CONFIG = {
    "appid": _config.get("WECHAT_APPID", "wxxxxx"),
    "appsecret": _config.get("WECHAT_APPSECRET", "0axxxx"),
    "author": _config.get("WECHAT_AUTHOR", "xxxx"),
}

# 样式配置
STYLE = {
    "primary_color": "#003399",
    "text_color": "#333",
    "light_text": "#3f3f3f",
    "font_family": "-apple-system, BlinkMacSystemFont, 'Helvetica Neue', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei UI', 'Microsoft YaHei', Arial, sans-serif",
}

# 微信 API 地址
WECHAT_API = {
    "token": "https://api.weixin.qq.com/cgi-bin/token",
    "upload_material": "https://api.weixin.qq.com/cgi-bin/material/add_material",
    "upload_img": "https://api.weixin.qq.com/cgi-bin/media/uploadimg",
    "add_draft": "https://api.weixin.qq.com/cgi-bin/draft/add",
}


def publish_article(article_dir: str) -> str:
    """
    发布文章到微信公众号草稿箱

    Args:
        article_dir: 文章目录路径

    Returns:
        成功返回草稿 media_id，失败返回错误信息
    """
    try:
        publisher = WechatPublisher(article_dir)
        return publisher.run()
    except Exception as e:
        return f"错误: {str(e)}"


class ArticleParser:
    """文章解析器"""

    # 内部标记
    QUOTE_START = "__QUOTE_START__"
    QUOTE_END = "__QUOTE_END__"
    TITLE_IMAGE_PREFIX = "__TITLE_IMAGE_"  # 标题图片标记前缀，如 __TITLE_IMAGE_1__

    def __init__(self, article_dir: str):
        self.article_dir = Path(article_dir).resolve()
        self.title = ""
        self.cover_image = ""
        self.content_lines = []    # 所有内容（包含引言标记）
        self._in_quote = False     # 跟踪是否在引言块中

    def parse(self) -> bool:
        """解析 artical.md 文件"""
        md_path = self.article_dir / "artical.md"
        if not md_path.exists():
            raise FileNotFoundError(f"找不到 artical.md: {md_path}")

        with open(md_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 解析【文章标题】行 - 提取标题，整行不保留
            if stripped.startswith('【文章标题】'):
                title_part = stripped.replace('【文章标题】', '').strip()
                # 去掉开头的 # 符号
                title_part = re.sub(r'^#+\s*', '', title_part)
                self.title = title_part
                i += 1
                continue

            # 解析【封面主图】标记 - 自动使用 assets/cover.png，同时闭合引言
            if '【封面主图' in stripped and stripped.startswith('【') and '】' in stripped:
                # 如果在引言块中，先闭合引言
                if self._in_quote:
                    self.content_lines.append(self.QUOTE_END + "\n")
                    self._in_quote = False
                
                # 自动设置封面路径为 assets/cover.png
                cover_path = self.article_dir / "assets" / "cover.png"
                if cover_path.exists():
                    self.cover_image = "assets/cover.png"
                else:
                    # 向后兼容：如果下一行有图片语法，也支持
                    i += 1
                    while i < len(lines):
                        next_line = lines[i].strip()
                        if next_line:
                            img_match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', next_line)
                            if img_match:
                                self.cover_image = img_match.group(2)
                                # 不再把封面图片加入正文
                            i += 1
                            break
                        i += 1
                    continue
                
                i += 1
                # 跳过下一行如果是图片语法（向后兼容）
                if i < len(lines):
                    next_line = lines[i].strip()
                    if re.match(r'!\[([^\]]*)\]\(([^)]+)\)', next_line):
                        i += 1
                continue

            # 解析【引言】标记 - 插入引言开始标记
            if stripped == '【引言】':
                self.content_lines.append(self.QUOTE_START + "\n")
                self._in_quote = True
                i += 1
                continue

            # 解析【正文】标记 - 插入引言结束标记
            if stripped == '【正文】':
                if self._in_quote:
                    self.content_lines.append(self.QUOTE_END + "\n")
                    self._in_quote = False
                i += 1
                continue

            # 解析【标题1】【标题2】等标记 - 转换为内部标记，保留下一行标题文字
            title_match = re.match(r'^【标题(\d+)】$', stripped)
            if title_match:
                # 如果在引言块中，先闭合引言
                if self._in_quote:
                    self.content_lines.append(self.QUOTE_END + "\n")
                    self._in_quote = False
                
                title_num = title_match.group(1)
                # 插入内部标记
                self.content_lines.append(f"{self.TITLE_IMAGE_PREFIX}{title_num}__\n")
                i += 1
                # 下一行是标题文字，保留
                if i < len(lines):
                    self.content_lines.append(lines[i])
                    i += 1
                continue

            # 其他【xxx】标记行 - 不保留
            if stripped.startswith('【') and '】' in stripped:
                i += 1
                continue

            # 普通行 - 保留
            self.content_lines.append(line)
            i += 1

        # 解析结束时，如果引言未闭合，自动闭合
        if self._in_quote:
            self.content_lines.append(self.QUOTE_END + "\n")
            self._in_quote = False

        return True

    def get_content(self) -> str:
        """获取处理后的正文内容"""
        return ''.join(self.content_lines)

    def get_cover_path(self) -> str:
        """获取封面图片完整路径"""
        # 优先使用解析到的路径
        if self.cover_image:
            if self.cover_image.startswith('http'):
                return self.cover_image
            return str(self.article_dir / self.cover_image)
        
        # 自动检测 assets/cover.png
        auto_cover = self.article_dir / "assets" / "cover.png"
        if auto_cover.exists():
            return str(auto_cover)
        
        return ""


class WechatPublisher:
    """微信公众号发布器"""

    def __init__(self, article_dir: str):
        self.article_dir = Path(article_dir).resolve()
        self.appid = CONFIG["appid"]
        self.appsecret = CONFIG["appsecret"]
        self.access_token = None
        self.primary = STYLE["primary_color"]
        self.parser = ArticleParser(article_dir)
        self.title_image_urls = {}  # 保存标题图片的微信URL映射 {数字: URL}

    def run(self) -> str:
        """执行发布流程"""
        print("\n" + "=" * 50)
        print("   微信公众号文章发布")
        print("=" * 50 + "\n")

        # 1. 解析文章
        print("[1/6] 解析文章...")
        try:
            self.parser.parse()
            if not self.parser.title:
                return "错误: 未找到文章标题"
            print(f"      标题: {self.parser.title}")
            print(f"      封面: {self.parser.cover_image or '自动检测 assets/cover.png'}")
        except Exception as e:
            return f"错误: 解析文章失败 - {str(e)}"

        # 2. 获取 token
        if not self._get_token():
            return "错误: 获取 access_token 失败"

        # 3. 上传封面
        cover_path = self.parser.get_cover_path()
        if not cover_path or not os.path.exists(cover_path):
            return f"错误: 封面图片不存在 - {cover_path or 'assets/cover.png'}"

        thumb_media_id = self._upload_cover(cover_path)
        if not thumb_media_id:
            return "错误: 上传封面图片失败"

        # 4-5. 处理正文并转换 HTML
        html_content = self._process_content()

        # 保存预览文件
        preview_path = self.article_dir / "preview.html"
        with open(preview_path, 'w', encoding='utf-8') as f:
            f.write(f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>预览</title></head><body style="max-width:600px;margin:0 auto;">{html_content}</body></html>')
        print(f"      已生成预览: {preview_path}")

        # 6. 创建草稿
        result = self._create_draft(
            title=self.parser.title,
            html_content=html_content,
            thumb_media_id=thumb_media_id,
        )

        print("\n" + "=" * 50)
        if result and not result.startswith("错误"):
            print("发布成功!")
            print(f"   草稿 media_id: {result}")
            print("   请登录公众号后台查看草稿箱")
        else:
            print(f"发布失败: {result}")
        print("=" * 50 + "\n")

        return result

    def _get_token(self) -> bool:
        """获取 access_token"""
        print("[2/6] 获取 access_token...")

        url = f"{WECHAT_API['token']}?grant_type=client_credential&appid={self.appid}&secret={self.appsecret}"
        response = requests.get(url, timeout=10)
        data = response.json()

        if 'access_token' in data:
            self.access_token = data['access_token']
            print(f"      成功，有效期 {data.get('expires_in', 7200)} 秒")
            return True
        else:
            print(f"      失败: {data}")
            return False

    def _upload_cover(self, image_path: str) -> str:
        """上传封面图片"""
        print(f"[3/6] 上传封面图片: {image_path}")

        url = f"{WECHAT_API['upload_material']}?access_token={self.access_token}&type=image"

        with open(image_path, 'rb') as f:
            files = {'media': (os.path.basename(image_path), f, 'image/png')}
            response = requests.post(url, files=files, timeout=30)
            data = response.json()

        if 'media_id' in data:
            print(f"      成功，media_id: {data['media_id'][:20]}...")
            return data['media_id']
        else:
            print(f"      失败: {data}")
            return ""

    def _upload_content_image(self, image_path: str) -> str:
        """上传正文图片"""
        print(f"      上传图片: {image_path}")

        url = f"{WECHAT_API['upload_img']}?access_token={self.access_token}"

        with open(image_path, 'rb') as f:
            files = {'media': (os.path.basename(image_path), f, 'image/png')}
            response = requests.post(url, files=files, timeout=30)
            data = response.json()

        if 'url' in data:
            print(f"      成功")
            return data['url']
        else:
            print(f"      失败: {data}")
            return ""

    def _process_content(self) -> str:
        """处理正文内容"""
        print("[4/6] 处理正文图片...")

        content = self.parser.get_content()

        # 先上传标题图片 (assets/1.png, assets/2.png, ... assets/9.png)
        for i in range(1, 10):
            title_img_path = self.article_dir / "assets" / f"{i}.png"
            if title_img_path.exists():
                wechat_url = self._upload_content_image(str(title_img_path))
                if wechat_url:
                    self.title_image_urls[str(i)] = wechat_url
                    print(f"      标题图片 {i}.png 上传成功")

        # 上传正文中的图片
        img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        images = re.findall(img_pattern, content)

        for alt, img_path in images:
            if img_path.startswith('http'):
                continue

            full_path = self.article_dir / img_path
            if full_path.exists():
                wechat_url = self._upload_content_image(str(full_path))
                if wechat_url:
                    content = content.replace(f']({img_path})', f']({wechat_url})')
            else:
                print(f"      警告: 图片不存在 - {full_path}")

        # 转换为 HTML
        print("[5/6] 转换为 HTML...")
        html = self._markdown_to_html(content)
        print("      转换完成")

        return html

    def _markdown_to_html(self, md: str) -> str:
        """Markdown 转 HTML"""
        html_parts = []
        is_first_heading = True  # 标记是否是第一个标题

        # 外层容器
        html_parts.append(f'<section style="font-family: {STYLE["font_family"]}; letter-spacing: 0.5px; text-align: justify; padding: 10px; color: {STYLE["text_color"]};">')

        lines = md.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # 跳过空行
            if not line:
                i += 1
                continue

            # 引言块开始标记 - 按普通段落处理引言内容
            if line == ArticleParser.QUOTE_START:
                i += 1
                while i < len(lines) and lines[i].strip() != ArticleParser.QUOTE_END:
                    quote_line = lines[i].strip()
                    if quote_line:
                        # 处理图片
                        img_match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', quote_line)
                        if img_match:
                            alt, src = img_match.groups()
                            html_parts.append(self._render_image(src, alt))
                        else:
                            # 普通段落
                            html_parts.append(self._render_paragraph(quote_line))
                    i += 1
                i += 1  # 跳过 QUOTE_END
                continue

            # 处理【标题X】标记 - 渲染图片+标题文字
            title_img_match = re.match(r'__TITLE_IMAGE_(\d+)__', line)
            if title_img_match:
                title_num = title_img_match.group(1)
                i += 1
                # 下一行是标题文字
                title_text = ""
                if i < len(lines):
                    title_text = lines[i].strip()
                    i += 1
                # 渲染标题图片+标题文字
                html_parts.append(self._render_title_with_image(title_num, title_text))
                continue

            # 代码块
            if line.startswith('```'):
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                code_text = '\n'.join(code_lines)
                html_parts.append(self._render_code(code_text))
                i += 1
                continue

            # 一级标题
            if line.startswith('# ') and not line.startswith('## '):
                title = line[2:].strip()
                html_parts.append(self._render_h1(title, is_first_heading))
                is_first_heading = False
                i += 1
                continue

            # 二级标题
            if line.startswith('## '):
                title = line[3:].strip()
                html_parts.append(self._render_h2(title))
                i += 1
                continue

            # 三级标题
            if line.startswith('### '):
                title = line[4:].strip()
                html_parts.append(self._render_h3(title))
                i += 1
                continue

            # 图片
            img_match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', line)
            if img_match:
                alt, src = img_match.groups()
                html_parts.append(self._render_image(src, alt))
                i += 1
                continue

            # 无序列表
            if line.startswith('- ') or line.startswith('* '):
                list_items = []
                while i < len(lines):
                    l = lines[i].strip()
                    if l.startswith('- ') or l.startswith('* '):
                        list_items.append(l[2:])
                        i += 1
                    elif l == '':
                        i += 1
                        break
                    else:
                        break
                html_parts.append(self._render_ul(list_items))
                continue

            # 有序列表
            if re.match(r'^\d+\. ', line):
                list_items = []
                while i < len(lines):
                    l = lines[i].strip()
                    if re.match(r'^\d+\. ', l):
                        list_items.append(re.sub(r'^\d+\. ', '', l))
                        i += 1
                    elif l == '':
                        i += 1
                        break
                    else:
                        break
                html_parts.append(self._render_ol(list_items))
                continue

            # 分隔线
            if line == '---' or line == '***':
                html_parts.append(self._render_divider())
                i += 1
                continue

            # 普通段落
            html_parts.append(self._render_paragraph(line))
            i += 1

        # 页脚
        html_parts.append(self._render_footer())
        html_parts.append('</section>')

        return '\n'.join(html_parts)

    # ========== 样式渲染方法 ==========

    def _render_quote(self, text):
        return f'''
<section style="margin: 40px 0px;">
    <section style="border-top: 2px solid {self.primary}; width: 60px; margin-bottom: 25px;"></section>
    <section style="display: flex; align-items: flex-start;">
        <section style="margin-right: 12px;">
            <span style="font-size: 60px; line-height: 40px; color: {self.primary}; font-family: Georgia, serif;">"</span>
        </section>
        <section style="flex: 1; text-align: justify; font-size: 17px; color: {STYLE['light_text']}; line-height: 1.8; letter-spacing: 0.5px;">
            {text}
        </section>
    </section>
    <section style="display: flex; justify-content: flex-end; margin-top: 15px;">
        <span style="font-size: 60px; line-height: 20px; color: {self.primary}; font-family: Georgia, serif; height: 30px; display: block;">"</span>
    </section>
</section>'''

    def _render_title_with_image(self, title_num: str, title_text: str):
        """渲染标题图片+标题文字"""
        # 去掉标题文字开头的 # 号
        title_text = re.sub(r'^#+\s*', '', title_text.strip())

        # 从预上传的映射中获取微信URL
        img_url = self.title_image_urls.get(title_num)

        if not img_url:
            # 如果没有找到URL（图片不存在或上传失败），降级为普通标题渲染
            return self._render_h1(title_text, False)

        return f'''
<section style="margin: 45px 0 30px 0;">
    <section style="text-align: left; margin-bottom: 15px;">
        <img src="{img_url}" alt="标题{title_num}" style="max-width: 120px; height: auto;"/>
    </section>
    <section style="font-size: 24px; font-weight: bold; color: #1a1a1a; letter-spacing: 1px; line-height: 1.6; text-align: left;">
        {self._process_inline(title_text)}
    </section>
</section>'''

    def _render_h1(self, text, is_first=False):
        # 第一个标题顶部边距小一些
        margin_top = "20px" if is_first else "45px"
        return f'''
<section style="margin: {margin_top} 0 20px 0; display: flex; align-items: center;">
    <section style="width: 4px; height: 26px; background-color: {self.primary}; margin-right: 12px; flex-shrink: 0;"></section>
    <section style="font-size: 24px; font-weight: bold; color: #1a1a1a; letter-spacing: 1.5px;">
        {self._process_inline(text)}
    </section>
</section>'''

    def _render_h2(self, text):
        return f'''
<section style="margin: 35px 0 15px 0;">
    <section style="font-size: 17px; font-weight: bold; color: {self.primary}; letter-spacing: 1px;">
        {self._process_inline(text)}
    </section>
</section>'''

    def _render_h3(self, text):
        return f'''
<section style="margin: 25px 0 10px 0;">
    <section style="font-size: 16px; font-weight: bold; color: #1a1a1a; letter-spacing: 0.5px;">
        {self._process_inline(text)}
    </section>
</section>'''

    def _render_image(self, src, alt=""):
        return f'''
<section style="text-align: center; margin: 25px 0;">
    <img src="{src}" alt="{alt}" style="max-width: 100%; border-radius: 5px;"/>
</section>'''

    def _render_paragraph(self, text):
        processed = self._process_inline(text)
        return f'''
<section style="font-size: 17px; color: {STYLE['text_color']}; line-height: 1.8; margin-bottom: 15px;">
    <p>{processed}</p>
</section>'''

    def _render_ul(self, items):
        li_html = ''.join([
            f'<li style="margin: 8px 0; line-height: 1.8;">{self._process_inline(item)}</li>'
            for item in items
        ])
        return f'''
<section style="font-size: 17px; color: {STYLE['text_color']}; line-height: 1.8; margin: 15px 0; padding-left: 20px;">
    <ul style="margin: 0; padding-left: 20px;">{li_html}</ul>
</section>'''

    def _render_ol(self, items):
        li_html = ''.join([
            f'<li style="margin: 8px 0; line-height: 1.8;">{self._process_inline(item)}</li>'
            for item in items
        ])
        return f'''
<section style="font-size: 17px; color: {STYLE['text_color']}; line-height: 1.8; margin: 15px 0; padding-left: 20px;">
    <ol style="margin: 0; padding-left: 20px;">{li_html}</ol>
</section>'''

    def _render_code(self, code):
        escaped = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f'''
<section style="margin: 20px 0;">
    <pre style="background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; font-size: 14px; line-height: 1.6;"><code>{escaped}</code></pre>
</section>'''

    def _render_divider(self):
        return f'''
<section style="margin: 45px auto; display: flex; align-items: center; justify-content: center; width: 60%;">
    <section style="flex: 1; height: 1px; background-color: {self.primary}; opacity: 0.15;"></section>
    <section style="width: 4px; height: 4px; background-color: {self.primary}; margin: 0 15px; transform: rotate(45deg);"></section>
    <section style="flex: 1; height: 1px; background-color: {self.primary}; opacity: 0.15;"></section>
</section>'''

    def _render_footer(self):
        return f'''
<section style="margin-top: 60px; border-top: 1px solid #eee; text-align: center; padding-top: 20px;">
    <span style="font-size: 11px; color: #bbb; letter-spacing: 3px; font-family: 'Helvetica Neue', Helvetica, sans-serif; text-transform: uppercase;">
        {CONFIG['author']} · 2026 Edition
    </span>
</section>'''

    def _process_inline(self, text):
        """处理行内样式"""
        # 粗体
        text = re.sub(
            r'\*\*(.+?)\*\*',
            f'<span style="color: {self.primary}; font-weight: bold;">\\1</span>',
            text
        )
        # 斜体
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        # 链接
        text = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            f'<a href="\\2" style="color: {self.primary}; text-decoration: none;">\\1</a>',
            text
        )
        # 行内代码
        text = re.sub(
            r'`([^`]+)`',
            r'<code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-size: 14px;">\1</code>',
            text
        )
        return text

    def _create_draft(self, title: str, html_content: str, thumb_media_id: str) -> str:
        """创建草稿"""
        print("[6/6] 创建草稿...")

        url = f"{WECHAT_API['add_draft']}?access_token={self.access_token}"

        data = {
            "articles": [{
                "title": title,
                "author": CONFIG["author"],
                "digest": "",
                "content": html_content,
                "thumb_media_id": thumb_media_id,
                "need_open_comment": 0,
                "only_fans_can_comment": 0
            }]
        }

        response = requests.post(
            url,
            data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        result = response.json()

        if 'media_id' in result:
            print(f"      成功! media_id: {result['media_id']}")
            return result['media_id']
        else:
            print(f"      失败: {result}")
            return f"错误: {result}"


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("用法: python wechat_publisher.py <文章目录路径>")
        print("示例: python wechat_publisher.py ./artical/artical1")
        sys.exit(1)

    article_dir = sys.argv[1]
    result = publish_article(article_dir)
    print(result)

