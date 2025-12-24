# Cosmetic RAG Assistant

## Proje Amacı

Bu proje, kozmetik ürün verilerinin Excel (XLSX) formatında yüklenerek bir **knowledge base (KB)** haline getirildiği ve kullanıcıların doğal dilde sordukları sorulara **LangChain tabanlı gerçek bir RAG (Retrieval‑Augmented Generation) zinciri** üzerinden cevap alabildiği bir web uygulamasıdır.

Temel hedefler:

* Ham tablo verisini doğrudan LLM’e vermemek
* Her ürünü açıklayıcı, tek parça metinsel dokümana dönüştürmek
* Bu dokümanları vektör veritabanında saklamak
* Kullanıcı sorularına yalnızca bu KB’ye dayanarak cevap üretmek

Bu sürüm, LangChain zincirlerinin (Retriever + LLM + History) **gerçek anlamda kullanıldığı** final mimariyi temsil eder.

---

## Genel Mimari

Sistem üç ana katmandan oluşur:

1. **Arayüz Katmanı (Streamlit)**
2. **Retrieval Katmanı (LangChain + ChromaDB)**
3. **Cevap Üretim Katmanı (Gemini LLM)**

RAG orkestrasyonu LangChain tarafından yapılır. UI ve veri yükleme süreçleri zincirden izole tutulur.

---

## Arayüz Yapısı (Streamlit)

Uygulama tek bir `app.py` dosyası üzerinden çalışır ve iki sekme içerir:

### 1) Chat Sekmesi

* Son kullanıcıya yöneliktir.
* Klasik bir chat ekranı gibi davranır.
* Mesajlar kronolojik olarak yukarıdan aşağıya sıralanır.
* Giriş (input) alanı her zaman ekranın en altında sabittir.
* Asistan cevap üretirken "Yazıyor..." durumu gösterilir.

Kullanıcı bu ekranda:

* Normal sohbet edebilir
* Ürün önerisi isteyebilir
* Ürünler hakkında detay sorular sorabilir

Chat ekranında:

* Dosya yükleme
* Indexleme
* Veritabanı işlemleri

bulunmaz.

### 2) Admin Sekmesi

* Teknik yönetim ekranıdır.
* Sadece XLSX dosyası kabul edilir.
* Yüklenen dosya:

  * Pandas ile okunur
  * Zorunlu kolonlar doğrulanır
  * Her satır bir ürün olarak işlenir

**“KB oluştur ve indexle”** butonuna basıldığında:

* Mevcut knowledge base tamamen silinir
* Yeni ürünler sıfırdan embedding’lenir
* ChromaDB’ye persist edilir

Bu reset davranışı bilinçlidir ve deterministik bir KB durumu sağlar.

---

## Veri Girişi

### Desteklenen Format

* XLSX

CSV desteği bilinçli olarak kapsam dışıdır.

### Beklenen Kolonlar

* Label
* Brand
* Name
* Price
* Rank
* Ingredients
* Combination
* Dry
* Normal
* Oily
* Sensitive

Kolon doğrulaması `utils/validators.py` içinde yapılır.

---

## Sentetik Doküman Üretimi

Her ürün için şu ilke uygulanır:

> **1 ürün = 1 doküman**

`services/document_builder.py`:

* Ürün bilgilerini tek parça, doğal dilli bir metne dönüştürür
* Bu metin, LLM’e verilecek bağlamdır

Amaç:

* Tutarlı
* Açıklayıcı
* RAG uyumlu dokümanlar üretmektir

---

## Embedding ve Vector Database

### Embedding

* Google Gemini `text-embedding-004` modeli kullanılır
* Her doküman 768 boyutlu bir vektöre dönüştürülür

### ChromaDB

* Vektörler `db/` klasörü altında persist edilir
* Tek collection kullanılır: `cosmetics_kb`
* Her indexleme işleminde:

  * Collection tamamen silinir
  * Yeni embedding’ler sıfırdan yazılır

Bu yaklaşım embedding boyutu uyuşmazlığı ve kirli veri riskini ortadan kaldırır.

---

## LangChain RAG Zinciri

Bu projede RAG orkestrasyonu **LangChain** ile yapılır.

### Kullanılan Zincir

* **ConversationalRetrievalChain**

### Zincir Bileşenleri

* **VectorStore**: Chroma (persist edilmiş)
* **Retriever**: `vectorstore.as_retriever(k=5)`
* **LLM**: Google Gemini (`gemini-2.5-flash`)
* **History**: Streamlit `session_state` üzerinden sağlanır

Zincir `services/langchain_rag.py` dosyasında tanımlıdır.

### History Yönetimi

* Chat geçmişi UI tarafında tutulur
* `(user, assistant)` çiftleri LangChain zincirine aktarılır
* Zincir önceki konuşmaları dikkate alarak cevap üretir

---

## Soru–Cevap Akışı

1. Kullanıcı mesaj gönderir
2. Mesaj chat geçmişine eklenir
3. LangChain zinciri çalışır:

   * Soru embedding’e çevrilir
   * ChromaDB semantic search yapar
   * En alakalı dokümanlar alınır
4. Gemini LLM yalnızca bu dokümanlara dayanarak cevap üretir
5. Cevap chat ekranında gösterilir

---

## Indexleme Stratejisi

* Indexleme **reset temellidir**
* Her yeni XLSX yüklemede:

  * Eski collection silinir
  * Yeni collection oluşturulur

Bu strateji:

* Deterministik sonuçlar
* Basit admin davranışı
* Hata riskinin azalması

sağlar.

---

## Klasör Yapısı

```
mat409-chatbot/
├─ app.py
├─ services/
│  ├─ ingestion.py
│  ├─ document_builder.py
│  ├─ rag.py
│  ├─ langchain_rag.py
├─ utils/
│  └─ validators.py
├─ data/
│  └─ uploads/
├─ db/
├─ .env
└─ requirements.txt
```

* `data/` → ham Excel dosyaları (sadece indexleme sırasında kullanılır)
* `db/` → ChromaDB’nin persist edilmiş vector veritabanı
