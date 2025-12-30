from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, List, Tuple

import chromadb
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings  # OpenAI embedding modeli için 
from langchain_google_genai import GoogleGenerativeAIEmbeddings


def make_product_id(row: Dict[str, Any]) -> str:
    """
    Ürün satırından stabil bir product_id üretir.
    Aynı ürün tekrar yüklense bile aynı id üretilsin diye sha256 kullanılır.
    """
    brand = str(row.get("Brand", "")).strip().lower()
    name = str(row.get("Name", "")).strip().lower()
    label = str(row.get("Label", "")).strip().lower()

    base = f"{brand}::{name}::{label}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def index_documents_to_chroma_with_embeddings(
    documents: List[str],
    metadatas: List[Dict[str, Any]],
    ids: List[str],
    persist_dir: str = "db",
    collection_name: str = "cosmetics_kb",
    provider: str = "gemini",  # Hangi sağlayıcıyla embed edeceğimizi seçmek için
) -> Tuple[bool, str]:
    # Provider’a göre API key seç
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()  # OpenAI key (.env)
        if not api_key:
            return False, "OPENAI_API_KEY bulunamadı (.env)."  # Key yoksa hata
    else:
        api_key = os.getenv("GOOGLE_API_KEY", "").strip()  # Gemini key (.env)
        if not api_key:
            return False, "GOOGLE_API_KEY bulunamadı (.env)."  # Key yoksa hata

    try:
        # 1) Collection reset: delete_collection (dimension mismatch riskini azaltır)
        client = chromadb.PersistentClient(path=persist_dir)
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            pass  # collection yoksa sorun değil

        # 2) Embedding modeli seçimi
        if provider == "openai":
            embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",  # Ucuz/hızlı embedding modeli
                openai_api_key=api_key,          # OpenAI API key
            )
        else:
            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",  # Gemini embedding modeli (mevcut)
                google_api_key=api_key,             # Gemini API key
            )

        # 3) LangChain Chroma ile ekle
        vectorstore = Chroma(
            persist_directory=persist_dir,       # DB klasörü
            collection_name=collection_name,     # Collection adı
            embedding_function=embeddings,       # Seçilen embedding fonksiyonu
        )

        vectorstore.add_texts(
            texts=documents,       # Doküman metinleri
            metadatas=metadatas,   # Metadata
            ids=ids,               # Stabil product_id
        )

        vectorstore.persist()  # Diske yaz
        return True, f"Indexleme tamamlandı. Toplam doküman: {len(documents)}"

    except Exception as exc:
        return False, f"Indexleme hatası: {exc}"
