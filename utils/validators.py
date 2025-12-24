from __future__ import annotations  # Python tip ipuçlarında ileri referans desteği için

from typing import List, Tuple  # Fonksiyon dönüş tiplerini açık yazmak için


REQUIRED_COLUMNS: List[str] = [
    "Label",  # Ürün kategorisi/etiketi
    "Brand",  # Marka adı
    "Name",  # Ürün adı
    "Price",  # Fiyat bilgisi
    "Rank",  # Puan / sıralama
    "Ingredients",  # İçerik listesi
    "Combination",  # Kombinasyon cilt uygunluğu (beklenen kolon)
    "Dry",  # Kuru cilt uygunluğu
    "Normal",  # Normal cilt uygunluğu
    "Oily",  # Yağlı cilt uygunluğu
    "Sensitive",  # Hassas cilt uygunluğu
]  # Blueprint'te beklenen kolon isimleri


def validate_required_columns(actual_columns: List[str]) -> Tuple[bool, List[str]]:
    """
    Yüklenen dosyada gerekli kolonlar var mı kontrol eder.

    Args:
        actual_columns: Dosyadan okunan kolon isimleri listesi.

    Returns:
        (is_valid, missing_columns):
            is_valid: Tüm zorunlu kolonlar varsa True.
            missing_columns: Eksik kolonların listesi.
    """
    missing_columns: List[str] = []  # Eksik kolonları toplamak için

    for col in REQUIRED_COLUMNS:
        if col not in actual_columns:
            missing_columns.append(col)  # Dosyada olmayan zorunlu kolonu listeye ekler

    is_valid: bool = len(missing_columns) == 0  # Eksik yoksa dosya geçerli sayılır
    return is_valid, missing_columns  # Sonucu ve eksikleri döndürür
