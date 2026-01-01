# scripts/run_ragas_eval.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import os  # Path ve env için
import json  # JSONL okumak için
from dotenv import load_dotenv  # .env için
import pandas as pd  # Sonuçları tabloya dökmek için

from datasets import Dataset  # RAGAS Dataset formatı için

from ragas import evaluate  # RAGAS evaluate fonksiyonu
from ragas.metrics import faithfulness, answer_relevancy, context_recall  # İstenen metrikler

from services.langchain_rag import build_rag_chain  # Mevcut RAG chain'i kurmak için


def load_jsonl(path: str) -> list[dict]:
    """
    JSONL dosyasını (satır satır JSON) okur.
    """
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))  # Satırı dict'e çevir
    return rows


def main():
    load_dotenv()  # .env yükle

    provider = os.getenv("RAG_PROVIDER", "openai").strip().lower()  # openai / gemini
    persist_dir = f"db_{provider}"  # db_openai / db_gemini
    collection_name = f"cosmetics_kb_{provider}"  # cosmetics_kb_openai / cosmetics_kb_gemini

    test_path = os.path.join("test_data", f"ragas_testset_{provider}.jsonl")  # Test seti
    if not os.path.exists(test_path):
        raise FileNotFoundError(f"Test seti bulunamadı: {test_path}. Önce build_ragas_testset.py çalıştırmalısın.")

    # 1) Chain'i kur (projedeki gibi)
    chain = build_rag_chain(
        persist_dir=persist_dir,  # DB dizini
        collection_name=collection_name,  # Collection adı
        k=5,  # Top-k retrieval
        provider=provider,  # Provider
    )

    # 2) Test setini oku
    rows = load_jsonl(test_path)

    # 3) Her soru için: RAG chain'i çalıştır, cevap ve retrieved context topla
    questions = []
    answers = []
    contexts = []  # RAGAS burada list[list[str]] bekler (her soru için retrieved doküman metinleri)
    retrieved_context_ids = []  # ID-based recall için retrieved doc id listesi
    reference_context_ids = []  # Test setinden gelen doğru id listesi
    ground_truths = []  # Referans cevap

    for r in rows:
        q = r["question"]  # Soru
        gt = r.get("ground_truth", "")  # Referans cevap
        ref_ids = r.get("reference_context_ids", [])  # Referans doc id

        # Chain'i çağır
        res = chain.invoke({"input": q})  # LangChain retrieval chain çağrısı

        ans = str(res.get("answer", "")).strip()  # Model cevabı
        ctx_docs = res.get("context", [])  # Retrieved Document listesi (LangChain)

        # Context metinlerini çıkar
        ctx_texts = []
        ctx_ids = []

        for d in ctx_docs:
            # d.page_content: retrieved doküman metni
            ctx_texts.append(str(getattr(d, "page_content", "")).strip())

            # metadata içinden product_id yakala (indexlerken koyuyorsun)
            meta = getattr(d, "metadata", {}) or {}
            ctx_ids.append(str(meta.get("product_id", "")).strip())

        questions.append(q)  # Soru ekle
        answers.append(ans)  # Cevap ekle
        contexts.append(ctx_texts)  # Context ekle
        retrieved_context_ids.append(ctx_ids)  # Retrieved id listesi
        reference_context_ids.append(ref_ids)  # Referans id listesi
        ground_truths.append(gt)  # Ground truth

    # 4) RAGAS dataset'i oluştur
    ds = Dataset.from_dict(
        {
            "question": questions,  # Soru
            "answer": answers,  # Üretilen cevap
            "contexts": contexts,  # Retrieved context metinleri
            "ground_truth": ground_truths,  # Referans cevap
            "retrieved_context_ids": retrieved_context_ids,  # Recall için
            "reference_context_ids": reference_context_ids,  # Recall için
        }
    )

    # 5) RAGAS evaluation çalıştır
    # Not: context_recall + faithfulness + answer_relevancy istenen metrikler
    result = evaluate(
        ds,
        metrics=[
            context_recall,  # Retrieval Recall (RAGAS context_recall)
            faithfulness,  # Faithfulness
            answer_relevancy, 
        ],
    )

    # 6) Rapor dosyalarını üret
    os.makedirs("reports", exist_ok=True)  # reports klasörü yoksa oluştur
    df = result.to_pandas()  # Sonuçları pandas DataFrame'e çevir

    csv_path = os.path.join("reports", f"ragas_report_{provider}.csv")  # CSV yolu
    md_path = os.path.join("reports", f"ragas_report_{provider}.md")  # Markdown yolu

    df.to_csv(csv_path, index=False)  # CSV kaydet

    # Markdown özet yaz
    mean_context_recall = float(df["context_recall"].mean())
    mean_faithfulness = float(df["faithfulness"].mean())

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# RAGAS Doğruluk Raporu\n\n")
        f.write(f"- Provider: {provider}\n")
        f.write(f"- Ortalama context_recall (Retrieval Recall): {mean_context_recall:.3f}\n")
        f.write(f"- Ortalama faithfulness: {mean_faithfulness:.3f}\n\n")
        f.write("## Satır Bazlı Sonuçlar\n\n")
        f.write(df.to_markdown(index=False))  # Tabloyu markdown bas

    print(f"Rapor üretildi:\n- {csv_path}\n- {md_path}")


if __name__ == "__main__":
    main()
