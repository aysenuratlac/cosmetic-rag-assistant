from __future__ import annotations  # Tip ipuçlarında ileri referans için

from typing import Tuple  # Fonksiyon dönüş tipini açık yazmak için

import pandas as pd  # XLSX dosyasını okumak için pandas


def load_table_file(file_path: str) -> Tuple[bool, str, pd.DataFrame | None]:
    """
    Sadece XLSX dosyasını pandas DataFrame olarak okur.

    Args:
        file_path: Diskteki dosya yolu.

    Returns:
        (is_ok, message, df):
            is_ok: Okuma başarılıysa True.
            message: Kullanıcıya gösterilecek durum mesajı.
            df: Başarılıysa DataFrame, değilse None.
    """
    try:
        if not file_path.lower().endswith(".xlsx"):
            return False, "Bu MVP sürümünde sadece XLSX dosyaları desteklenmektedir.", None  # Bilinçli kısıt

        df = pd.read_excel(file_path)  # XLSX dosyasını okur
        return True, "XLSX dosyası okundu.", df  # Başarılı okuma sonucu

    except Exception as exc:
        return False, f"Dosya okunamadı: {exc}", None  # Okuma sırasında hata yakalanır
