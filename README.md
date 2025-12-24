# Cosmetic RAG Assistant

## Proje Özeti

Bu proje, kozmetik ürün verilerinin Excel (XLSX) formatında yüklenerek bir **knowledge base (KB)** haline getirildiği ve kullanıcıların doğal dilde sordukları sorulara **RAG (Retrieval-Augmented Generation)** yaklaşımıyla cevap alabildiği bir web uygulamasıdır.

Sistem iki ana rolü ayırır:

* **Kullanıcı (Chat ekranı):** Ürünler hakkında serbest sohbet edebilir, öneri isteyebilir ve sorular sorar.
* **Admin (Admin sekmesi):** Yeni ürün verilerini yükler ve knowledge base’i sıfırdan indeksler.

Amaç; ham tablo verisini doğrudan LLM’e vermek yerine, kontrollü ve açıklayıcı metin dokümanlarına dönüştürerek daha güvenli ve tutarlı cevaplar üretmektir.

---

## Temel Mimari Yaklaşım

Proje üç ana katmandan oluşur:

1. **Arayüz Katmanı (Streamlit)**
2. **Retrieval Katmanı (Embeddings + ChromaDB)**
3. **Cevap Üretim Katmanı (Gemini LLM)**

Bu katmanlar bilinçli olarak birbirinden ayrılmıştır. Böylece hem sade bir MVP elde edilir hem de ileride yeni özellikler eklenebilir.

---

## Kullanıcı Arayüzü (Streamlit)

Uygulama tek bir `app.py` dosyası üzerinden çalışır ve iki sekme içerir:

### 1. Chat Sekmesi

* Son kullanıcıya yöneliktir.
* Klasik bir chat ekranı gibi davranır.
* Mesajlar kronolojik olarak yukarıdan aşağıya sıralanır.
* Input alanı her zaman ekranın en altında sabit kalır.

Kullanıcı:

* Normal sohbet edebilir (selam, genel sorular vb.)
* Ürün önerisi isteyebilir.
* Ürünler hakkında detay sorular sorabilir.

Kullanıcı bu ekranda:

* Dosya yüklemez
* Indexleme yapmaz
* Veritabanına doğrudan erişmez

### 2. Admin Sekmesi

* Teknik yönetim ekranıdır.
* Sadece XLSX dosyası kabul edilir.
* Yüklenen dosya:

  * Pandas ile okunur
  * Zorunlu kolonlar kontrol edilir
  * Her satır bir ürün olarak işlenir

Admin **“KB oluştur ve indexle”** butonuna bastığında:

* Eski knowledge base tamamen silinir
* Yeni ürünler sıfırdan embedding’lenir
* ChromaDB’ye persist edilir

Bu davranış bilinçlidir ve deterministik bir KB durumu sağlar.

---

## Veri Girişi ve İşleme

### Desteklenen Format

* XLSX (CSV bilinçli olarak kapsam dışıdır)

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

Her ürün satırı için şu ilke uygulanır:

> **1 ürün = 1 doküman**

`services/document_builder.py`:

* Ürün bilgilerini tek parça, doğal dilli bir metne dönüştürür.
* Bu metin LLM’e verilecek bağlamdır.

Doküman; ürün adı, marka, kategori, fiyat, puan, uygun cilt tipleri ve ingredients bilgilerini içerir.

---

## Embedding ve Vector Database (ChromaDB)

### Embedding

* Google Gemini `text-embedding-004` modeli kullanılır.
* Her doküman 768 boyutlu bir vektöre çevrilir.

### ChromaDB

* Vektörler `db/` klasörü altında persist edilir.
* Tek collection kullanılır: `cosmetics_kb`
* Her indexleme işleminde:

  * Eski collection silinir
  * Yeni embedding’ler sıfırdan yazılır

Bu yaklaşım:

* Embedding boyutu çakışmalarını önler
* Kirli veri riskini azaltır

---

## Retrieval (Semantic Search)

Kullanıcı chat ekranında soru sorduğunda:

1. Soru embedding’e çevrilir
2. ChromaDB’de semantic search yapılır
3. En alakalı N doküman getirilir
4. Bu dokümanlar LLM’e context olarak verilir

Bu aşamada keyword arama yoktur; tamamen anlamsal benzerlik kullanılır.

---

## LLM Katmanı (Gemini)

* Google Gemini Chat modeli kullanılır (`gemini-2.5-flash`).
* Düşük temperature ile daha tutarlı cevaplar hedeflenir.

### Prompt Yaklaşımı

Tek bir ana prompt kullanılır. Prompt:

* Normal sohbet ile ürün sorularını ayırt eder
* Ürün sorusuysa:

  * Cevabın KB’ye dayandığını belirtir
  * Önce kısa ürün tanıtımı yapar
  * Detay istenmedikçe uzun analiz yapmaz
* Emin olunmayan konularda:

  * “belirlenemedi” ifadesini kullanır
  * “olabilir / risk taşıyabilir” diliyle konuşur

Intent sınıflandırması için ayrı bir model veya kural sistemi yoktur; karar prompt içinde alınır.

---

## Chat Akışı ve State Yönetimi

* Tüm mesajlar `st.session_state["messages"]` içinde tutulur.
* Mesajlar sırayla yeniden render edilir.
* Kullanıcı mesajı gönderildiğinde:

  * Anında ekranda görünür
  * Asistan cevap üretirken spinner gösterilir
  * Cevap geldikten sonra state güncellenir

Bu yapı, klasik chat uygulamalarına benzer bir kullanıcı deneyimi sağlar.

---

## Klasör Yapısı

```
mat409-chatbot/
├─ app.py
├─ services/
│  ├─ ingestion.py
│  ├─ document_builder.py
│  ├─ embeddings.py
│  ├─ rag.py
│  └─ llm.py
├─ utils/
│  └─ validators.py
├─ data/
│  └─ uploads/
├─ db/
├─ .env
└─ requirements.txt
```

* `data/` → ham Excel dosyaları (sadece indexleme sırasında kullanılır)
* `db/` → ChromaDB persist edilen vector database

