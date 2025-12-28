from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, List, Tuple

import chromadb
from langchain_community.vectorstores import Chroma
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
) -> Tuple[bool, str]:
    """
    Knowledge base'i SIFIRDAN indexler.

    Strateji:
    1) Mevcut collection varsa komple sil (dimension mismatch riskini sıfırlar)
    2) LangChain Chroma + GoogleGenerativeAIEmbeddings ile tekrar oluştur
    3) add_texts ile dokümanları ve embedding'leri yaz
    4) persist et
    """
    if not documents:
        return False, "Indexlenecek doküman yok."
    if not (len(documents) == len(metadatas) == len(ids)):
        return False, "documents/metadatas/ids uzunlukları eşit olmalı."

    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return False, "GOOGLE_API_KEY bulunamadı (.env)."

    try:
        # 1) Collection reset: delete_collection (en temiz yöntem)
        client = chromadb.PersistentClient(path=persist_dir)
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            pass  # collection yoksa sorun değil

        # 2) Embedding modeli (768 boyut)
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=api_key,
        )

        # 3) LangChain Chroma ile yeniden oluştur ve ekle
        vectorstore = Chroma(
            persist_directory=persist_dir,
            collection_name=collection_name,
            embedding_function=embeddings,
        )

        vectorstore.add_texts(
            texts=documents,
            metadatas=metadatas,
            ids=ids,
        )

        # 4) Diske yaz
        vectorstore.persist()

        return True, f"Indexleme tamamlandı. Toplam doküman: {len(documents)}"

    except Exception as exc:
        return False, f"Indexleme hatası: {exc}"
