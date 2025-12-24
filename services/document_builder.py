from __future__ import annotations  # Tip ipuçlarında ileri referans için

from typing import Any, Dict  # Satır verisini dict olarak taşımak için


def build_product_document(row: Dict[str, Any]) -> str:
    """
    Tek bir ürün satırından (row) RAG uyumlu sentetik metin dokümanı üretir.
    Bu fonksiyon LLM kullanmaz; sadece şablona göre bir metin oluşturur.

    Args:
        row: Excel satırından gelen ürün verisi (kolon adı -> değer).

    Returns:
        Ürünü açıklayan tek parça metin (page_content olarak kullanılacak).
    """
    name = str(row.get("Name", "")).strip()  # Ürün adını güvenli şekilde alır
    brand = str(row.get("Brand", "")).strip()  # Marka adını güvenli şekilde alır
    label = str(row.get("Label", "")).strip()  # Kategori/etiket bilgisini alır

    price = row.get("Price", "")  # Fiyat bilgisini alır (sayısal olabilir)
    rank = row.get("Rank", "")  # Puan bilgisini alır (sayısal olabilir)

    ingredients = str(row.get("Ingredients", "")).strip()  # İçerik listesini alır

    # Cilt tipi uygunlukları (dosyada 0/1 veya True/False gibi değerler olabilir)
    combination = row.get("Combination", "")  # Kombinasyon cilt uygunluğu
    dry = row.get("Dry", "")  # Kuru cilt uygunluğu
    normal = row.get("Normal", "")  # Normal cilt uygunluğu
    oily = row.get("Oily", "")  # Yağlı cilt uygunluğu
    sensitive = row.get("Sensitive", "")  # Hassas cilt uygunluğu

    skin_type_map = {
        "Combination": combination,
        "Dry": dry,
        "Normal": normal,
        "Oily": oily,
        "Sensitive": sensitive,
    }  # Cilt tipi kolonlarını tek bir sözlükte toplar

    suitable_skin_types_list = []  # Uygun cilt tiplerini burada toplayacağız

    for skin_type, value in skin_type_map.items():
        if str(value) == "1":  # Değeri 1 olan cilt tiplerini uygun kabul eder
            suitable_skin_types_list.append(skin_type)  # Sadece adını ekler

    if suitable_skin_types_list:
        suitable_skin_types = ", ".join(suitable_skin_types_list)  # Listeyi okunabilir metne çevirir
    else:
        suitable_skin_types = "Belirlenemedi"  # Hiçbiri uygun değilse net ifade


    # Bu alanlar blueprint'te var ama LLM olmadan şu an “belirlenemedi” dememiz gerekiyor
    intro = "Ürün tanıtımı: belirlenemedi."  # LLM olmadan ürün tanıtımı üretemeyiz
    formula_comment = "İçerik analizi: belirlenemedi."  # Ingredient yorumunu LLM olmadan yapmıyoruz
    comedogenic_risk = "Komedojenik risk: belirlenemedi."  # Kesin yargı yok, belirlenemedi
    sensitivity_risk = "Hassasiyet/iritasyon riski: belirlenemedi."  # Kesin yargı yok, belirlenemedi

    document_text = (
        f"Ürün adı: {name}\n"
        f"Marka: {brand}\n"
        f"Kategori: {label}\n"
        f"Fiyat: {price}\n"
        f"Puan: {rank}\n"
        f"Uygun cilt tipleri: {suitable_skin_types}\n\n"
        f"{intro}\n"
        f"{formula_comment}\n"
        f"{comedogenic_risk}\n"
        f"{sensitivity_risk}\n\n"
        f"Ingredients: {ingredients}\n"
    )  # Tek parça RAG dokümanı metni

    return document_text  # Oluşturulan metni döndürür
