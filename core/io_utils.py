"""文件与临时目录管理。

隐私承诺（系统提示词 4.3.4）：
  - 用户上传数据仅存于临时目录，处理后 10 分钟内自动清理；
  - 不持久化任何用户数据。
"""

from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path

import pandas as pd

_TEMP_ROOT = Path(tempfile.gettempdir()) / "studyhack_uploads"
_TTL_SECONDS = 600  # 10 分钟


def _ensure_root() -> Path:
    _TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    return _TEMP_ROOT


def cleanup_expired(now: float | None = None) -> int:
    """清理超过 TTL 的临时目录，返回清理数量。"""
    now = now or time.time()
    root = _ensure_root()
    removed = 0
    for d in root.iterdir():
        try:
            if d.is_dir() and (now - d.stat().st_mtime) > _TTL_SECONDS:
                shutil.rmtree(d, ignore_errors=True)
                removed += 1
        except OSError:
            continue
    return removed


def save_upload(uploaded_file) -> tuple[str, str]:
    """保存上传文件到临时目录，返回 (file_id, 文件路径)。"""
    import uuid

    cleanup_expired()
    fid = uuid.uuid4().hex[:12]
    workdir = _ensure_root() / fid
    workdir.mkdir(parents=True, exist_ok=True)
    suffix = Path(uploaded_file.name).suffix or ".xlsx"
    path = workdir / f"upload{suffix}"
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return fid, str(path)


def read_upload(path: str) -> pd.DataFrame:
    """读取上传的 Excel/CSV 为 DataFrame，支持 xlsx/xls/csv。"""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(p)
    if suffix == ".csv":
        try:
            return pd.read_csv(p, encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(p, encoding="gbk")
    raise ValueError(f"不支持的文件格式：{suffix}（仅支持 .xlsx / .xls / .csv）")


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    """DataFrame 导出为 Excel 字节流（供下载）。"""
    import io

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return buf.getvalue()


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """DataFrame 导出为 CSV 字节流（utf-8-sig 兼容 Excel 中文）。"""
    return df.to_csv(index=False).encode("utf-8-sig")
