"""
File Processor Module
Xử lý tất cả loại tài liệu cho AI:
- File Gemini đọc được trực tiếp (ảnh, PDF, audio, video, text) → gửi inlineData
- File Gemini không đọc được (DOCX, XLSX, PPTX, ...) → chuyển đổi thành text cho AI đọc
"""

import os
import base64
import io
import re
import logging
import mimetypes
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List

logger = logging.getLogger("antigravity-files")

# MIME types mà Gemini API hỗ trợ đọc trực tiếp qua inlineData (Chỉ các định dạng nhị phân/multimodal)
GEMINI_NATIVE_MIMES = {
    # Ảnh
    "image/png", "image/jpeg", "image/gif", "image/webp",
    "image/heic", "image/heif", "image/bmp",
    # PDF
    "application/pdf",
    # Audio
    "audio/wav", "audio/mp3", "audio/mpeg", "audio/aiff",
    "audio/aac", "audio/ogg", "audio/flac", "audio/x-wav",
    # Video
    "video/mp4", "video/mpeg", "video/mov", "video/avi",
    "video/x-flv", "video/mpg", "video/webm", "video/wmv", "video/3gpp",
    "video/quicktime",
}

# Mapping extension → MIME type cho các file phổ biến
EXTENSION_MIME_MAP = {
    # Ảnh
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
    ".heic": "image/heic", ".heif": "image/heif", ".svg": "image/svg+xml",
    # Tài liệu
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".rtf": "application/rtf",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    # Text
    ".txt": "text/plain", ".md": "text/markdown", ".csv": "text/csv",
    ".json": "application/json", ".xml": "application/xml",
    ".html": "text/html", ".htm": "text/html",
    ".css": "text/css", ".js": "text/javascript", ".ts": "text/x-typescript",
    ".py": "text/x-python", ".java": "text/x-java",
    ".c": "text/x-c", ".cpp": "text/x-c++", ".h": "text/x-c",
    ".cs": "text/x-csharp", ".go": "text/x-go", ".rs": "text/x-rust",
    ".rb": "text/x-ruby", ".php": "text/x-php", ".swift": "text/x-swift",
    ".kt": "text/x-kotlin", ".dart": "text/x-dart",
    ".sql": "text/x-sql", ".sh": "text/x-sh", ".bat": "text/x-bat",
    ".yaml": "text/yaml", ".yml": "text/yaml", ".toml": "text/x-toml",
    ".ini": "text/plain", ".cfg": "text/plain", ".conf": "text/plain",
    ".log": "text/plain", ".env": "text/plain",
    # Audio
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
    ".flac": "audio/flac", ".aac": "audio/aac", ".m4a": "audio/mp4",
    # Video
    ".mp4": "video/mp4", ".avi": "video/avi", ".mov": "video/quicktime",
    ".wmv": "video/wmv", ".webm": "video/webm", ".mkv": "video/x-matroska",
    ".flv": "video/x-flv",
}

# Magic bytes để detect MIME type từ binary data
MAGIC_BYTES = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),  # RIFF....WEBP
    (b"%PDF", "application/pdf"),
    (b"PK\x03\x04", "application/zip"),  # ZIP-based (docx, xlsx, pptx, odt, ods)
    (b"\xd0\xcf\x11\xe0", "application/x-ole2"),  # OLE2 (doc, xls, ppt cũ)
    (b"ID3", "audio/mpeg"),  # MP3 with ID3
    (b"\xff\xfb", "audio/mpeg"),  # MP3
    (b"\xff\xf3", "audio/mpeg"),  # MP3
    (b"\xff\xf2", "audio/mpeg"),  # MP3
    (b"fLaC", "audio/flac"),
    (b"OggS", "audio/ogg"),
    (b"RIFF", "audio/wav"),  # RIFF....WAVE
    (b"\x00\x00\x00\x18ftypmp4", "video/mp4"),
    (b"\x00\x00\x00\x1cftypmp4", "video/mp4"),
    (b"\x00\x00\x00\x20ftyp", "video/mp4"),
    (b"\x1a\x45\xdf\xa3", "video/webm"),  # EBML (webm/mkv)
    (b"{\\rtf", "application/rtf"),
]

# Các extension thuộc ZIP-based document
ZIP_DOC_EXTENSIONS = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
}


def detect_mime_from_bytes(data_bytes: bytes) -> str:
    """Detect MIME type từ magic bytes của file binary."""
    for magic, mime in MAGIC_BYTES:
        if data_bytes[:len(magic)] == magic:
            # Phân biệt RIFF (WEBP vs WAV)
            if magic == b"RIFF" and len(data_bytes) > 11:
                if data_bytes[8:12] == b"WEBP":
                    return "image/webp"
                elif data_bytes[8:12] == b"WAVE":
                    return "audio/wav"
            return mime
    return ""


def detect_mime_from_extension(filename: str) -> str:
    """Detect MIME type từ phần mở rộng file."""
    if not filename:
        return ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return EXTENSION_MIME_MAP.get(ext, mimetypes.guess_type(filename)[0] or "")


def parse_file_data(raw_data: str) -> Tuple[str, bytes, str]:
    """
    Parse dữ liệu file từ client (data URI hoặc raw base64).
    Returns: (mime_type, raw_bytes, base64_string)
    """
    raw_data = raw_data.strip()

    # Trường hợp 1: Data URI format "data:mime;base64,..."
    match = re.match(r"^data:([^;,]+)?(?:;charset=[^;,]+)?;base64,(.*)$", raw_data, re.DOTALL)
    if match:
        mime = (match.group(1) or "").strip()
        b64_str = (match.group(2) or "").strip()
        try:
            raw_bytes = base64.b64decode(b64_str) if b64_str else b""
        except Exception:
            raw_bytes = b""
        return mime, raw_bytes, b64_str

    # Trường hợp 2: Có tiền tố data: nhưng format biến thể
    if raw_data.startswith("data:"):
        parts = raw_data.split(",", 1)
        mime = parts[0].split(";")[0].replace("data:", "").strip() if ";" in parts[0] else "application/octet-stream"
        b64_str = parts[1].strip() if len(parts) > 1 else ""
        try:
            raw_bytes = base64.b64decode(b64_str) if b64_str else b""
        except Exception:
            raw_bytes = b""
        return mime, raw_bytes, b64_str

    # Trường hợp 3: Raw base64 string
    try:
        raw_bytes = base64.b64decode(raw_data)
    except Exception:
        raw_bytes = b""

    # Detect từ magic bytes
    detected = detect_mime_from_bytes(raw_bytes) if raw_bytes else ""
    if not detected:
        # Fallback: detect từ base64 prefix patterns
        if raw_data.startswith("iVBORw0KGgo"):
            detected = "image/png"
        elif raw_data.startswith("/9j/"):
            detected = "image/jpeg"
        elif raw_data.startswith("R0lGOD"):
            detected = "image/gif"
        elif raw_data.startswith("UklGR"):
            detected = "image/webp"
        elif raw_data.startswith("JVBERi"):
            detected = "application/pdf"
        else:
            detected = "application/octet-stream"

    return detected, raw_bytes, raw_data


def is_gemini_native(mime_type: str) -> bool:
    """Kiểm tra xem Gemini có đọc được MIME type này trực tiếp không."""
    if mime_type in GEMINI_NATIVE_MIMES:
        return True
    # Text-based files đều đọc được
    if mime_type.startswith("text/"):
        return True
    return False


def extract_text_from_docx(data_bytes: bytes) -> str:
    """Trích xuất text từ file DOCX."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(data_bytes))
        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text)

        # Trích xuất bảng
        for table in doc.tables:
            rows = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                rows.append(" | ".join(cells))
            if rows:
                paragraphs.append("\n" + "\n".join(rows))

        return "\n\n".join(paragraphs)
    except ImportError:
        logger.warning("Thư viện python-docx chưa được cài. Đang thử đọc XML trực tiếp...")
        return _extract_text_from_zip_xml(data_bytes, "word/document.xml")
    except Exception as e:
        logger.error(f"Lỗi đọc file DOCX: {e}")
        return f"[Lỗi đọc file DOCX: {e}]"


def extract_text_from_xlsx(data_bytes: bytes) -> str:
    """Trích xuất text từ file XLSX thành bảng markdown."""
    try:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data_bytes), read_only=True, data_only=True)
        result = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows_data = []
            for row in ws.iter_rows(values_only=True):
                cells = [str(c) if c is not None else "" for c in row]
                if any(c.strip() for c in cells):
                    rows_data.append(cells)

            if rows_data:
                result.append(f"### Sheet: {sheet_name}")
                # Format as markdown table
                if len(rows_data) > 0:
                    header = rows_data[0]
                    result.append("| " + " | ".join(header) + " |")
                    result.append("| " + " | ".join(["---"] * len(header)) + " |")
                    for row in rows_data[1:]:
                        # Pad row to match header length
                        padded = row + [""] * (len(header) - len(row))
                        result.append("| " + " | ".join(padded[:len(header)]) + " |")

        wb.close()
        return "\n\n".join(result)
    except ImportError:
        logger.warning("Thư viện openpyxl chưa được cài. Đang thử đọc XML trực tiếp...")
        return _extract_text_from_zip_xml(data_bytes, "xl/sharedStrings.xml")
    except Exception as e:
        logger.error(f"Lỗi đọc file XLSX: {e}")
        return f"[Lỗi đọc file XLSX: {e}]"


def extract_text_from_pptx(data_bytes: bytes) -> str:
    """Trích xuất text từ file PPTX."""
    try:
        from pptx import Presentation
        prs = Presentation(io.BytesIO(data_bytes))
        slides_text = []

        for i, slide in enumerate(prs.slides, 1):
            texts = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        txt = para.text.strip()
                        if txt:
                            texts.append(txt)
                if shape.has_table:
                    for row in shape.table.rows:
                        cells = [cell.text.strip() for cell in row.cells]
                        texts.append(" | ".join(cells))
            if texts:
                slides_text.append(f"### Slide {i}\n" + "\n".join(texts))

        return "\n\n".join(slides_text)
    except ImportError:
        logger.warning("Thư viện python-pptx chưa được cài. Đang thử đọc XML trực tiếp...")
        return _extract_text_from_zip_xml(data_bytes, "ppt/slides/slide")
    except Exception as e:
        logger.error(f"Lỗi đọc file PPTX: {e}")
        return f"[Lỗi đọc file PPTX: {e}]"


def extract_text_from_rtf(data_bytes: bytes) -> str:
    """Trích xuất text cơ bản từ file RTF."""
    try:
        text = data_bytes.decode("utf-8", errors="replace")
        # Loại bỏ RTF control codes cơ bản
        text = re.sub(r"\\[a-z]+\d*\s?", " ", text)
        text = re.sub(r"[{}]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception as e:
        return f"[Lỗi đọc file RTF: {e}]"


def extract_text_from_csv(data_bytes: bytes) -> str:
    """Đọc CSV và chuyển thành bảng markdown."""
    try:
        import csv
        text = data_bytes.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return ""

        result = []
        header = rows[0]
        result.append("| " + " | ".join(header) + " |")
        result.append("| " + " | ".join(["---"] * len(header)) + " |")
        for row in rows[1:]:
            padded = row + [""] * (len(header) - len(row))
            result.append("| " + " | ".join(padded[:len(header)]) + " |")

        return "\n".join(result)
    except Exception as e:
        return f"[Lỗi đọc file CSV: {e}]"


def _extract_text_from_zip_xml(data_bytes: bytes, target_path: str) -> str:
    """Fallback: đọc text từ file ZIP-based (docx/xlsx/pptx) bằng cách parse XML trực tiếp."""
    import zipfile
    try:
        with zipfile.ZipFile(io.BytesIO(data_bytes)) as zf:
            texts = []
            for name in zf.namelist():
                if name.startswith(target_path) and name.endswith(".xml"):
                    xml_content = zf.read(name).decode("utf-8", errors="replace")
                    # Loại bỏ XML tags, giữ text content
                    clean = re.sub(r"<[^>]+>", " ", xml_content)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    if clean:
                        texts.append(clean)
            return "\n\n".join(texts) if texts else "[Không trích xuất được nội dung từ file]"
    except Exception as e:
        return f"[Lỗi đọc file ZIP: {e}]"


def detect_zip_document_type(data_bytes: bytes, filename: str = "") -> str:
    """Phân biệt loại tài liệu ZIP-based (docx/xlsx/pptx) từ nội dung bên trong."""
    import zipfile
    try:
        # Ưu tiên dùng extension nếu có
        if filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext in ZIP_DOC_EXTENSIONS:
                return ZIP_DOC_EXTENSIONS[ext]

        with zipfile.ZipFile(io.BytesIO(data_bytes)) as zf:
            names = zf.namelist()
            if any(n.startswith("word/") for n in names):
                return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif any(n.startswith("xl/") for n in names):
                return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif any(n.startswith("ppt/") for n in names):
                return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    except Exception:
        pass
    return "application/zip"


def process_file(
    raw_data: str,
    filename: str = ""
) -> Dict[str, Any]:
    """
    Xử lý file từ client và trả về dict mô tả cách gửi cho AI.

    Returns dict với structure:
    - type: "inline" | "text_extract"
    - mime_type: str
    - filename: str
    Nếu type == "inline":
        - data: str (base64)
    Nếu type == "text_extract":
        - extracted_text: str
    """
    mime_type, raw_bytes, b64_str = parse_file_data(raw_data)

    # Refine MIME type dựa trên filename nếu có
    if filename:
        ext_mime = detect_mime_from_extension(filename)
        if ext_mime and (mime_type in ["application/octet-stream", "application/zip", ""] or
                         (mime_type == "application/zip" and ext_mime != "application/zip")):
            mime_type = ext_mime

    # Phân biệt ZIP-based documents
    if mime_type in ["application/zip", "application/octet-stream"] and raw_bytes[:4] == b"PK\x03\x04":
        mime_type = detect_zip_document_type(raw_bytes, filename)

    # OLE2 format (doc, xls, ppt cũ)
    if mime_type == "application/x-ole2":
        ext_mime = detect_mime_from_extension(filename) if filename else ""
        mime_type = ext_mime or "application/msword"

    result = {
        "mime_type": mime_type,
        "filename": filename,
    }

    # Nếu file rỗng (0 bytes) hoặc không có dữ liệu base64 hợp lệ
    if not raw_bytes or not b64_str:
        result["type"] = "text_extract"
        result["extracted_text"] = f"[File rỗng: `{filename or 'tập tin'}` (0 bytes)]"
        return result

    # Nếu Gemini đọc trực tiếp được (ảnh, PDF, audio, video) và có dữ liệu hợp lệ → gửi inlineData
    if is_gemini_native(mime_type) and b64_str and raw_bytes:
        result["type"] = "inline"
        result["data"] = b64_str
        logger.info(f"File '{filename}' ({mime_type}) → gửi trực tiếp cho AI (inlineData)")
        return result

    # Nếu không, chuyển đổi thành text
    result["type"] = "text_extract"
    extracted = ""

    if mime_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword"
    ]:
        extracted = extract_text_from_docx(raw_bytes)

    elif mime_type in [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel"
    ]:
        extracted = extract_text_from_xlsx(raw_bytes)

    elif mime_type in [
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint"
    ]:
        extracted = extract_text_from_pptx(raw_bytes)

    elif mime_type == "application/rtf":
        extracted = extract_text_from_rtf(raw_bytes)

    elif mime_type == "text/csv":
        extracted = extract_text_from_csv(raw_bytes)

    elif mime_type.startswith("text/") or mime_type in ["application/json", "application/xml", "application/yaml"]:
        # Text file thuần → đọc trực tiếp
        try:
            extracted = raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            extracted = "[Không đọc được nội dung text file]"

    elif mime_type in ["application/zip", "application/x-zip-compressed", "application/x-zip"] or (filename and filename.lower().endswith(".zip")):
        # ZIP archive của thư mục → giải nén và phân tích sâu toàn bộ file bên trong
        extracted = extract_zip_folder(raw_bytes, filename)

    else:
        # Loại không hỗ trợ → thử đọc như text
        try:
            text_attempt = raw_bytes.decode("utf-8", errors="strict")
            if text_attempt.strip():
                extracted = text_attempt
                logger.info(f"File '{filename}' ({mime_type}) đọc được như text thuần.")
            else:
                extracted = f"[File '{filename}' loại {mime_type} — AI không thể đọc trực tiếp nội dung binary này]"
        except (UnicodeDecodeError, Exception):
            extracted = f"[File '{filename}' loại {mime_type} — AI không thể đọc trực tiếp nội dung binary này]"

    result["extracted_text"] = extracted
    logger.info(f"File '{filename}' ({mime_type}) → đã trích xuất {len(extracted)} ký tự text")
    return result


# Danh sách thư mục và file rác/hệ thống cần bỏ qua khi quét thư mục hoặc giải nén ZIP
IGNORED_DIR_PATTERNS = {
    "node_modules", ".git", ".svn", ".hg", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".tox", ".venv", "venv", "env", "dist", "build",
    "out", ".next", ".nuxt", ".output", ".idea", ".vscode", "__macosx",
    "coverage", ".cache", "bin", "obj", ".cargo", "target"
}

IGNORED_FILE_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".exe", ".dll", ".so", ".dylib", ".bin",
    ".class", ".jar", ".war", ".ear", ".iso", ".tar", ".gz", ".7z",
    ".rar", ".dmg", ".pkg", ".ds_store", ".thumbs.db", ".lock"
}

SYNTAX_LANG_MAP = {
    ".py": "python", ".js": "javascript", ".jsx": "jsx", ".ts": "typescript",
    ".tsx": "tsx", ".html": "html", ".htm": "html", ".css": "css",
    ".scss": "scss", ".sass": "sass", ".less": "less", ".json": "json",
    ".xml": "xml", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".md": "markdown", ".sql": "sql", ".sh": "bash", ".bash": "bash",
    ".bat": "batch", ".ps1": "powershell", ".rs": "rust", ".go": "go",
    ".java": "java", ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
    ".cs": "csharp", ".php": "php", ".rb": "ruby", ".swift": "swift",
    ".kt": "kotlin", ".dart": "dart", ".r": "r", ".lua": "lua",
    ".ini": "ini", ".conf": "ini", ".txt": "text", ".csv": "csv"
}

def is_ignored_path(path_str: str) -> bool:
    """Kiểm tra đường dẫn có thuộc thư mục hoặc file rác cần bỏ qua không."""
    normalized = path_str.replace("\\", "/").lower()
    parts = normalized.split("/")
    for part in parts:
        if part in IGNORED_DIR_PATTERNS:
            return True
        if part.startswith(".") and part not in [".env.example", ".gitignore", ".oxlintrc.json"]:
            return True
    ext = "." + parts[-1].rsplit(".", 1)[-1] if "." in parts[-1] else ""
    if ext in IGNORED_FILE_EXTENSIONS:
        return True
    return False

def get_syntax_highlight_lang(filename: str) -> str:
    """Trả về ngôn ngữ code fence Markdown phù hợp với extension."""
    if not filename:
        return ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return SYNTAX_LANG_MAP.get(ext, "")

def build_directory_tree(file_paths: List[str], max_entries: int = 150) -> str:
    """Tạo sơ đồ cây thư mục (ASCII Tree) từ danh sách đường dẫn file."""
    if not file_paths:
        return ""
    
    tree: Dict[str, Any] = {}
    for p in sorted(file_paths):
        parts = [part for part in p.replace("\\", "/").strip("/").split("/") if part]
        curr = tree
        for part in parts[:-1]:
            curr = curr.setdefault(part, {})
        if parts:
            curr[parts[-1]] = None

    lines = []
    def _walk(d: Dict[str, Any], prefix: str = ""):
        keys = list(d.keys())
        for idx, k in enumerate(keys):
            if len(lines) >= max_entries:
                lines.append(f"{prefix}... (và thêm {len(file_paths) - max_entries} file khác)")
                return
            is_last = (idx == len(keys) - 1)
            connector = "└── " if is_last else "├── "
            val = d[k]
            if val is None:
                lines.append(f"{prefix}{connector}📄 {k}")
            else:
                lines.append(f"{prefix}{connector}📁 {k}/")
                new_prefix = prefix + ("    " if is_last else "│   ")
                _walk(val, new_prefix)

    _walk(tree)
    return "\n".join(lines)

MANIFEST_FILENAMES = {
    "readme.md", "readme.txt", "readme", "read_me.md",
    "package.json", "package-lock.json",
    "requirements.txt", "requirements-dev.txt", "pyproject.toml", "setup.py", "setup.cfg",
    "composer.json", "go.mod", "pom.xml", "build.gradle", "cargo.toml",
    "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "tsconfig.json", "vite.config.ts", "vite.config.js",
    "next.config.js", "next.config.mjs", "next.config.ts",
    ".env.example"
}

def is_manifest_file(filepath: str) -> bool:
    """Kiểm tra xem file có phải là file tổng quan / cấu hình trọng yếu của dự án không."""
    base = Path(filepath).name.lower()
    if base in MANIFEST_FILENAMES:
        return True
    if base.startswith("readme") or base.startswith("docker-compose"):
        return True
    return False

def format_file_size(num_bytes: int) -> str:
    """Định dạng dung lượng file dễ đọc."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    else:
        return f"{num_bytes / (1024 * 1024):.1f} MB"

def read_single_file_from_disk(file_path: str, max_size: int = 500000) -> Dict[str, Any]:
    """
    Đọc và trích xuất nội dung của một file bất kỳ trên đĩa (text, code, docx, xlsx, pptx, csv, rtf...).
    """
    p = Path(file_path).resolve()
    if not p.exists() or not p.is_file():
        return {"success": False, "error": f"File không tồn tại: {file_path}"}

    try:
        fsize = p.stat().st_size
    except Exception:
        fsize = 0

    fext = p.suffix.lower()
    lang = get_syntax_highlight_lang(p.name)

    try:
        raw_bytes = p.read_bytes()
        if fext in [".docx", ".doc"]:
            content = extract_text_from_docx(raw_bytes)
        elif fext in [".xlsx", ".xls"]:
            content = extract_text_from_xlsx(raw_bytes)
        elif fext in [".pptx", ".ppt"]:
            content = extract_text_from_pptx(raw_bytes)
        elif fext == ".csv":
            content = extract_text_from_csv(raw_bytes)
        elif fext == ".rtf":
            content = extract_text_from_rtf(raw_bytes)
        else:
            try:
                content = raw_bytes.decode("utf-8", errors="replace")
            except Exception:
                content = "[Không đọc được nội dung text file]"

        if len(content) > max_size:
            content = content[:max_size] + f"\n\n...[Đã cắt bớt vì file quá lớn ({max_size // 1000} KB)]..."

        return {
            "success": True,
            "file_path": str(p),
            "filename": p.name,
            "size": fsize,
            "lang": lang,
            "content": content
        }
    except Exception as e:
        logger.error(f"Lỗi đọc file {file_path}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def extract_zip_folder(
    data_bytes: bytes,
    zip_name: str = "archive.zip",
    max_files: int = 200,
    max_file_size: int = 50000
) -> str:
    """
    Giải nén thư mục ZIP theo Chế Độ On-Demand Tiết Kiệm Token (Mặc định):
    - Xây dựng sơ đồ cây thư mục trực quan (ASCII Tree)
    - Lập danh mục bảng các tệp tin trong dự án kèm dung lượng
    - Trích xuất nội dung các file cấu hình / tổng quan trọng yếu (README, package.json, requirements.txt...)
    - Hướng dẫn AI cách nạp file chi tiết khi cần ([FETCH_FILE: đường_dẫn])
    """
    import zipfile
    try:
        with zipfile.ZipFile(io.BytesIO(data_bytes)) as zf:
            valid_infos = []
            for info in zf.infolist():
                if info.is_dir():
                    continue
                if is_ignored_path(info.filename):
                    continue
                valid_infos.append(info)

            if not valid_infos:
                return f"📁 Thư mục nén '{zip_name}' không chứa file hợp lệ hoặc toàn bộ là file hệ thống/nhị phân."

            valid_paths = [info.filename for info in valid_infos[:max_files]]
            tree_str = build_directory_tree(valid_paths)
            total_bytes = sum(info.file_size for info in valid_infos)

            # Nếu là archive nhỏ (<= 3 file và tổng dung lượng < 30KB), trích xuất toàn bộ trực tiếp
            if len(valid_infos) <= 3 and total_bytes < 30000:
                parts = [
                    f"📁 **TÀI LIỆU NÉN: `{zip_name}`** ({len(valid_infos)} files - {format_file_size(total_bytes)})\n",
                    f"```text\n📂 {zip_name}\n{tree_str}\n```\n"
                ]
                for info in valid_infos:
                    fname = info.filename
                    fbytes = zf.read(info)
                    fext = "." + fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                    lang = get_syntax_highlight_lang(fname)
                    content = ""
                    if fext in [".docx", ".doc"]:
                        content = extract_text_from_docx(fbytes)
                    elif fext in [".xlsx", ".xls"]:
                        content = extract_text_from_xlsx(fbytes)
                    elif fext in [".pptx", ".ppt"]:
                        content = extract_text_from_pptx(fbytes)
                    elif fext == ".csv":
                        content = extract_text_from_csv(fbytes)
                    elif fext == ".rtf":
                        content = extract_text_from_rtf(fbytes)
                    else:
                        try:
                            content = fbytes.decode("utf-8", errors="replace")
                        except Exception:
                            content = "[Không đọc được nội dung]"
                    parts.append(
                        f"\n---\n#### 📄 File: `{fname}` ({format_file_size(len(fbytes))})\n"
                        f"```{lang}\n{content}\n```"
                    )
                return "\n".join(parts)

            # CHẾ ĐỘ ON-DEMAND MẶC ĐỊNH CHO THƯ MỤC / DỰ ÁN
            parts = [
                f"📁 **TỔNG QUAN THƯ MỤC DỰ ÁN: `{zip_name}`**",
                f"- Tổng số file: **{len(valid_infos)}** file (Tổng dung lượng: **{format_file_size(total_bytes)}**)",
                f"\n```text\n📂 {zip_name}\n{tree_str}\n```\n",
                f"📋 **DANH MỤC CÁC FILE TRONG DỰ ÁN:**",
                "| STT | File | Dung lượng |",
                "| :--- | :--- | :--- |"
            ]

            for idx, info in enumerate(valid_infos[:200], 1):
                fsize_str = format_file_size(info.file_size)
                parts.append(f"| {idx} | `{info.filename}` | {fsize_str} |")

            if len(valid_infos) > 200:
                parts.append(f"\n*... và {len(valid_infos) - 200} file khác (xem chi tiết trên sơ đồ cây).*\n")

            # Hướng dẫn AI On-Demand
            parts.append(
                "\n💡 **CHẾ ĐỘ TIẾT KIỆM TOKEN & NẠP THEO NHU CẦU (MẶC ĐỊNH):**\n"
                "- Danh sách trên thể hiện toàn bộ các tệp và cấu trúc thư mục của dự án.\n"
                "- Để tối ưu hóa token và tốc độ phản hồi, nội dung chi tiết của các tệp mã nguồn CHƯA được nạp sẵn.\n"
                "- Khi bạn cần phân tích, đọc code hoặc xem chi tiết bất kỳ tệp nào, hãy yêu cầu trong câu trả lời theo cú pháp: "
                "`[READ_FILE: đường_dẫn_file]` (Ví dụ: `[READ_FILE: src/index.ts]`). "
                "Backend sẽ tự động đọc đúng tệp đó và gửi lại nội dung cho bạn tiếp tục hoàn thành câu trả lời."
            )

            return "\n".join(parts)
    except Exception as e:
        logger.error(f"Lỗi giải nén thư mục ZIP: {e}")
        return f"[Lỗi giải nén thư mục ZIP: {e}]"

def scan_directory_on_disk(
    folder_path: str,
    max_files: int = 200,
    max_file_size: int = 50000
) -> Dict[str, Any]:
    """
    Quét thư mục trên ổ đĩa máy chủ / máy tính theo Chế Độ On-Demand Tiết Kiệm Token (Mặc định):
    - Xây dựng sơ đồ cây thư mục trực quan (ASCII Tree)
    - Lập danh mục bảng các tệp tin trong dự án kèm dung lượng
    - Trích xuất nội dung các file cấu hình / tổng quan trọng yếu (README, package.json, requirements.txt...)
    - Hướng dẫn AI cách nạp file chi tiết khi cần ([FETCH_FILE: đường_dẫn])
    """
    p = Path(folder_path).resolve()
    if not p.exists() or not p.is_dir():
        return {
            "success": False,
            "error": f"Đường dẫn thư mục không tồn tại hoặc không phải là thư mục: {folder_path}"
        }

    collected_files = []
    file_paths_rel = []

    for root, dirs, files in os.walk(str(p)):
        dirs[:] = [d for d in dirs if not is_ignored_path(d) and not d.startswith(".")]

        for f in files:
            full_path = Path(root) / f
            try:
                rel_path = str(full_path.relative_to(p)).replace("\\", "/")
            except Exception:
                rel_path = f

            if is_ignored_path(rel_path):
                continue

            file_paths_rel.append(rel_path)
            try:
                fsize = full_path.stat().st_size
            except Exception:
                fsize = 0
            collected_files.append((rel_path, full_path, fsize))

    tree_str = build_directory_tree(file_paths_rel)
    total_bytes = sum(fsize for _, _, fsize in collected_files)

    # CHẾ ĐỘ ON-DEMAND MẶC ĐỊNH CHO THƯ MỤC
    parts = [
        f"📁 **TỔNG QUAN THƯ MỤC TRÊN MÁY: `{p.name}`** (`{str(p)}`)",
        f"- Tổng số file: **{len(file_paths_rel)}** file (Tổng dung lượng: **{format_file_size(total_bytes)}**)",
        f"\n```text\n📂 {p.name}/\n{tree_str}\n```\n",
        f"📋 **DANH MỤC CÁC FILE TRONG DỰ ÁN:**",
        "| STT | File | Dung lượng |",
        "| :--- | :--- | :--- |"
    ]

    file_items = []
    for idx, (rel_path, full_path, fsize) in enumerate(collected_files, 1):
        file_items.append({"filename": rel_path, "size": fsize, "full_path": str(full_path)})
        if idx <= 200:
            fsize_str = format_file_size(fsize)
            parts.append(f"| {idx} | `{rel_path}` | {fsize_str} |")

    if len(file_paths_rel) > 200:
        parts.append(f"\n*... và {len(file_paths_rel) - 200} file khác (xem chi tiết trên sơ đồ cây).*\n")

    # Hướng dẫn AI On-Demand
    parts.append(
        "\n💡 **CHẾ ĐỘ TIẾT KIỆM TOKEN & NẠP THEO NHU CẦU (MẶC ĐỊNH):**\n"
        "- Danh sách trên thể hiện toàn bộ các tệp và cấu trúc thư mục của dự án.\n"
        "- Để tối ưu hóa token và tốc độ phản hồi, nội dung chi tiết của các tệp mã nguồn CHƯA được nạp sẵn.\n"
        "- Khi bạn cần phân tích, đọc code hoặc xem chi tiết bất kỳ tệp nào, hãy yêu cầu trong câu trả lời theo cú pháp: "
        "`[READ_FILE: đường_dẫn_file]` (Ví dụ: `[READ_FILE: src/index.ts]`). "
        "Backend sẽ tự động đọc đúng tệp đó và gửi lại nội dung cho bạn tiếp tục hoàn thành câu trả lời."
    )

    return {
        "success": True,
        "folder_name": p.name,
        "folder_path": str(p),
        "total_files": len(file_paths_rel),
        "tree": tree_str,
        "context_text": "\n".join(parts),
        "files": file_items
    }

def build_file_context(processed_files: List[Dict[str, Any]]) -> str:
    """
    Tạo context text từ các file đã trích xuất text để thêm vào prompt.
    Tự động áp dụng Chế Độ On-Demand Tiết Kiệm Token nếu có cấu trúc thư mục hoặc nhiều file.
    """
    valid_files = [f for f in processed_files if f.get("type") == "text_extract" and f.get("extracted_text")]
    if not valid_files:
        return ""

    # Nếu chỉ có 1 file và đã là tổng quan thư mục / nén thì xuất trực tiếp
    if len(valid_files) == 1:
        text = valid_files[0].get("extracted_text", "")
        fname = valid_files[0].get("filename", "file")
        if text.startswith("📁 **TỔNG QUAN"):
            return text
        lang = get_syntax_highlight_lang(fname)
        mime = valid_files[0].get("mime_type", "unknown")
        return f"📎 **Nội dung file: `{fname}`** (loại: {mime})\n```{lang}\n{text}\n```"

    file_names = [f.get("filename", f"file_{idx}") for idx, f in enumerate(valid_files)]
    has_folder_structure = any("/" in name or "\\" in name for name in file_names)

    # Nếu là thư mục hoặc nhiều file (> 4 files): áp dụng On-Demand
    if has_folder_structure and len(valid_files) > 4:
        tree_str = build_directory_tree(file_names)
        parts = [
            f"📁 **DANH SÁCH & CẤU TRÚC THƯ MỤC ĐÍNH KÈM ({len(valid_files)} files):**\n"
            f"```text\n{tree_str}\n```\n",
            "📋 **DANH MỤC CÁC FILE TRONG DỰ ÁN:**",
            "| STT | File | Trạng thái |",
            "| :--- | :--- | :--- |"
        ]
        for idx, f in enumerate(valid_files[:200], 1):
            fname = f.get("filename", "file")
            parts.append(f"| {idx} | `{fname}` | 📄 Sẵn sàng |")

        if len(valid_files) > 200:
            parts.append(f"\n*... và {len(valid_files) - 200} file khác (xem chi tiết trên sơ đồ cây).*\n")

        parts.append(
            "\n💡 **CHẾ ĐỘ TIẾT KIỆM TOKEN & NẠP THEO NHU CẦU (MẶC ĐỊNH):**\n"
            "- Toàn bộ danh sách tệp tin trong dự án đã được liệt kê ở trên.\n"
            "- Để tối ưu hóa token và tốc độ phản hồi, nội dung chi tiết của các tệp tin CHƯA được nạp sẵn.\n"
            "- Khi bạn cần đọc hoặc phân tích chi tiết tệp nào, hãy yêu cầu theo cú pháp: `[READ_FILE: đường_dẫn_file]`.\n"
            "- Backend sẽ tự động đọc đúng tệp đó và gửi lại nội dung cho bạn tiếp tục hoàn thành câu trả lời."
        )
        return "\n".join(parts)

    # Ngược lại (<= 4 files hoặc các file đơn lẻ): xuất đầy đủ
    tree_header = ""
    if has_folder_structure or len(valid_files) > 1:
        tree_str = build_directory_tree(file_names)
        tree_header = f"📁 **DANH SÁCH FILE ĐÍNH KÈM ({len(valid_files)} files):**\n```text\n{tree_str}\n```\n\n---\n\n"

    contexts = []
    for f in valid_files:
        text = f.get("extracted_text", "")
        fname = f.get("filename", "file")
        mime = f.get("mime_type", "unknown")
        lang = get_syntax_highlight_lang(fname)
        if text.startswith("📁 **TỔNG QUAN"):
            contexts.append(text)
        else:
            contexts.append(
                f"📎 **Nội dung file: `{fname}`** (loại: {mime})\n"
                f"```{lang}\n{text}\n```"
            )

    return tree_header + "\n\n---\n\n".join(contexts)


def get_file_type_label(mime_type: str) -> str:
    """Trả về nhãn loại file dễ đọc."""
    labels = {
        "image/": "🖼️ Ảnh",
        "application/pdf": "📄 PDF",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "📝 Word",
        "application/msword": "📝 Word",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "📊 Excel",
        "application/vnd.ms-excel": "📊 Excel",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "📽️ PowerPoint",
        "application/vnd.ms-powerpoint": "📽️ PowerPoint",
        "text/csv": "📊 CSV",
        "text/plain": "📄 Text",
        "text/markdown": "📝 Markdown",
        "text/html": "🌐 HTML",
        "application/json": "📋 JSON",
        "application/xml": "📋 XML",
        "audio/": "🎵 Audio",
        "video/": "🎬 Video",
        "application/rtf": "📝 RTF",
        "application/zip": "📦 ZIP",
    }

    for key, label in labels.items():
        if key.endswith("/"):
            if mime_type.startswith(key):
                return label
        elif mime_type == key:
            return label

    if mime_type.startswith("text/"):
        return "📄 Text"
    return "📎 File"
