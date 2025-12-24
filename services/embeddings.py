from __future__ import annotations  # Tip ipuçlarında ileri referans için

import os  # Ortam değişkeninden API key okumak için

from typing import List  # Liste tipini açık yazmak için

from langchain_google_genai import GoogleGenerativeAIEmbeddings  # Gemini embeddings modeli için


def get_embeddings_model() -> GoogleGenerativeAIEmbeddings:
    """
    Gemini embeddings modelini hazırlar.

    Returns:
        GoogleGenerativeAIEmbeddings nesnesi.
    """
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()  # API key'i ortam değişkeninden okur

    if not api_key:
        raise ValueError("GOOGLE_API_KEY bulunamadı. .env dosyasını doldurmalısın.")  # Key yoksa net hata verir

    model = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",  # Gemini embedding modeli adı
        google_api_key=api_key,  # API key'i modele verir
    )  # Embedding modelini oluşturur

    return model  # Modeli döndürür


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Birden fazla metni embedding vektörlerine çevirir.

    Args:
        texts: Embed edilecek metin listesi.

    Returns:
        Her metin için embedding vektörü listesi.
    """
    model = get_embeddings_model()  # Embedding modelini alır
    vectors = model.embed_documents(texts)  # Doküman embedding'lerini üretir
    return vectors  # Vektörleri döndürür


def embed_query(text: str) -> List[float]:
    """
    Tek bir sorguyu embedding vektörüne çevirir.

    Args:
        text: Kullanıcı sorgusu.

    Returns:
        Tek embedding vektörü.
    """
    model = get_embeddings_model()  # Embedding modelini alır
    vector = model.embed_query(text)  # Sorgu embedding'ini üretir
    return vector  # Vektörü döndürür
