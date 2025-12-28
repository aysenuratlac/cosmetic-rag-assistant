from __future__ import annotations  # Tip ipuçlarında ileri referans için

from typing import Any, Dict, Optional  # Satır verisini dict olarak taşımak için


def _llm_call(llm: Any, system: str, user: str, fallback: str) -> str:
    """
    Tek bir alan için LLM çağrısı yapar.
    Hata veya boş cevap olursa fallback döndürür.
    """
    try:
        response = llm.invoke(system + "\n\n" + user)  # MVP: system+user tek metinde
        text = getattr(response, "content", response)  # Bazı LLM'ler .content döndürür
        text = str(text).strip()  # Güvenli string dönüşümü
        return text if text else fallback  # Boşsa fallback
    except Exception:
        return fallback  # Herhangi bir hatada fallback


def build_product_document(row: Dict[str, Any], llm: Optional[Any] = None) -> str:
    """
    Tek bir ürün satırından (row) RAG uyumlu sentetik metin dokümanı üretir.

    - llm=None ise: statik şablon üretir (mevcut davranış).
    - llm verilirse: intro ve formula_comment alanlarını LLM ile doldurur (fallback'li).

    Args:
        row: Excel satırından gelen ürün verisi (kolon adı -> değer).
        llm: Opsiyonel LLM objesi (örn: ChatGoogleGenerativeAI)

    Returns:
        Ürünü açıklayan tek parça metin (page_content olarak kullanılacak).
    """
    name = str(row.get("Name", "")).strip()  # Ürün adını alır
    brand = str(row.get("Brand", "")).strip()  # Marka adını alır
    label = str(row.get("Label", "")).strip()  # Kategori/etiket bilgisini alır

    price = row.get("Price", "")  # Fiyat bilgisini alır
    rank = row.get("Rank", "")  # Puan bilgisini alır

    ingredients = str(row.get("Ingredients", "")).strip()  # İçerik listesini alır

    # Cilt tipi uygunlukları (dosyada 0/1 gibi değerler olabilir)
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
    }  # Cilt tipi kolonlarını sözlükte toplar

    suitable_skin_types_list = []  # Uygun cilt tiplerini toplayacağız
    for skin_type, value in skin_type_map.items():
        if str(value) == "1":  # Değeri 1 olanları uygun kabul eder
            suitable_skin_types_list.append(skin_type)  # Cilt tipi adını ekler

    if suitable_skin_types_list:
        suitable_skin_types = ", ".join(suitable_skin_types_list)  # Listeyi metne çevirir
    else:
        suitable_skin_types = "Belirlenemedi"  # Uygunluk yoksa net ifade

    # Varsayılan (LLM yoksa / hata olursa) fallback alanlar
    intro = "Ürün tanıtımı: belirlenemedi."  # LLM yoksa üretemeyiz
    formula_comment = "İçerik analizi: belirlenemedi."  # LLM yoksa üretemeyiz

    if llm is not None:
        # Ortak kurallar: uydurma yok, teşhis yok, risk dili yumuşak, kısa cevap
        common_system = (
            "Sen kozmetik ürün içeriklerini genel düzeyde yorumlayan bir asistansın.\n"
            "- Yeni ingredient uydurma.\n"
            "- Tıbbi teşhis veya kesin hüküm verme.\n"
            "- Risk dilini 'olabilir' / 'risk taşıyabilir' şeklinde kur.\n"
            "- Emin değilsen 'belirlenemedi' yaz.\n"
            "- Sadece istenen formatta cevap ver.\n"
        )

        base_info = (
            f"Ürün adı: {name}\n"
            f"Marka: {brand}\n"
            f"Kategori: {label}\n"
            f"Fiyat: {price}\n"
            f"Puan: {rank}\n"
            f"Uygun cilt tipleri: {suitable_skin_types}\n"
            f"Ingredients: {ingredients}\n"
        )  # LLM'e verilecek ürün bağlamı

        # 1) Intro: genel ürün tanıtımı (uzunluk limitli)
        intro = _llm_call(
            llm=llm,
            system=common_system,
            user=(
                base_info
                + "\nİstek:\n"
                "- Genel bir ürün tanıtımı yaz.\n"
                "- En fazla 2 cümle.\n"
                "- En fazla 280 karakter.\n"
                "- Çıktı formatı: 'Ürün tanıtımı: ...'\n"
            ),
            fallback=intro,
        )

        # 2) Formula comment: içerik yorumu + risk bilgilendirmesi (uzunluk limitli)
        formula_comment = _llm_call(
            llm=llm,
            system=common_system,
            user=(
                base_info
                + "\nİstek:\n"
                "- İçerik listesine göre genel bir formül yorumu yap.\n"
                "- Komedojenik risk yaratabilecek içerikler varsa isimlerini yaz ve 'olabilir' dili kullan.\n"
                "- Hassasiyet/iritasyon riski yaratabilecek içerikler varsa isimlerini yaz ve 'olabilir' dili kullan.\n"
                "- Eğer belirleyemiyorsan 'belirlenemedi' yaz.\n"
                "- En fazla 5 kısa cümle.\n"
                "- En fazla 450 karakter.\n"
                "- Çıktı formatı: 'İçerik analizi: ...'\n"
            ),
            fallback=formula_comment,
        )

    # Tek parça RAG dokümanı metni (bu metin embed edilecek)
    document_text = (
        f"Ürün adı: {name}\n"
        f"Marka: {brand}\n"
        f"Kategori: {label}\n"
        f"Fiyat: {price}\n"
        f"Puan: {rank}\n"
        f"Uygun cilt tipleri: {suitable_skin_types}\n\n"
        f"{intro}\n"
        f"{formula_comment}\n\n"
        f"Ingredients: {ingredients}\n"
    )

    return document_text  # Oluşturulan metni döndürür
