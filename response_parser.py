import re
import urllib.parse
from typing import List, Dict, Any, Optional

def parse_markdown_table(table_text: str) -> Optional[Dict[str, Any]]:
    lines = [l.strip() for l in table_text.strip().split('\n') if l.strip()]
    if len(lines) < 2:
        return None

    sep_idx = -1
    for i, line in enumerate(lines):
        if re.match(r'^\|?[\s:-]+\|[\s:\|-]+$', line):
            sep_idx = i
            break

    if sep_idx <= 0:
        return None

    def split_cells(line: str) -> List[str]:
        trimmed = line.strip()
        if trimmed.startswith('|'):
            trimmed = trimmed[1:]
        if trimmed.endswith('|'):
            trimmed = trimmed[:-1]
        return [c.strip() for c in trimmed.split('|')]

    headers = split_cells(lines[sep_idx - 1])
    sep_cells = split_cells(lines[sep_idx])

    alignments = []
    for cell in sep_cells:
        c = cell.strip()
        if c.startswith(':') and c.endswith(':'):
            alignments.append('center')
        elif c.endswith(':'):
            alignments.append('right')
        elif c.startswith(':'):
            alignments.append('left')
        else:
            alignments.append('left')

    rows = []
    for line in lines[sep_idx + 1:]:
        if not ('|' in line):
            continue
        cells = split_cells(line)
        if len(cells) < len(headers):
            cells.extend([''] * (len(headers) - len(cells)))
        elif len(cells) > len(headers):
            cells = cells[:len(headers)]
        rows.append(cells)

    return {
        'headers': headers,
        'rows': rows,
        'alignments': alignments,
        'columns_count': len(headers),
        'rows_count': len(rows),
        'raw': table_text.strip()
    }

def extract_domain(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc.replace('www.', '')
    except Exception:
        return ''

def parse_callout(block_text: str) -> Optional[Dict[str, Any]]:
    lines = block_text.split('\n')
    if not lines:
        return None

    first_line = lines[0].strip()
    gh_match = re.match(r'^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION|DANGER|INFO|SUCCESS)\](?:\s+(.*))?$', first_line, re.IGNORECASE)
    if gh_match:
        variant = gh_match.group(1).lower()
        if variant == 'danger':
            variant = 'caution'
        custom_title = gh_match.group(2) or ''
        default_titles = {
            'note': 'Ghi chú (Note)',
            'tip': 'Mẹo hữu ích (Tip)',
            'important': 'Quan trọng (Important)',
            'warning': 'Cảnh báo (Warning)',
            'caution': 'Lưu ý rủi ro (Caution)',
            'info': 'Thông tin (Info)',
            'success': 'Thành công (Success)'
        }
        title = custom_title.strip() or default_titles.get(variant, variant.capitalize())
        content_lines = []
        for l in lines[1:]:
            cleaned = re.sub(r'^>\s?', '', l)
            content_lines.append(cleaned)
        return {
            'type': 'callout',
            'variant': variant,
            'title': title,
            'content': '\n'.join(content_lines).strip()
        }

    vn_match = re.match(r'^>\s*\*\*(Lưu ý|Mẹo|Cảnh báo|Quan trọng|Chú ý|Mẹo nhỏ|Ghi chú)\s*:?\*\*(?:\s*(.*))?$', first_line, re.IGNORECASE)
    if vn_match:
        keyword = vn_match.group(1).lower()
        rest = vn_match.group(2) or ''
        variant_map = {
            'lưu ý': 'note',
            'ghi chú': 'note',
            'chú ý': 'note',
            'mẹo': 'tip',
            'mẹo nhỏ': 'tip',
            'cảnh báo': 'warning',
            'quan trọng': 'important'
        }
        variant = variant_map.get(keyword, 'info')
        content_lines = []
        if rest.strip():
            content_lines.append(rest.strip())
        for l in lines[1:]:
            cleaned = re.sub(r'^>\s?', '', l)
            content_lines.append(cleaned)
        return {
            'type': 'callout',
            'variant': variant,
            'title': vn_match.group(1).capitalize(),
            'content': '\n'.join(content_lines).strip()
        }

    return None

def parse_task_list(text: str) -> Optional[Dict[str, Any]]:
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    if not lines:
        return None

    items = []
    for line in lines:
        m = re.match(r'^-\s*\[([ xX])\]\s*(.+)$', line)
        if m:
            checked = m.group(1).strip().lower() == 'x'
            task_text = m.group(2).strip()
            items.append({'task': task_text, 'completed': checked})
        else:
            return None

    if items:
        return {
            'type': 'task_list',
            'items': items,
            'total': len(items),
            'completed_count': sum(1 for it in items if it['completed']),
            'raw': text.strip()
        }
    return None

def parse_suggestions(text: str) -> Optional[Dict[str, Any]]:
    lower = text.lower()
    if not any(k in lower for k in ['gợi ý câu hỏi', 'gợi ý tiếp theo', 'câu hỏi gợi ý', 'bạn có thể hỏi tiếp', 'suggested follow-up']):
        return None

    lines = text.strip().split('\n')
    suggestions = []
    for line in lines:
        cleaned = line.strip()
        m = re.match(r'^(?:\d+[\.\)]|[-*•])\s*(?:`|"|“)?([^`"\n]+)(?:`|"|”)?$', cleaned)
        if m:
            item = m.group(1).strip()
            if len(item) > 3 and not any(k in item.lower() for k in ['gợi ý', 'tiếp theo', 'câu hỏi']):
                suggestions.append(item)

    if suggestions:
        return {
            'type': 'suggestion',
            'title': 'Gợi ý tương tác tiếp theo',
            'items': suggestions[:6],
            'raw': text.strip()
        }
    return None

def parse_key_value(text: str) -> Optional[Dict[str, Any]]:
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    if len(lines) < 2:
        return None

    items = []
    current_key = None
    current_val = []

    for line in lines:
        if re.match(r'^[—\-_=]{3,}$', line):
            continue

        m = re.match(r'^(?:[-*•]\s*)?\*?\*?([^:\n]{2,50})\*?\*?\s*:\s*(.*)$', line)
        if m:
            if current_key:
                items.append({'key': current_key, 'value': ' '.join(current_val).strip()})
            current_key = m.group(1).strip().replace('**', '').replace('*', '')
            val_part = m.group(2).strip()
            current_val = [val_part] if val_part else []
        else:
            if current_key:
                current_val.append(line)
            else:
                return None

    if current_key:
        items.append({'key': current_key, 'value': ' '.join(current_val).strip()})

    if len(items) >= 2:
        return {
            'type': 'key_value',
            'title': 'Thông số & Metadata',
            'items': items,
            'raw': text.strip()
        }
    return None

def parse_citations_block(text: str) -> Optional[Dict[str, Any]]:
    if 'nguồn tìm kiếm' not in text.lower() and 'search sources' not in text.lower() and 'nguồn tham khảo' not in text.lower():
        return None

    lines = text.strip().split('\n')
    sources = []
    for line in lines:
        matches = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', line)
        for title, url in matches:
            domain = extract_domain(url)
            sources.append({
                'title': title.strip(),
                'url': url.strip(),
                'domain': domain
            })

    if sources:
        return {
            'type': 'citations',
            'title': 'Nguồn tham khảo từ Web',
            'sources': sources,
            'raw': text.strip()
        }
    return None

def parse_response_to_blocks(
    raw_text: str,
    thoughts: Optional[List[str]] = None,
    grounding_sources: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []

    # 1. Native Thoughts
    if thoughts:
        combined_thoughts = '\n\n'.join([t.strip() for t in thoughts if t and t.strip()]).strip()
        if combined_thoughts:
            blocks.append({
                'type': 'thought',
                'title': 'Quá trình suy luận (Thinking Process)',
                'content': combined_thoughts
            })

    # 2. Inline think tags
    clean_text = raw_text or ''
    think_tags_match = re.findall(r'<(?:think|thought)>([\s\S]*?)</(?:think|thought)>', clean_text, re.IGNORECASE)
    if think_tags_match:
        for t_content in think_tags_match:
            t_clean = t_content.strip()
            if t_clean:
                blocks.append({
                    'type': 'thought',
                    'title': 'Suy nghĩ & Phân tích nội bộ',
                    'content': t_clean
                })
        clean_text = re.sub(r'<(?:think|thought)>[\s\S]*?</(?:think|thought)>', '', clean_text, flags=re.IGNORECASE).strip()

    if not clean_text:
        return blocks

    # 3. Tokenize code and math blocks (lang cannot contain newline)
    special_pattern = re.compile(
        r'(?P<code>```(?P<lang>[^\n]*)\n(?P<code_content>[\s\S]*?)```)|'
        r'(?P<math>\$\$(?P<math_content>[\s\S]*?)\$\$)',
        re.MULTILINE
    )

    chunks = []
    last_end = 0
    for match in special_pattern.finditer(clean_text):
        start, end = match.span()
        if start > last_end:
            chunks.append(('text', clean_text[last_end:start]))

        if match.group('code') is not None:
            raw_lang_str = (match.group('lang') or '').strip()
            code_content = match.group('code_content') or ''
            lang = raw_lang_str
            filename = None
            if ':' in raw_lang_str:
                parts = raw_lang_str.split(':', 1)
                lang = parts[0].strip()
                filename = parts[1].strip()
            elif 'title="' in raw_lang_str:
                m_title = re.search(r'title="([^"]+)"', raw_lang_str)
                if m_title:
                    filename = m_title.group(1)
                    lang = re.sub(r'title="[^"]+"', '', raw_lang_str).strip()

            chunks.append(('code_block', {
                'raw': match.group('code'),
                'language': lang or 'text',
                'filename': filename,
                'content': code_content.rstrip()
            }))
        elif match.group('math') is not None:
            math_content = match.group('math_content') or ''
            chunks.append(('math_block', {
                'raw': match.group('math'),
                'formula': math_content.strip()
            }))

        last_end = end

    if last_end < len(clean_text):
        chunks.append(('text', clean_text[last_end:]))

    # 4. Process each chunk
    for chunk_type, chunk_val in chunks:
        if chunk_type == 'code_block':
            lang = (chunk_val['language'] or 'text').lower()
            code_str = chunk_val['content']
            lines_count = len(code_str.split('\n')) if code_str else 0

            if lang in ['mermaid', 'graphviz', 'dot', 'plantuml']:
                blocks.append({
                    'type': 'diagram',
                    'diagram_type': lang,
                    'code': code_str,
                    'title': chunk_val.get('filename') or f'Sơ đồ {lang.capitalize()}',
                    'raw': chunk_val['raw']
                })
            else:
                blocks.append({
                    'type': 'code',
                    'language': chunk_val['language'] or 'text',
                    'filename': chunk_val.get('filename'),
                    'content': code_str,
                    'lines_count': lines_count,
                    'raw': chunk_val['raw']
                })
        elif chunk_type == 'math_block':
            blocks.append({
                'type': 'math',
                'formula': chunk_val['formula'],
                'display': True,
                'raw': chunk_val['raw']
            })
        elif chunk_type == 'text':
            raw_chunk_text = chunk_val
            paragraphs = re.split(r'\n\s*\n', raw_chunk_text)

            for para in paragraphs:
                p = para.strip()
                if not p:
                    continue

                if '|' in p and ('\n' in p):
                    table_obj = parse_markdown_table(p)
                    if table_obj:
                        blocks.append({
                            'type': 'table',
                            **table_obj
                        })
                        continue

                if p.startswith('>'):
                    callout_obj = parse_callout(p)
                    if callout_obj:
                        blocks.append(callout_obj)
                        continue

                    quote_lines = [re.sub(r'^>\s?', '', l) for l in p.split('\n')]
                    blocks.append({
                        'type': 'quote',
                        'content': '\n'.join(quote_lines).strip(),
                        'raw': p
                    })
                    continue

                citations_obj = parse_citations_block(p)
                if citations_obj:
                    blocks.append(citations_obj)
                    continue

                suggestions_obj = parse_suggestions(p)
                if suggestions_obj:
                    blocks.append(suggestions_obj)
                    continue

                task_list_obj = parse_task_list(p)
                if task_list_obj:
                    blocks.append(task_list_obj)
                    continue

                key_value_obj = parse_key_value(p)
                if key_value_obj:
                    blocks.append(key_value_obj)
                    continue

                img_match = re.match(r'^!\[([^\]]*)\]\((https?://[^\)]+)\)(?:\s*\n\*(.*?)\*)?$', p)
                if img_match:
                    blocks.append({
                        'type': 'image',
                        'alt': img_match.group(1) or 'Image',
                        'url': img_match.group(2),
                        'caption': img_match.group(3) or img_match.group(1),
                        'raw': p
                    })
                    continue

                blocks.append({
                    'type': 'text',
                    'content': p
                })

    if grounding_sources and not any(b['type'] == 'citations' for b in blocks):
        sources = []
        for s in grounding_sources:
            u = s.get('url') or s.get('uri')
            if u:
                sources.append({
                    'title': s.get('title') or 'Nguồn tham khảo',
                    'url': u,
                    'domain': extract_domain(u),
                    'snippet': s.get('snippet')
                })
        if sources:
            blocks.append({
                'type': 'citations',
                'title': 'Nguồn tìm kiếm từ Google',
                'sources': sources
            })

    return blocks
