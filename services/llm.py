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
        "Sen bir kozmetik ürün asistanısın.\n"
        "Sadece aşağıdaki BAĞLAM dokümanlarını kullan.\n"
        "BAĞLAMDA olmayan hiçbir bilgiyi uydurma.\n"
        "Tıbbi teşhis veya kesin yargı verme.\n"
        "Emin olmadığın şeylerde 'belirlenemedi' de.\n"
        "Risk/uyarı cümlelerinde 'olabilir' / 'risk taşıyabilir' dili kullan.\n\n"
        "ÇIKTI FORMATI KURALLARI:\n"
        "- En fazla 5 ürün öner.\n"
        "- Her ürün için sadece şu alanları yaz:\n"
        "  * Ürün: <Name> (Brand)\n"
        "  * Puan: <Rank> | Fiyat: <Price>\n"
        "  * Neden öneri: 1 kısa cümle (bağlama dayanarak, genel)\n"
        "  * Ingredients (ilk 10): <ilk 10 madde>\n"
        "- Ürün başına 'belirlenemedi' satırları yazma.\n"
        "- Eğer bazı analizler yapılamıyorsa en sonda tek satır yaz:\n"
        "  'Not: Ürün tanıtımı/içerik analizi/iritasyon gibi detaylar bu MVP'de belirlenemedi.'\n\n"
        f"KULLANICI SORUSU:\n{user_question}\n\n"
        f"BAĞLAM:\n{context_text}\n\n"
        "CEVAP:"
    )


    response = llm.invoke(prompt)  # Gemini'ye prompt'u gönderir
    return str(response.content)  # Model cevabını metin olarak döndürür
