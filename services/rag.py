from __future__ import annotations  # Tip ipuçlarında ileri referans için

import hashlib  # Stabil id üretmek için hash kullanacağız
from typing import Any, Dict, List, Tuple  # Tipleri açık yazmak için

import chromadb  # ChromaDB client kullanmak için
from services.embeddings import embed_query, embed_texts  # Gemini embedding üretmek için


def make_product_id(row: Dict[str, Any]) -> str:
    """
    Ürün için stabil bir product_id üretir.
    Aynı (Name + Brand + Label) gelirse aynı id üretilir.

    Args:
        row: Ürün verisi (kolon adı -> değer).

    Returns:
        Hash tabanlı product_id.
    """
    name = str(row.get("Name", "")).strip()  # Ürün adını alır
    brand = str(row.get("Brand", "")).strip()  # Marka adını alır
    label = str(row.get("Label", "")).strip()  # Kategori bilgisini alır

    raw_key = f"{name}|{brand}|{label}"  # Stabil anahtar üretir
    product_id = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()  # SHA-256 ile hash üretir
    return product_id  # product_id döndürür


def index_documents_to_chroma(
    documents: List[str],
    metadatas: List[Dict[str, Any]],
    ids: List[str],
    persist_dir: str = "db",
    collection_name: str = "cosmetics_kb",
) -> Tuple[bool, str]:
    """
    Dokümanları ChromaDB'ye yazar ve diske persist eder.

    Args:
        documents: Her ürün için 1 metin dokümanı listesi.
        metadatas: Her doküman için metadata listesi.
        ids: Her doküman için id listesi.
        persist_dir: Chroma verisinin yazılacağı klasör.
        collection_name: Kullanılacak collection adı.

    Returns:
        (is_ok, message) sonucu.
    """
    try:
        client = chromadb.PersistentClient(path=persist_dir)  # Chroma'yı disk üzerinde persist edecek client
        
        try:
            client.delete_collection(name=collection_name)  # Eski collection varsa siler (embedding boyutu çakışmasını çözer)
        except Exception:
            pass  # Collection yoksa veya silinemezse hata vermesin


        collection = client.get_or_create_collection(name=collection_name)  # Tek collection kullanır

        collection.add(
            documents=documents,  # Metin dokümanları
            metadatas=metadatas,  # Metadata alanları
            ids=ids,  # product_id listesi
        )  # Chroma'ya yazar

        return True, f"Indexleme tamamlandı. Toplam doküman: {len(documents)}"  # Başarı mesajı

    except Exception as exc:
        return False, f"Indexleme başarısız: {exc}"  # Hata mesajı

def search_documents_in_chroma(
    query_text: str,
    persist_dir: str = "db",
    collection_name: str = "cosmetics_kb",
    top_k: int = 5,
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    ChromaDB içinde doküman metninde query_text geçen kayıtları arar.
    Bu yöntem embedding gerektirmez, sadece metin eşleşmesi üzerinden çalışır.

    Args:
        query_text: Kullanıcının aramak istediği metin.
        persist_dir: Chroma persist klasörü.
        collection_name: Collection adı.
        top_k: En fazla döndürülecek sonuç sayısı.

    Returns:
        (is_ok, message, results):
            results: Her eleman {"id":..., "document":..., "metadata":...} içerir.
    """
    try:
        client = chromadb.PersistentClient(path=persist_dir)  # Persist edilen DB'ye bağlanır
        collection = client.get_or_create_collection(name=collection_name)  # Collection'ı alır

        # where_document metin içinde arama yapar (embedding olmadan çalışır)
        res = collection.get(
            where_document={"$contains": query_text},  # Doküman metninde query_text içeriyor mu
            include=["documents", "metadatas"],  # Doküman ve metadata'yı getirir
        )

        ids = res.get("ids", [])  # Bulunan id listesi
        docs = res.get("documents", [])  # Bulunan doküman listesi
        metas = res.get("metadatas", [])  # Bulunan metadata listesi

        # Rank'a göre sıralamak için önce tüm sonuçları tek listede toplayacağız
        combined = list(zip(ids, docs, metas))  # (id, document, metadata) üçlüsünü birleştirir
        combined_sorted = sorted(combined, key=lambda x: float(x[2].get("rank", 0) or 0), reverse=True)  # Rank'a göre sıralar

        results: List[Dict[str, Any]] = []  # Sonuçları burada toplayacağız

        for i in range(min(top_k, len(combined_sorted))):
            doc_id, doc_text, md = combined_sorted[i]  # Sıralı sonuçtan tek kaydı alır
            results.append(
                {
                    "id": doc_id,  # Doküman id
                    "document": doc_text,  # Doküman metni
                    "metadata": md,  # Metadata
                }
            )  # Sonucu listeye ekler


        return True, f"Bulunan sonuç: {len(results)}", results  # Başarıyla döndürür

    except Exception as exc:
        return False, f"Arama başarısız: {exc}", []  # Hata varsa boş liste döndürür

def index_documents_to_chroma_with_embeddings(
    documents: List[str],
    metadatas: List[Dict[str, Any]],
    ids: List[str],
    persist_dir: str = "db",
    collection_name: str = "cosmetics_kb",
) -> Tuple[bool, str]:
    """
    Dokümanları Gemini embeddings ile vektöre çevirip ChromaDB'ye yazar.

    Args:
        documents: Her ürün için 1 metin dokümanı listesi.
        metadatas: Her doküman için metadata listesi.
        ids: Her doküman için id listesi.
        persist_dir: Chroma verisinin yazılacağı klasör.
        collection_name: Collection adı.

    Returns:
        (is_ok, message)
    """
    try:
        vectors = embed_texts(documents)  # Tüm dokümanları embedding'e çevirir

        client = chromadb.PersistentClient(path=persist_dir)  # Persist client
        collection = client.get_or_create_collection(name=collection_name)  # Collection alır

        collection.delete(ids=ids)  # Aynı id varsa temizler

        collection.add(
            ids=ids,  # id listesi
            documents=documents,  # metin dokümanları
            metadatas=metadatas,  # metadata
            embeddings=vectors,  # embedding vektörleri
        )  # Embedding'li şekilde yazar

        return True, f"Embedding'li indexleme tamamlandı. Toplam doküman: {len(documents)}"

    except Exception as exc:
        return False, f"Embedding'li indexleme başarısız: {exc}"

def semantic_search_in_chroma(
    query_text: str,
    persist_dir: str = "db",
    collection_name: str = "cosmetics_kb",
    top_k: int = 5,
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Gemini embeddings ile semantic search yapar.

    Args:
        query_text: Kullanıcı sorgusu.
        persist_dir: Chroma persist klasörü.
        collection_name: Collection adı.
        top_k: Döndürülecek sonuç sayısı.

    Returns:
        (is_ok, message, results)
    """
    try:
        q_vec = embed_query(query_text)  # Sorguyu embedding'e çevirir

        client = chromadb.PersistentClient(path=persist_dir)  # Persist DB
        collection = client.get_or_create_collection(name=collection_name)  # Collection

        res = collection.query(
            query_embeddings=[q_vec],  # Sorgu embedding listesi
            n_results=top_k,  # Kaç sonuç istiyoruz
            include=["documents", "metadatas", "distances"],  # Doküman + metadata + distance
        )  # Semantic search yapar

        ids = res.get("ids", [[]])[0]  # Sonuç id listesi
        docs = res.get("documents", [[]])[0]  # Sonuç doküman listesi
        metas = res.get("metadatas", [[]])[0]  # Sonuç metadata listesi
        dists = res.get("distances", [[]])[0]  # Mesafe listesi

        results: List[Dict[str, Any]] = []  # Sonuçları toplayacağız

        for i in range(len(ids)):
            results.append(
                {
                    "id": ids[i],  # id
                    "document": docs[i],  # doküman
                    "metadata": metas[i],  # metadata
                    "distance": dists[i],  # benzerlik mesafesi
                }
            )  # Sonuç ekler

        return True, f"Semantic sonuç: {len(results)}", results

    except Exception as exc:
        return False, f"Semantic arama başarısız: {exc}", []
