import os  # Ortam değişkenleri ve path işlemleri için
import json  # JSONL yazmak için
import random  # Rastgele örnekleme için
from dotenv import load_dotenv  # .env okumak için

from langchain_community.vectorstores import Chroma  # Chroma'yı açmak için
from langchain_openai import OpenAIEmbeddings  # OpenAI embedding (provider=openai)
from langchain_google_genai import GoogleGenerativeAIEmbeddings  # Gemini embedding (provider=gemini)


def pick_embeddings(provider: str):
    """
    Provider'a göre doğru embedding fonksiyonunu seçer.
    """
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()  # OpenAI key
        if not api_key:
            raise ValueError("OPENAI_API_KEY bulunamadı (.env).")
        return OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=api_key)  # Aynı embedding
    else:
        api_key = os.getenv("GOOGLE_API_KEY", "").strip()  # Google key
        if not api_key:
            raise ValueError("GOOGLE_API_KEY bulunamadı (.env).") 
        return GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)  # Aynı embedding


def extract_field(doc_text: str, prefix: str) -> str:
    """
    Doküman metninde 'Ürün adı: ...' gibi satırları basitçe parse eder.
    Bulamazsa 'Belirlenemedi' döner.
    """
    for line in doc_text.splitlines():  # Satır satır dolaş
        line = line.strip()
        if line.startswith(prefix):  # Prefix eşleşirse
            return line.replace(prefix, "", 1).strip() or "Belirlenemedi"  # Değeri döndür
    return "Belirlenemedi"  # Bulamazsa


def main():
    load_dotenv()  # .env yükle

    provider = os.getenv("RAG_PROVIDER", "openai").strip().lower()  # Default openai
    persist_dir = f"db_{provider}"  # db_openai / db_gemini
    collection_name = f"cosmetics_kb_{provider}"  # cosmetics_kb_openai / cosmetics_kb_gemini

    embeddings = pick_embeddings(provider)  # Provider'a uygun embedding seç

    vectorstore = Chroma(
        persist_directory=persist_dir,  # Persist DB dizini
        collection_name=collection_name,  # Collection adı
        embedding_function=embeddings,  # Embedding fonksiyonu
    )

    # Chroma içinden örnek doküman çekmek için düşük seviye collection'a ulaşıyoruz
    col = vectorstore._collection  # pratik erişim (LangChain wrapper)
    raw = col.get(include=["documents", "metadatas"])  # Tüm dokümanları ve metadata'yı çek

    documents = raw.get("documents", [])  # Doküman metinleri
    metadatas = raw.get("metadatas", [])  # Metadata listesi

    if not documents:
        raise ValueError("Chroma içinde doküman yok. Önce Admin'den indexleme yapmalısın.")

    # Rastgele n tane doküman seçip her biri için 3 soru üret
    n = 20  # 20 soru 
    idxs = list(range(len(documents)))
    random.shuffle(idxs)  # Karıştır
    idxs = idxs[: min(n, len(idxs))]  # İlk n tanesini al

    os.makedirs("test_data", exist_ok=True)  # test_data klasörü yoksa oluştur
    out_path = os.path.join("test_data", f"ragas_testset_{provider}.jsonl")  # Çıktı dosyası

    with open(out_path, "w", encoding="utf-8") as f:
        for i in idxs:
            doc_text = documents[i]  # Ürün dokümanı
            meta = metadatas[i] or {}  # Metadata
            product_id = str(meta.get("product_id", "")).strip()  # product_id

            # Dokümandan "ground truth" alanları çıkar
            name = extract_field(doc_text, "Ürün adı:")  # Ürün adı alanı
            brand = extract_field(doc_text, "Marka:")  # Marka alanı
            skin = extract_field(doc_text, "Uygun cilt tipleri:")  # Cilt tipi alanı
            rank = extract_field(doc_text, "Puan:")  # Puan alanı
            fiyat = extract_field(doc_text, "Fiyat:")  # Fiyat alanı


            # 3 tür soru üretiyoruz (hepsi dokümandan cevaplanabilir)
            qa = [
                {
                    "question": f"{brand} markasının {name} ürününün puanı kaç?",
                    "ground_truth": f"Puan: {rank}.",
                },
                {
                    "question": f"{name} ürünü hangi cilt tipleri için uygundur?",
                    "ground_truth": f"Uygun cilt tipleri: {skin}.",
                },
                {
                    "question": f"{name} ürünün,n fiyatı nedir?",
                    "ground_truth": f"Fiyat: {fiyat}.",
                },
            ]

            for item in qa:
                row = {
                    "question": item["question"],  # Soru
                    "ground_truth": item["ground_truth"],  # Beklenen cevap (referans)
                    "reference_context_ids": [product_id],  # Doğru dokümanın ID'si (retrieval recall için)
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")  # JSONL satırı yaz

    print(f"Test seti yazıldı: {out_path}")


if __name__ == "__main__":
    main()
