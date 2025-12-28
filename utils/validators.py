REQUIRED_COLUMNS = (
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
) 

def validate_required_columns(actual_columns):
    """
    Yüklenen dosyada gerekli kolonlar var mı kontrol eder.

    Args:
        actual_columns: Dosyadan okunan kolon isimleri listesi.

    Returns:
        (is_valid):
            is_valid: Tüm zorunlu kolonlar varsa True.

    """
    actual_set = set(actual_columns)
    is_valid = all(col in actual_set for col in REQUIRED_COLUMNS)
    return is_valid

