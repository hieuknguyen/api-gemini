"""
Docx Exporter Module - Phiên bản Nâng Cao Chuyên Sâu cho Bài Viết Chuẩn SEO
Chuyển đổi nội dung văn bản Markdown thành file Microsoft Word (.docx) chuyên nghiệp:
- Tự động loại bỏ câu chào hỏi, dẫn dắt mở đầu của AI (bắt đầu ngay từ Meta Description / Tiêu đề)
- Khối Meta Description được đóng khung chuyên biệt (Callout box) sang trọng
- Tiêu đề Heading 1 (18pt Navy), Heading 2 (14pt Blue), Heading 3 (12.5pt Dark Slate)
- Chuyển đổi bảng Markdown (| col | col |) thành Bảng Word chuẩn đẹp (Header màu xanh, viền thanh mảnh, so le màu dòng)
- Tự động làm sạch công thức toán LaTeX (\times 2 -> × 2, $1000$ -> 1000)
- Danh sách gạch đầu dòng (List Bullet với •, -, *), danh sách thứ tự (List Number với 1., 2.)
- Hộp vị trí ảnh chuẩn SEO (Đóng khung 📷 VỊ TRÍ CHÈN ẢNH, Chú thích ảnh in nghiêng, Tên file SEO font Consolas)
- Khối lưu ý, mẹo nhỏ (💡 Mẹo, ⚠️ Lưu ý, Trích dẫn >)
- Định dạng inline: **in đậm**, *in nghiêng*, <u>gạch chân</u>, `mã code`
- Căn lề chuẩn 1 inch (2.54 cm), font chữ 12pt, căn đều hai bên (Justified) theo đúng tiêu chuẩn
"""

import io
import re
from typing import Optional, List
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def clean_latex_math(text: str) -> str:
    """Thay thế các ký hiệu LaTeX thường gặp thành ký tự Unicode sạch đẹp."""
    math_symbols = [
        (r'\times', '×'),
        ('\t' + 'imes', '×'),
        (r'\div', '÷'),
        (r'\pm', '±'),
        (r'\le', '≤'),
        (r'\ge', '≥'),
        (r'\approx', '≈'),
        (r'\ne', '≠'),
        (r'\neq', '≠'),
        (r'\cdot', '·'),
        (r'\bullet', '•'),
        (r'\infty', '∞'),
        (r'\alpha', 'α'),
        (r'\beta', 'β'),
        (r'\rightarrow', '→'),
        (r'\leftarrow', '←'),
        (r'\Rightarrow', '⇒'),
        (r'\Leftarrow', '⇐'),
    ]
    for pat, rep in math_symbols:
        text = text.replace(pat, rep)
    
    text = re.sub(r'\$([^\$]+)\$', r'\1', text)
    return text

def strip_introductory_chitchat(lines: List[str]) -> List[str]:
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r'^(#+\s*)?(Meta\s*Description|Mô\s*tả\s*Meta|Meta\s*:)', stripped, re.IGNORECASE):
            start_idx = i
            break
        if re.match(r'^[—–\-_=]{3,}$', stripped):
            found_meta = False
            for j in range(i + 1, min(len(lines), i + 4)):
                next_str = lines[j].strip()
                if re.match(r'^(#+\s*)?(Meta\s*Description|Mô\s*tả\s*Meta|Meta\s*:)', next_str, re.IGNORECASE):
                    start_idx = j
                    found_meta = True
                    break
            if found_meta:
                break
        if stripped.startswith('# '):
            start_idx = i
            break
        is_chitchat = bool(re.match(
            r'^(dưới đây là|sau đây là|chào bạn|xin chào|tôi xin gửi|đây là bài viết|bài viết dưới đây|dưới đây tôi|sau đây tôi)',
            stripped,
            re.IGNORECASE
        ))
        if not is_chitchat and not stripped.startswith('—') and not stripped.startswith('-'):
            start_idx = i
            break
    return lines[start_idx:]

def set_cell_background(cell, fill_hex: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=110, bottom=110, left=140, right=140):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_table_borders(table, color="CBD5E1", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def render_image_box(doc, title: str, caption: Optional[str] = None, filename: Optional[str] = None):
    """Tạo hộp vị trí chèn ảnh chuẩn SEO (Image Placeholder Card) chuyên nghiệp."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = tbl.cell(0, 0)
    
    tcPr = c._tc.get_or_add_tcPr()
    tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="F0F9FF"/>'))
    tcPr.append(parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="6" w:space="0" w:color="93C5FD"/>'
        f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="93C5FD"/>'
        f'<w:left w:val="single" w:sz="6" w:space="0" w:color="93C5FD"/>'
        f'<w:right w:val="single" w:sz="6" w:space="0" w:color="93C5FD"/>'
        f'</w:tcBorders>'
    ))
    set_cell_margins(c, top=130, bottom=130, left=180, right=180)
    
    # Tiêu đề vị trí ảnh
    p1 = c.paragraphs[0]
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_before = Pt(2)
    p1.paragraph_format.space_after = Pt(2)
    r1 = p1.add_run(f"📷 [VỊ TRÍ CHÈN ẢNH] — {title}")
    r1.bold = True
    r1.font.name = 'Calibri'
    r1.font.size = Pt(11)
    r1.font.color.rgb = RGBColor(0x1D, 0x4E, 0xD8)  # Royal Blue
    
    # Chú thích ảnh nếu có
    if caption:
        p2 = c.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_before = Pt(1)
        p2.paragraph_format.space_after = Pt(2)
        r2_lbl = p2.add_run("Chú thích ảnh: ")
        r2_lbl.bold = True
        r2_lbl.font.size = Pt(10)
        r2_lbl.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
        r2_val = p2.add_run(caption)
        r2_val.italic = True
        r2_val.font.size = Pt(10)
        r2_val.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
        
    # Tên file ảnh SEO nếu có
    if filename:
        p3 = c.add_paragraph()
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p3.paragraph_format.space_before = Pt(1)
        p3.paragraph_format.space_after = Pt(2)
        r3_lbl = p3.add_run("Tên file SEO: ")
        r3_lbl.font.size = Pt(9.5)
        r3_lbl.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
        r3_val = p3.add_run(filename)
        r3_val.font.name = 'Consolas'
        r3_val.font.size = Pt(9.5)
        r3_val.font.color.rgb = RGBColor(0x25, 0x63, 0xEB)
        
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(0)
    p_sp.paragraph_format.space_after = Pt(6)

def add_inline_formatted_text(p, text: str, default_font_size=Pt(12), default_color=RGBColor(0x1F, 0x29, 0x37)):
    text = clean_latex_math(text)
    pattern = r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|<u>.*?</u>|<b>.*?</b>|<strong>.*?</strong>|<i>.*?</i>|<em>.*?</em>)'
    tokens = re.split(pattern, text)
    
    for t in tokens:
        if not t:
            continue
        
        bold = False
        italic = False
        underline = False
        is_code = False
        content = t
        
        if t.startswith('**') and t.endswith('**') and len(t) >= 4:
            bold = True
            content = t[2:-2]
        elif t.startswith('*') and t.endswith('*') and len(t) >= 2:
            italic = True
            content = t[1:-1]
        elif t.startswith('`') and t.endswith('`') and len(t) >= 2:
            is_code = True
            content = t[1:-1]
        elif t.lower().startswith('<u>') and t.lower().endswith('</u>'):
            underline = True
            content = t[3:-4]
        elif t.lower().startswith('<b>') and t.lower().endswith('</b>'):
            bold = True
            content = t[3:-4]
        elif t.lower().startswith('<strong>') and t.lower().endswith('</strong>'):
            bold = True
            content = t[8:-9]
        elif t.lower().startswith('<i>') and t.lower().endswith('</i>'):
            italic = True
            content = t[3:-4]
        elif t.lower().startswith('<em>') and t.lower().endswith('</em>'):
            italic = True
            content = t[4:-5]
            
        r = p.add_run(content)
        r.font.name = 'Calibri'
        r.font.size = default_font_size
        r.font.color.rgb = default_color
        
        if bold:
            r.bold = True
        if italic:
            r.italic = True
        if underline:
            r.underline = True
        if is_code:
            r.font.name = 'Consolas'
            r.font.size = Pt(10.5)
            r.font.color.rgb = RGBColor(0x7C, 0x3A, 0xED)

def markdown_to_docx(md_text: str, doc_title: Optional[str] = None) -> io.BytesIO:
    doc = docx.Document()

    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(12)
    normal_style.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)

    raw_lines = (md_text or '').splitlines()
    lines = strip_introductory_chitchat(raw_lines)

    i = 0
    n = len(lines)
    in_code_block = False
    code_lines = []
    is_first_content_heading = True

    if len(doc.paragraphs) > 0 and not doc.paragraphs[0].text:
        p_first = doc.paragraphs[0]._element
        p_first.getparent().remove(p_first)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # 1. Code Block
        if stripped.startswith('```'):
            if in_code_block:
                code_text = '\n'.join(code_lines)
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.3)
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(4)
                r = p.add_run(code_text)
                r.font.name = 'Consolas'
                r.font.size = Pt(10)
                r.font.color.rgb = RGBColor(0x37, 0x41, 0x51)
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
                code_lines = []
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        if not stripped:
            i += 1
            continue

        # 2. Divider
        if re.match(r'^[—–\-_=]{3,}$', stripped):
            i += 1
            continue

        # 3. Table Markdown
        if stripped.startswith('|') and stripped.endswith('|'):
            table_lines = []
            while i < n and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            
            if len(table_lines) >= 2:
                headers = [c.strip() for c in table_lines[0].strip('|').split('|')]
                alignments = []
                
                data_start_idx = 1
                if len(table_lines) > 1 and re.match(r'^[|\s:\-]+$', table_lines[1]):
                    sep_cells = [c.strip() for c in table_lines[1].strip('|').split('|')]
                    for sc in sep_cells:
                        if sc.startswith(':') and sc.endswith(':'):
                            alignments.append(WD_ALIGN_PARAGRAPH.CENTER)
                        elif sc.endswith(':'):
                            alignments.append(WD_ALIGN_PARAGRAPH.RIGHT)
                        else:
                            alignments.append(WD_ALIGN_PARAGRAPH.LEFT)
                    data_start_idx = 2
                else:
                    alignments = [WD_ALIGN_PARAGRAPH.LEFT] * len(headers)

                rows_data = []
                for row_str in table_lines[data_start_idx:]:
                    cells = [clean_latex_math(c.strip()) for c in row_str.strip('|').split('|')]
                    while len(cells) < len(headers):
                        cells.append('')
                    rows_data.append(cells[:len(headers)])

                table = doc.add_table(rows=len(rows_data) + 1, cols=len(headers))
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                set_table_borders(table)

                hdr_cells = table.rows[0].cells
                for col_idx, heading_text in enumerate(headers):
                    hdr_cells[col_idx].text = ""
                    p = hdr_cells[col_idx].paragraphs[0]
                    p.paragraph_format.space_before = Pt(4)
                    p.paragraph_format.space_after = Pt(4)
                    align = alignments[col_idx] if col_idx < len(alignments) else WD_ALIGN_PARAGRAPH.LEFT
                    p.alignment = align
                    add_inline_formatted_text(p, heading_text, default_font_size=Pt(11), default_color=RGBColor(0xFF, 0xFF, 0xFF))
                    for r in p.runs:
                        r.bold = True
                    set_cell_background(hdr_cells[col_idx], "1E40AF")
                    set_cell_margins(hdr_cells[col_idx], top=120, bottom=120, left=140, right=140)

                for row_idx, row_vals in enumerate(rows_data):
                    row_cells = table.rows[row_idx + 1].cells
                    bg_color = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
                    for col_idx, val in enumerate(row_vals):
                        row_cells[col_idx].text = ""
                        p = row_cells[col_idx].paragraphs[0]
                        p.paragraph_format.space_before = Pt(3)
                        p.paragraph_format.space_after = Pt(3)
                        align = alignments[col_idx] if col_idx < len(alignments) else WD_ALIGN_PARAGRAPH.LEFT
                        p.alignment = align
                        add_inline_formatted_text(p, val, default_font_size=Pt(11), default_color=RGBColor(0x33, 0x41, 0x55))
                        set_cell_background(row_cells[col_idx], bg_color)
                        set_cell_margins(row_cells[col_idx], top=100, bottom=100, left=140, right=140)

                doc.add_paragraph().paragraph_format.space_after = Pt(6)
            continue

        # 4. Khối Meta Description
        if re.match(r'^(#+\s*)?(Meta\s*Description|Mô\s*tả\s*Meta|Meta\s*:)', stripped, re.IGNORECASE):
            meta_label = stripped.lstrip('#').strip()
            meta_content = ""
            i += 1
            while i < n:
                next_line = lines[i].strip()
                if not next_line:
                    i += 1
                    continue
                if re.match(r'^[—–\-_=]{3,}$', next_line):
                    i += 1
                    break
                meta_content = next_line
                i += 1
                break

            tbl = doc.add_table(rows=1, cols=1)
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            c = tbl.cell(0, 0)
            set_cell_background(c, "F1F5F9")
            set_cell_margins(c, top=140, bottom=140, left=180, right=180)
            
            p_label = c.paragraphs[0]
            p_label.paragraph_format.space_before = Pt(2)
            p_label.paragraph_format.space_after = Pt(2)
            r_icon = p_label.add_run("📌 ")
            r_lbl = p_label.add_run(meta_label)
            r_lbl.bold = True
            r_lbl.font.size = Pt(11)
            r_lbl.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

            if meta_content:
                p_desc = c.add_paragraph()
                p_desc.paragraph_format.space_before = Pt(2)
                p_desc.paragraph_format.space_after = Pt(4)
                p_desc.paragraph_format.line_spacing = 1.15
                add_inline_formatted_text(p_desc, meta_content, default_font_size=Pt(11.5), default_color=RGBColor(0x47, 0x55, 0x69))
                for r in p_desc.runs:
                    r.italic = True

            p_space = doc.add_paragraph()
            p_space.paragraph_format.space_after = Pt(6)
            continue

        # 5. CỤM THÔNG TIN ẢNH (Image Placeholder Card)
        is_img_md = bool(re.match(r'^!\[(.*?)\]\((.*?)\)$', stripped))
        is_img_c = bool(re.match(r'^<!--\s*\[(.*?)\]:?\s*(.*?)\s*-->$', stripped))
        is_img_b = bool(re.match(r'^\[(?:VỊ\s*TRÍ\s*)?ẢNH\s*.*?:?\]?', stripped, re.IGNORECASE))
        is_caption = bool(
            re.match(r'^\((?:Hình ảnh minh họa|Ảnh minh họa|Minh họa|Chú thích):?.*?\)$', stripped, re.IGNORECASE) or
            stripped.lower().startswith('<p align="center">')
        )
        is_file = stripped.lower().startswith(("tên file ảnh:", "tên ảnh:", "tên file:", "kích thước:"))

        if is_img_md or is_img_c or is_img_b or is_caption or is_file:
            img_title = ""
            img_caption = ""
            img_filename = ""

            while i < n:
                cur_line = lines[i].strip()
                if not cur_line:
                    if i + 1 < n:
                        next_peek = lines[i + 1].strip()
                        if (re.match(r'^!\[(.*?)\]\((.*?)\)$', next_peek) or
                            re.match(r'^\((?:Hình ảnh minh họa|Ảnh minh họa|Minh họa|Chú thích):?.*?\)$', next_peek, re.IGNORECASE) or
                            next_peek.lower().startswith(('<p align="center">', "tên file ảnh:", "tên ảnh:", "tên file:", "kích thước:"))):
                            i += 1
                            continue
                    break

                m_md = re.match(r'^!\[(.*?)\]\((.*?)\)$', cur_line)
                m_c = re.match(r'^<!--\s*\[(.*?)\]:?\s*(.*?)\s*-->$', cur_line)
                m_b = re.match(r'^\[((?:VỊ\s*TRÍ\s*)?ẢNH\s*.*?)\]:?\s*(.*)$', cur_line, re.IGNORECASE)
                m_cap = re.match(r'^\((?:Hình ảnh minh họa|Ảnh minh họa|Minh họa|Chú thích):?\s*(.*?)\)$', cur_line, re.IGNORECASE)

                if m_md:
                    alt_t, url_t = m_md.groups()
                    if not img_title:
                        img_title = alt_t.strip()
                    if not img_filename:
                        img_filename = url_t.strip()
                    i += 1
                elif m_c:
                    tag, desc = m_c.groups()
                    img_title = f"{tag}: {desc}" if desc else tag
                    i += 1
                elif m_b:
                    tag, desc = m_b.groups()
                    img_title = f"{tag}: {desc}" if desc else tag
                    i += 1
                elif m_cap:
                    img_caption = m_cap.group(1).strip()
                    i += 1
                elif cur_line.lower().startswith('<p align="center">'):
                    cleaned_cap = re.sub(r'</?[a-zA-Z0-9="\'\s_-]+>', '', cur_line).strip()
                    if cleaned_cap:
                        img_caption = cleaned_cap
                    i += 1
                elif cur_line.lower().startswith(("tên file ảnh:", "tên ảnh:", "tên file:")):
                    img_filename = re.sub(r'^(?:tên file ảnh|tên ảnh|tên file):\s*', '', cur_line, flags=re.IGNORECASE).strip()
                    i += 1
                elif cur_line.lower().startswith("kích thước:"):
                    # Thông số kích thước ảnh (bỏ qua hoặc giữ lại nếu chưa có file)
                    i += 1
                else:
                    break

            render_image_box(doc, img_title or "Minh Họa Chuẩn SEO", img_caption or None, img_filename or None)
            continue

        # 6. Danh sách gạch đầu dòng
        if re.match(r'^[•–\-\*\+]\s+', stripped) or stripped.startswith(('•\t', '• ')):
            content_list = re.sub(r'^[•–\-\*\+]\s*', '', stripped).strip()
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.15
            add_inline_formatted_text(p, content_list, default_font_size=Pt(12), default_color=RGBColor(0x1F, 0x29, 0x37))
            i += 1
            continue

        # 7. Danh sách số thứ tự
        if re.match(r'^\d+[\.\)]\s+', stripped):
            num_match = re.match(r'^\d+[\.\)]\s+', stripped)
            content_list = stripped[len(num_match.group(0)):].strip()
            p = doc.add_paragraph(style='List Number')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.15
            add_inline_formatted_text(p, content_list, default_font_size=Pt(12), default_color=RGBColor(0x1F, 0x29, 0x37))
            i += 1
            continue

        # 8. Callout / Mẹo nhỏ / Lưu ý
        if stripped.startswith('> ') or stripped.startswith(('💡', '📌', '⚠️', 'Lưu ý quan trọng:', 'Lưu ý:')):
            callout_text = stripped[2:].strip() if stripped.startswith('> ') else stripped
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.35)
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.2
            add_inline_formatted_text(p, callout_text, default_font_size=Pt(11.5), default_color=RGBColor(0x33, 0x41, 0x55))
            i += 1
            continue

        # 9. Headings
        is_h1 = stripped.startswith('# ')
        is_h2 = stripped.startswith('## ')
        is_h3 = stripped.startswith('### ')
        
        clean_text = stripped.lstrip('#').strip()
        auto_heading = False
        auto_level = 2

        # Loại trừ tuyệt đối các dòng không phải tiêu đề
        is_not_heading = (
            any(kw in clean_text.lower() for kw in [
                'tên file', 'tên ảnh', 'file ảnh', '.jpg', '.png', '.webp', '.jpeg',
                'hình ảnh minh họa', 'chú thích ảnh', 'http://', 'https://'
            ]) or
            clean_text.startswith(('(', '[', '{', '<', '<!--', '-->'))
        )

        if not (is_h1 or is_h2 or is_h3) and not is_not_heading:
            if len(clean_text) <= 90 and not clean_text.endswith(('.', ',', ';')):
                if is_first_content_heading:
                    auto_heading = True
                    auto_level = 1
                elif clean_text.endswith('?') or len(clean_text) <= 65:
                    auto_heading = True
                    if clean_text.lower().startswith(('nhóm', 'chiến thuật', 'phương pháp', 'cách', 'bước', 'đặc điểm', 'ưu điểm')):
                        auto_level = 3
                    else:
                        auto_level = 2

        if is_h1 or (auto_heading and auto_level == 1):
            h = doc.add_paragraph()
            h.paragraph_format.space_before = Pt(18)
            h.paragraph_format.space_after = Pt(8)
            h.paragraph_format.keep_with_next = True
            add_inline_formatted_text(h, clean_text, default_font_size=Pt(18), default_color=RGBColor(0x1E, 0x3A, 0x8A))
            for r in h.runs:
                r.bold = True
            is_first_content_heading = False
            i += 1
            continue

        if is_h2 or (auto_heading and auto_level == 2):
            h = doc.add_paragraph()
            h.paragraph_format.space_before = Pt(14)
            h.paragraph_format.space_after = Pt(6)
            h.paragraph_format.keep_with_next = True
            add_inline_formatted_text(h, clean_text, default_font_size=Pt(14.5), default_color=RGBColor(0x1D, 0x4E, 0xD8))
            for r in h.runs:
                r.bold = True
            is_first_content_heading = False
            i += 1
            continue

        if is_h3 or (auto_heading and auto_level == 3):
            h = doc.add_paragraph()
            h.paragraph_format.space_before = Pt(10)
            h.paragraph_format.space_after = Pt(4)
            h.paragraph_format.keep_with_next = True
            add_inline_formatted_text(h, clean_text, default_font_size=Pt(13), default_color=RGBColor(0x0F, 0x17, 0x2A))
            for r in h.runs:
                r.bold = True
            is_first_content_heading = False
            i += 1
            continue

        # 10. Normal Paragraph
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.2
        add_inline_formatted_text(p, stripped, default_font_size=Pt(12), default_color=RGBColor(0x1F, 0x29, 0x37))
        is_first_content_heading = False
        i += 1

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

