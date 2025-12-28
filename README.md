# Cosmetic RAG Assistant

## 1. Proje

Bu proje, kozmetik ürün verilerini (XLSX) bir bilgi tabanına (Knowledge Base / KB) dönüştürüp, kullanıcıların doğal dilde sorduğu sorulara RAG (Retrieval-Augmented Generation) yaklaşımıyla cevap veren bir Streamlit uygulamasıdır.

Uygulama iki ana iş yapar:

1) Admin ekranında yüklenen Excel dosyasından (ürün tablosu) her ürün için RAG uyumlu metin dokümanları üretir ve ChromaDB’ye indeksler.

2) Chat ekranında kullanıcı sorusunu alır, ChromaDB’den en alakalı ürün dokümanlarını getirir ve LLM explain/cevap üretir.

Veri kaynağı: Kaggle Cosmetics Datasets (https://www.kaggle.com/datasets/kingabzpro/cosmetics-datasets?resource=download)

Demo videosu için: [buraya tıklayın.](https://drive.google.com/file/d/1Rw07_GH_wFvL0m_WJKErPYjR91sB27Kz/view?usp=sharing)

Not: Indexleme sırasında LLM desteği kullanılır. Bu sayede yalnızca “ham tablo alanları” değil, ürün tanıtımı ve içerik analizi gibi ek feature’lar (ör. komedojenik risk, iritasyon/hassasiyet riski, alerjen olabilecek bileşenler hakkında “olabilir” diliyle uyarılar) sentetik dokümana eklenir. Bu feature’lar dokümanın bir parçası olduğu için aramada da açıklamada da kullanılabilir.


## 2. Proje yapısı

Klasör yapısı özet:

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
├─ db_gemini/
├─ db_openai/
├─ requirements.txt
├─ .env.example
└─ README.md
```

Dosyalar ne işe yarar?

- `app.py`
  - Streamlit UI.
  - İki sekme içerir: Chat ve Admin.
  - Admin sekmesinde KB’yi oluşturur/indexler.
  - Chat sekmesinde RAG chain’i kullanır.

- `services/ingestion.py`
  - Yüklenen dosyayı okur.
  - Bu projede bilinçli olarak sadece XLSX kabul edilir.

- `utils/validators.py`
  - Dataset’te beklenen zorunlu kolonlar var mı kontrol eder.

- `services/document_builder.py`
  - Tek ürün satırından tek bir “sentetik ürün dokümanı” üretir.
  - LLM verilirse `Ürün tanıtımı` ve `İçerik analizi` alanlarını LLM ile doldurur.
  - LLM yoksa veya hata olursa fallback metin döner.

- `services/rag.py`
  - `make_product_id`: ürün için stabil id üretir (aynı ürün tekrar gelirse id sabit kalsın).
  - `index_documents_to_chroma_with_embeddings`: embedding alır ve ChromaDB’ye yazar.
  - Indexleme sırasında aynı collection’ı silip yeniden kurar (dimension mismatch / kirli data riskini azaltmak için).

- `services/langchain_rag.py`
  - LangChain RAG zincirini kurar.
  - Provider seçimine göre embedding ve LLM seçer.
  - Chroma’dan retriever oluşturur ve `create_retrieval_chain` ile QA zincirini bağlar.

- `db_gemini/` ve `db_openai/`
  - ChromaDB’nin persist edilen verisi.
  - Provider bazında ayrı tutulur (embedding boyutu / embedding modeli karışmasın diye).


## 3. Mimari akış (yükleme → indeksleme → sohbet)

### 3.1 Admin akışı (KB oluşturma)

Admin sekmesinde bu adımlar çalışır:

1) Kullanıcı XLSX dosyasını yükler.
2) `services/ingestion.py` dosyayı pandas ile okur.
3) `utils/validators.py` gerekli kolonları doğrular.
4) Her satır (1 ürün) için:
   - `services/rag.py` içindeki `make_product_id` ile id üretilir.
   - `services/document_builder.py` ile ürün dokümanı üretilir.
     - LLM varsa: kısa tanıtım ve içerik analizi alanları otomatik üretilir.
     - Bu analizler “kesin hüküm” vermez; risk dili “olabilir / risk taşıyabilir” şeklindedir.
   - Metadata hazırlanır (name, brand, label, price, rank).
5) Tüm dokümanlar embedding’lenir ve ChromaDB’ye yazılır.
6) Yeni indexleme bitince chat tarafındaki chain cache’i sıfırlanır (yeni KB ile arama yapsın diye).

### 3.2 Chat akışı (RAG)

Chat sekmesinde bu adımlar çalışır:

1) Kullanıcı soru yazar.
2) Son mesajlar (kısa konuşma geçmişi) tek bir metne çevrilir.
3) Bu metin, retriever’a sorgu olarak verilir.
4) ChromaDB en yakın `k` dokümanı getirir.
5) LLM, yalnızca bu `context` ile cevap üretir.
6) Cevap chat ekranında gösterilir ve konuşma geçmişine eklenir.

Not: Konuşma geçmişi retriever sorgusuna eklenir. Amaç, takip sorularında (örn. “bu ürün hassas ciltte?”) bağlam kaybını azaltmaktır.


## 4. Kullanılan teknolojiler

- UI: Streamlit
- RAG orkestrasyonu: LangChain
- Vector DB: ChromaDB (persist mod)
- Embeddings:
  - Gemini: `models/text-embedding-004`
  - OpenAI: `text-embedding-3-small`
- LLM:
  - Gemini: `gemini-2.5-flash`
  - OpenAI: `gpt-4o-mini`


## 5. Kurulum (Windows + VSCode)

### 5.1 Repo’yu VSCode ile açma

- Proje klasörü bilgisayara indirildikten veya klonlandıktan sonra, VSCode içinde `File > Open Folder` ile açılabilir.

### 5.2 Python ve sanal ortam (venv)

Sanal ortam (venv) kullanılması, proje bağımlılıklarının diğer projelerle çakışma ihtimalini azaltır.

1) VSCode içinde `Terminal > New Terminal` ile terminal açılabilir.
2) Sanal ortam şu komutla oluşturulabilir:

```bash
python -m venv .venv
```

3) PowerShell üzerinde sanal ortam şu komutla aktive edilebilir:

```bash
.\.venv\Scripts\Activate.ps1
```

Eğer PowerShell script çalıştırma kısıtıyla karşılaşılırsa, aşağıdaki komut yardımcı olabilir:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

4) VSCode Python interpreter seçimi için, sağ altta görünen Python sürümüne tıklanıp `.venv` içindeki interpreter seçilebilir.

### 5.3 Paketlerin kurulumu

Gerekli paketler `requirements.txt` üzerinden kurulabilir:

```bash
pip install -r requirements.txt
```

### 5.4 .env dosyasının hazırlanması

Proje, API anahtarlarını `.env` dosyasından okur.

- `.env.example` dosyası kopyalanıp `.env` adıyla kaydedilebilir.
- İçerisine ilgili anahtarlar eklenebilir:

```
GOOGLE_API_KEY="..."
OPENAI_API_KEY="..."

# LangSmith (opsiyonel)
# LANGSMITH_TRACING=true
# LANGSMITH_API_KEY="..."
# LANGSMITH_PROJECT=mat409-chatbot
```

Notlar:
- Admin sekmesinde doküman zenginleştirme (tanıtım/analiz) için LLM kullanılmaktadır.
- Chat tarafında provider seçimine göre OpenAI veya Gemini kullanılabilir.


## 6. Uygulamayı çalıştırma

Terminalde (sanal ortam aktifken) aşağıdaki komutla uygulama başlatılabilir:

```bash
streamlit run app.py
```

Komut çalıştıktan sonra tarayıcıda uygulama arayüzü açılır.


## 7. Kullanım

### 7.1 Admin sekmesi

Admin sekmesi, ürün KB’sinin oluşturulup indekslendiği alandır.

- XLSX dosyası yüklendikten sonra dosya okunur ve kolonlar doğrulanır.
- “KB oluştur ve indexle” işlemi başlatıldığında her satır (ürün) için bir metin dokümanı üretilir ve embedding alınarak ChromaDB’ye yazılır.
- İndeksleme tamamlandığında chat tarafındaki zincir (chain) sıfırlanır; böylece sohbet ekranı yeni KB üzerinden arama yapar.

Önemli not:
- Bu projede her indeksleme, aynı collection’ı silip yeniden oluşturarak yapılır. Bu tercih, embedding boyutu uyuşmazlığı gibi sorunları azaltmayı hedefler.
- Provider’a göre veri dizini ayrıdır: `db_openai` veya `db_gemini`.

### 7.2 Chat sekmesi

Chat sekmesi, kullanıcının doğal dilde soru sorabildiği ve RAG akışıyla yanıt alabildiği ekrandır.

- Kullanıcı mesajı alındıktan sonra, kısa bir konuşma geçmişi metne dönüştürülerek retriever sorgusuna dahil edilir.
- ChromaDB’den en alakalı dokümanlar getirilir.
- LLM, yalnızca getirilen bağlama dayanarak yanıt üretir.

Örnek soru türleri:
- “Kuru cilt için uygun nemlendirici önerir misin?”
- “Hassas ciltte iritasyon riski düşük olabilecek ürünleri listeler misin?”
- “Bu ürün komedojenik risk taşıyabilir mi?”

Not: Bağlamda bulunmayan bilgiler için sistem, “Bunu mevcut bilgi tabanında bulamadım.” ifadesini kullanacak şekilde kurgulanmıştır.


## 8. Provider (OpenAI / Gemini) seçimi

Uygulamada sağlayıcı seçimi `app.py` dosyasındaki şu değişkenle yapılır:

```python
PROVIDER = "openai"
```

- `openai` seçildiğinde:
  - Embedding: `text-embedding-3-small`
  - Chat LLM: `gpt-4o-mini`
  - Persist dizini: `db_openai`
  - Collection: `cosmetics_kb_openai`

- `gemini` seçildiğinde:
  - Embedding: `models/text-embedding-004`
  - Chat LLM: `gemini-2.5-flash`
  - Persist dizini: `db_gemini`
  - Collection: `cosmetics_kb_gemini`

Teknik not:
- Embedding boyutları sağlayıcıya göre farklılık gösterebildiğinden, DB dizinlerinin ve collection isimlerinin ayrıştırılması bilinçli bir tercihtir.


## 9. Dataset kolonları ve doğrulama

Beklenen kolonlar:

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


## 10. Sentetik doküman formatı

Her ürün için tek bir metin dokümanı üretilir. Yapı örneği:

- Ürün adı
- Marka
- Kategori
- Fiyat
- Puan
- Uygun cilt tipleri
- Ürün tanıtımı (LLM ile)
- İçerik analizi (LLM ile)
- Ingredients

LLM guardrail yaklaşımı:
- Yeni ingredient uydurma yok.
- Teşhis yok, kesin hüküm yok.
- Risk dili “olabilir / risk taşıyabilir”.
- Emin olunmayan yerde “belirlenemedi”.

Bu yaklaşım sayesinde alerjen veya iritan olabilecek içerikler hakkında, kesinlik iddiası olmadan bilgilendirici uyarılar üretilebilir.


## 11. LangSmith (opsiyonel izleme ve debug)

Bu projede LangChain akışlarını gözlemlemek ve debug sürecini kolaylaştırmak amacıyla **LangSmith** entegrasyonu opsiyonel olarak desteklenmektedir.

LangSmith kullanıldığında:
- Retriever ve LLM çağrılarının hangi sırayla çalıştığı izlenebilir.
- Her bir sorguda hangi dokümanların getirildiği görülebilir.
- Prompt, input ve output’lar merkezi bir panel üzerinden incelenebilir.

LangSmith’i aktif etmek için `.env` dosyasına aşağıdaki değişkenlerin eklenmesi yeterlidir:

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY="..."
LANGSMITH_PROJECT=mat409-chatbot
```

Bu ayarlar yapıldığında, uygulama çalışırken LangChain zincirleri otomatik olarak LangSmith paneline loglanır.

Notlar:
- LangSmith tamamen opsiyoneldir; aktif edilmediğinde uygulamanın çalışma şeklinde herhangi bir değişiklik olmaz.
- Geliştirme ve performans analizi aşamalarında fayda sağlar.


