# Cosmetic RAG Assistant

## Proje Amacı

Bu proje, kozmetik ürün verilerinin Excel (XLSX) formatında yüklenerek bir **knowledge base (KB)** haline getirildiği ve kullanıcıların doğal dilde sordukları sorulara **LangChain tabanlı bir RAG (Retrieval‑Augmented Generation)** akışıyla cevap alabildiği bir Streamlit uygulamasıdır.

Temel hedefler:

- Ham tablo verisini doğrudan LLM’e vermemek
- Her ürünü **tek bir sentetik metin dokümanına** dönüştürmek (1 ürün = 1 doküman)
- Bu dokümanları embedding’leyip **ChromaDB** içinde saklamak
- Kullanıcı sorularına yalnızca bu KB’ye dayanarak cevap üretmek

---

## Teknoloji Yığını

- **UI:** Streamlit
- **RAG Orkestrasyonu:** LangChain
- **LLM:** Google Gemini (`gemini-2.5-flash`)
- **Embeddings:** Google Gemini (`text-embedding-004`)
- **Vector DB:** ChromaDB (persist: `db/`)

---

## Uygulama Akışı

Uygulama iki sekmeden oluşur:

### 1) Chat

- Kullanıcı sohbet ekranından soru sorar
- Sistem, ChromaDB içinden ilgili ürün dokümanlarını getirir (semantic retrieval)
- **Retriever, yalnızca son soruya değil, konuşma geçmişini de içeren bir metne göre arama yapar**
- Gemini modeli, getirilen dokümanlara dayanarak yanıt üretir
- Mesajlar `st.session_state["messages"]` içinde tutulur

> Not: Konuşma geçmişinin retriever girdisine eklenmesi bilinçli bir tercihtir. Amaç, takip sorularında bağlam kaybını azaltmaktır.

---

### 2) Admin

- XLSX dosyası yüklenir
- Kolonlar doğrulanır
- Her satır için bir ürün dokümanı üretilir
- Dokümanlar embedding’lenir ve ChromaDB’ye yazılır
- Her indexleme işleminde collection sıfırlanır (temiz yeniden kurulum)

---

## Veri Girişi

### Desteklenen Format

- XLSX

### Beklenen Kolonlar

- Label
- Brand
- Name
- Price
- Rank
- Ingredients
- Combination
- Dry
- Normal
- Oily
- Sensitive

Kolon doğrulama `utils/validators.py` içinde yapılır.

---

## Sentetik Doküman Üretimi

Her ürün için şu ilke uygulanır:

> **1 ürün = 1 doküman**

`services/document_builder.py`:

- Ürün alanlarını tek bir, doğal dilli metin haline getirir
- Indexleme sırasında opsiyonel olarak LLM kullanarak:
  - kısa ürün tanıtımı
  - içerik analizi (risk dili: “olabilir”)
  üretir
- LLM kullanılmadığında güvenli fallback metinler kullanılır

Bu metinler embedding’e giren asıl dokümanlardır.

---

## Indexleme ve Vector Database (ChromaDB)

Indexleme fonksiyonu:

`services/rag.py → index_documents_to_chroma_with_embeddings`

Strateji:

1. Mevcut collection varsa tamamen silinir
2. `text-embedding-004` modeli ile embedding alınır
3. Dokümanlar, metadata ve stabil `product_id` ile ChromaDB’ye eklenir
4. Veritabanı `db/` klasörüne persist edilir

Collection adı: `cosmetics_kb`

Bu reset temelli yaklaşım:

- Embedding boyutu uyuşmazlıklarını
- Kirli veri problemlerini

bilinçli olarak önler.

---

## LangChain RAG Zinciri

Zincir tanımı: `services/langchain_rag.py`

Kullanılan yapı:

- Persist edilmiş **Chroma VectorStore**
- `vectorstore.as_retriever(k=5)`
- `ChatPromptTemplate` (system + human)
- `create_stuff_documents_chain`
- `create_retrieval_chain`

System prompt prensipleri:

- Cevap yalnızca `{context}` içindeki bilgiye dayanır
- Bağlamda yoksa: **“Bunu mevcut bilgi tabanında bulamadım.”**
- Tıbbi teşhis veya kesin yargı yok
- Emin olunmayan durumlarda: **“belirlenemedi”**
- Kısa ve net cevaplar

---

## Konuşma Geçmişi ve Retrieval Kararı

Bu projede konuşma geçmişi:

- UI tarafında tutulur
- Retriever’a giden sorgu metnine eklenir

Bu yaklaşımın amacı:

- Takip sorularında bağlam kopmasını azaltmak
- "Bu ürün peki hassas ciltte?" gibi referanslı soruları daha doğru eşleştirmek


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

- `data/uploads/`: Admin yüklemeleri
- `db/`: ChromaDB persist dosyaları

---

## Kurulum (Windows + VSCode)

### 1) Sanal ortam oluştur

```bash
python -m venv venv
```

### 2) Sanal ortamı aktif et

```bash
venv\Scripts\activate
```

### 3) Bağımlılıkları kur

```bash
pip install -r requirements.txt
```

### 4) Ortam değişkenlerini ayarla

Proje kökünde `.env` dosyası oluştur:

```env
GOOGLE_API_KEY=YOUR_API_KEY
```

### 5) Uygulamayı çalıştır

```bash
streamlit run app.py
```

---

## Kullanım

1. **Admin** sekmesine geç
2. XLSX dosyasını yükle
3. "KB oluştur ve indexle" butonuna bas
4. **Chat** sekmesine geçerek soru sor


