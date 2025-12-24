from __future__ import annotations  # Tip ipuçlarında ileri referans için

import os  # API key okumak için
from typing import List  # Liste tipini açık yazmak için

from langchain_google_genai import ChatGoogleGenerativeAI  # Gemini chat modeli için


def get_chat_model() -> ChatGoogleGenerativeAI:
    """
    Gemini chat modelini hazırlar.

    Returns:
        ChatGoogleGenerativeAI nesnesi.
    """
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()  # API key'i ortam değişkeninden okur

    if not api_key:
        raise ValueError("GOOGLE_API_KEY bulunamadı. .env dosyasını doldurmalısın.")  # Key yoksa net hata

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",  # Hızlı ve uygun maliyetli model
        google_api_key=api_key,  # API key
        temperature=0.2,  # Daha tutarlı cevap için düşük sıcaklık
    )  # Chat modelini oluşturur

    return llm  # Modeli döndürür


def generate_answer(user_question: str, context_docs: List[str]) -> str:
    """
    Kullanıcı sorusuna, sadece verilen doküman bağlamına dayanarak cevap üretir.

    Args:
        user_question: Kullanıcının sorusu.
        context_docs: Retrieval ile gelen doküman metinleri.

    Returns:
        Modelin ürettiği cevap metni.
    """
    llm = get_chat_model()  # Chat modelini alır

    context_text = "\n\n---\n\n".join(context_docs)  # Dokümanları tek bağlam metnine birleştirir



    prompt = (
    "Sen bir kozmetik ürün asistanısın ve aynı zamanda günlük sohbet de edebilirsin.\n"
    "Sadece aşağıdaki BAĞLAM dokümanlarını, kullanıcı ürün/kozmetik hakkında bir şey sorduğunda kullan.\n"
    "Kullanıcı ürün istemiyorsa (selamlaşma, small talk vb.) BAĞLAM'a dayanarak ürün listesi çıkarma.\n"
    "BAĞLAMDA olmayan hiçbir bilgiyi uydurma.\n"
    "Tıbbi teşhis koyma, kesin yargı verme.\n"
    "Emin olmadığın yerde 'belirlenemedi' yaz.\n"
    "Risk/uyarı cümlelerinde 'olabilir' / 'risk taşıyabilir' dili kullan.\n\n"
    "ÖNCE ŞU KARARI VER:\n"
    "1) Kullanıcı mesajı sadece sohbet mi? (selam, nasılsın, teşekkür, espri vb.)\n"
    "2) Yoksa ürün/kozmetik sorusu mu? (öneri, cilt tipi, içerik, ürün adı, ingredient, risk vb.)\n\n"
    "EĞER (1) SOHBET İSE:\n"
    "- Kısa, samimi cevap ver.\n"
    "- Ürün listesi çıkarma.\n"
    "- Gerekirse bir cümleyle yardımcı olabileceğin konuları söyle: 'İstersen cilt tipini söyle, ürün de önerebilirim.'\n\n"
    "EĞER (2) ÜRÜN/Kozmetik SORUSU İSE:\n"
    "- Cevabın ilk satırında şunu yaz: 'Not: Bu öneriler yüklenen ürün KB (knowledge base) içeriğine dayanır.'\n"
    "- En fazla 5 ürün öner.\n"
    "- İlk yanıtta DETAY DÖKME.\n"
    "- Her ürün için kısa tanıtım yap:\n"
    "  * Ürün: <Name> (Brand)\n"
    "  * Kategori: <Label> | Puan: <Rank> | Fiyat: <Price>\n"
    "  * Kısa açıklama: 1 cümle (genel; bağlamda olmayan iddia yok)\n"
    "- Kullanıcı açıkça 'detay', 'içerik', 'neden', 'hassasiyet', 'komedojen', 'risk', 'akne' vb. istemediyse:\n"
    "  * Ingredients veya uzun analiz yazma.\n"
    "- Kullanıcı detay isterse:\n"
    "  * Ingredients'ı (varsa) yaz.\n"
    "  * Hassasiyet/iritasyon/komedojen gibi konularda BAĞLAM yoksa 'belirlenemedi' de.\n\n"
    f"KULLANICI MESAJI:\n{user_question}\n\n"
    f"BAĞLAM (Ürün dokümanları):\n{context_text}\n\n"
    "CEVAP:"
    )



    response = llm.invoke(prompt)  # Gemini'ye prompt'u gönderir
    return str(response.content)  # Model cevabını metin olarak döndürür
