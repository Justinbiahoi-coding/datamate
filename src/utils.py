import os
import json
import pandas as pd

def get_business_dir(base_dir: str, business_id: str) -> str:
    """Trả về thư mục của doanh nghiệp (ví dụ: /data/data/dev_001)."""
    return os.path.join(base_dir, "data", business_id)

def get_root_rulebook(base_dir: str) -> str:
    """Đọc file rulebook.md ở thư mục gốc."""
    file_path = os.path.join(base_dir, "rulebook.md")
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def list_business_files(base_dir: str, business_id: str) -> list:
    """Liệt kê toàn bộ tên các file có trong thư mục của doanh nghiệp."""
    biz_dir = get_business_dir(base_dir, business_id)
    if os.path.exists(biz_dir):
        return os.listdir(biz_dir)
    return []

def load_business_excel(base_dir: str, business_id: str, file_name: str, sheet_name=0) -> pd.DataFrame:
    """Đọc file Excel (.xlsx) bên trong thư mục doanh nghiệp."""
    biz_dir = get_business_dir(base_dir, business_id)
    file_path = os.path.join(biz_dir, file_name)
    if os.path.exists(file_path):
        return pd.read_excel(file_path, sheet_name=sheet_name)
    return pd.DataFrame()

def load_business_csv(base_dir: str, business_id: str, file_name: str) -> pd.DataFrame:
    """Đọc file CSV bên trong thư mục doanh nghiệp."""
    biz_dir = get_business_dir(base_dir, business_id)
    file_path = os.path.join(biz_dir, file_name)
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return pd.DataFrame()