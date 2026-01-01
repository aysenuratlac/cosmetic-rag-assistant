# scripts/make_model_comparison.py
# Amaç: Gemini ve OpenAI için üretilmiş RAGAS CSV raporlarını okuyup,
#       rapora eklenebilir bir "özet karşılaştırma tablosu" üretmek.

from __future__ import annotations  # Tip ipuçları için (Python 3.9+ uyumlu)
import os  # Dosya yolu işlemleri için
import pandas as pd  # CSV okuma ve tablo üretimi için


# 1) Kullanıcı ayarları (bu iki yolu kendi makinen/proje yapına göre güncelle)
GEMINI_REPORT_PATH = r"reports\ragas_report_gemini.csv"  # Gemini RAGAS çıktısı
OPENAI_REPORT_PATH = r"reports\ragas_report_openai.csv"  # OpenAI RAGAS çıktısı

# 2) Çıktı dosyaları
OUT_DIR = r"reports"  # Üretilen tabloların kaydedileceği klasör
SUMMARY_OUT_PATH = os.path.join(OUT_DIR, "model_comparison_summary.csv")  # Özet tablo
PER_QUESTION_OUT_PATH = os.path.join(OUT_DIR, "model_comparison_per_question.csv")  # Soru bazlı tablo


def _load_report(csv_path: str) -> pd.DataFrame:
    """RAGAS rapor CSV'sini okur ve beklenen kolonları seçer."""
    df = pd.read_csv(csv_path)  # CSV oku

    # Notebook'ta kullandığın kolon seti ile aynı olacak şekilde seçiyoruz. :contentReference[oaicite:2]{index=2}
    needed_cols = [
        "question",
        "answer",
        "ground_truth",
        "context_recall",
        "faithfulness",
        "answer_relevancy",
    ]

    missing = [c for c in needed_cols if c not in df.columns]  # Eksik kolon kontrolü
    if missing:
        raise ValueError(
            f"CSV içinde beklenen kolon(lar) yok: {missing}\n"
            f"Dosya: {csv_path}\n"
            f"Mevcut kolonlar: {list(df.columns)}"
        )

    return df[needed_cols].copy()  # Sadece gereken kolonları döndür


def _summarize(df: pd.DataFrame, model_name: str) -> dict:
    """Tek bir model raporundan özet metrikleri hesaplar."""
    metrics = ["context_recall", "faithfulness", "answer_relevancy"]  # Ölçülecek metrikler

    n_questions = int(df["question"].nunique())  # Benzersiz soru sayısı
    n_rows = int(len(df))  # Satır sayısı (genelde soru sayısı ile aynı olur)

    # NaN sayıları (rapora "bazı metrikler NaN döndü" gibi bir not koymak için faydalı)
    nan_counts = {f"{m}_nan_count": int(df[m].isna().sum()) for m in metrics}

    # Metrik ortalamaları (pandas varsayılan olarak NaN'leri ortalamadan hariç tutar)
    means = {f"{m}_mean": float(df[m].mean()) for m in metrics}

    # Üç metriğin ortalaması (notebook'taki overall mean mantığı) :contentReference[oaicite:3]{index=3}
    overall_mean = float(pd.Series([means["context_recall_mean"], means["faithfulness_mean"], means["answer_relevancy_mean"]]).mean())

    return {
        "model": model_name,
        "n_rows": n_rows,
        "n_questions": n_questions,
        **means,
        "overall_mean": overall_mean,
        **nan_counts,
    }


def _per_question_compare(gemini_df: pd.DataFrame, openai_df: pd.DataFrame) -> pd.DataFrame:
    """
    Soru bazlı karşılaştırma üretir.
    Aynı soru iki raporda da varsa metrikleri yan yana koyar ve farklarını hesaplar.
    """
    metrics = ["context_recall", "faithfulness", "answer_relevancy"]

    g = gemini_df[["question"] + metrics].copy()  # Gemini soru + metrikler
    o = openai_df[["question"] + metrics].copy()  # OpenAI soru + metrikler

    # Kolon isimlerini çakışmaması için yeniden adlandır
    g = g.rename(columns={m: f"{m}_gemini" for m in metrics})
    o = o.rename(columns={m: f"{m}_openai" for m in metrics})

    # Soru üzerinden birleştir (inner: sadece iki tarafta da olan sorular)
    merged = pd.merge(g, o, on="question", how="inner")

    # Fark kolonları: openai - gemini
    for m in metrics:
        merged[f"{m}_diff_openai_minus_gemini"] = merged[f"{m}_openai"] - merged[f"{m}_gemini"]

    return merged


def main() -> None:
    """Ana akış: raporları oku, özet ve soru bazlı karşılaştırma üret, CSV'ye yaz."""
    os.makedirs(OUT_DIR, exist_ok=True)  # reports klasörü yoksa oluştur

    # 1) Raporları yükle
    gemini_df = _load_report(GEMINI_REPORT_PATH)  # Gemini raporunu oku
    openai_df = _load_report(OPENAI_REPORT_PATH)  # OpenAI raporunu oku

    # 2) Özet karşılaştırma tablosu
    summary_rows = [
        _summarize(gemini_df, "gemini"),
        _summarize(openai_df, "openai"),
    ]
    summary_df = pd.DataFrame(summary_rows)

    # 3) Soru bazlı karşılaştırma tablosu
    per_q_df = _per_question_compare(gemini_df, openai_df)

    # 4) CSV çıktıları kaydet
    summary_df.to_csv(SUMMARY_OUT_PATH, index=False)  # Özet tabloyu yaz
    per_q_df.to_csv(PER_QUESTION_OUT_PATH, index=False)  # Soru bazlı tabloyu yaz

    # 5) Terminale kısa çıktı ver (rapora kopyalamak istersen diye)
    print("SUMMARY (rapora eklenebilir özet tablo):")
    print(summary_df.to_string(index=False))
    print("\nYazılan dosyalar:")
    print(f"- {SUMMARY_OUT_PATH}")
    print(f"- {PER_QUESTION_OUT_PATH}")


if __name__ == "__main__":
    main()  # Script doğrudan çalıştırıldığında main() çağır
