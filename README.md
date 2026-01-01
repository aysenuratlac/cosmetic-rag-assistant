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
cosmetic-rag-assistant/
├─ app.py
├─ services/
│ ├─ ingestion.py
│ ├─ document_builder.py
│ ├─ rag.py
│ ├─ langchain_rag.py
├─ utils/
│ └─ validators.py
├─ data/
│ └─ uploads/
├─ db_openai/
├─ db_gemini/
├─ scripts/
│ ├─ build_ragas_testset.py
│ └─ run_ragas_eval.py
├─ test_data/
│ ├─ ragas_testset_openai.jsonl
│ └─ ragas_testset_gemini.jsonl
├─ reports/
│ ├─ ragas_report_openai.csv
│ ├─ ragas_report_openai.md
│ ├─ ragas_report_gemini.csv
│ ├─ ragas_report_gemini.md
│ └─ report_analysis.ipynb
├─ requirements.txt
├─ .env.example
└─ README.md
```

Dosyalar ve klasörler ne işe yarar?

- `app.py`
  - Streamlit tabanlı ana uygulama dosyasıdır.
  - Chat ve Admin sekmelerini içerir.
  - Admin sekmesinde KB oluşturma ve indexleme işlemlerini yönetir.
  - Chat sekmesinde LangChain RAG zinciri ile soru-cevap akışını yürütür.

- `services/`
  - Projenin iş mantığını (business logic) içeren modülleri barındırır.
  - `ingestion.py`: Yüklenen XLSX dosyasını okur ve DataFrame olarak döndürür.
  - `document_builder.py`: Her ürün satırından tek bir sentetik, RAG uyumlu metin dokümanı üretir.
  - `rag.py`: Ürünler için stabil `product_id` üretir ve dokümanları ChromaDB’ye indeksler.
  - `langchain_rag.py`: Embedding, retriever ve LLM’i birleştirerek LangChain RAG zincirini kurar.

- `utils/`
  - Yardımcı fonksiyonları içerir.
  - `validators.py`: Dataset’te beklenen zorunlu kolonların varlığını kontrol eder.

- `data/`
  - Uygulama üzerinden yüklenen dosyaların saklandığı dizindir.
  - `uploads/`: Admin sekmesinde yüklenen XLSX dosyaları burada tutulur.

- `db_openai/` ve `db_gemini/`
  - ChromaDB’nin persist edilen vektör verilerini içerir.
  - Embedding boyutu ve modeli karışmaması için provider bazında ayrılmıştır.

- `scripts/`
  - RAGAS değerlendirme sürecine ait script’leri içerir.
  - `build_ragas_testset.py`: Mevcut knowledge base üzerinden otomatik test seti üretir.
  - `run_ragas_eval.py`: Üretilen test seti ile RAGAS değerlendirmesini çalıştırır.

- `test_data/`
  - RAGAS için otomatik üretilmiş test setlerini içerir.
  - Test setleri JSONL formatındadır ve provider bazında ayrılmıştır.

- `reports/`
  - RAGAS değerlendirme çıktılarının kaydedildiği dizindir.
  - CSV dosyaları metrik sonuçlarını içerir.
  - Markdown dosyaları özet değerlendirme raporlarıdır.
  - `report_analysis.ipynb`, sonuçların manuel analizi ve incelenmesi için kullanılır.

- `requirements.txt`
  - Projenin Python bağımlılıklarını listeler.

- `.env.example`
  - Gerekli ortam değişkenleri için örnek yapılandırma dosyasıdır.

- `README.md`
  - Projenin kurulum, kullanım, mimari ve değerlendirme dokümantasyonunu içerir.


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

## 11. Doküman granülaritesi ve chunking kararı

Bu projede **chunking uygulanmamıştır**. Bilgi tabanı tasarımında bilinçli olarak şu yaklaşım seçilmiştir:

- **1 ürün = 1 sentetik doküman = 1 vektör**
- Her ürün satırı, tek bir metin dokümanına dönüştürülür ve ChromaDB’ye tek parça olarak indekslenir.

Bu tercih özellikle bu veri tipi için uygundur çünkü:
- Kaynak veri zaten “ürün kartı” gibi **doğal bir atomic birim** (tek ürün).
- Kullanıcı sorularının çoğu (fiyat, puan, cilt tipi uygunluğu, içerik yorumu) **tek ürün bağlamında** cevaplanır.
- Chunking yapılması, tek ürünün parçalanmasına ve retrieval’da bağlamın bölünmesine yol açabilir.


## 12. LangSmith (opsiyonel izleme ve debug)

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

## 13. RAGAS ile değerlendirme 

Geliştirilen RAG sisteminin retrieval ve cevap kalitesini ölçmek amacıyla **RAGAS** kullanılarak
otomatik, tekrar edilebilir ve savunulabilir bir değerlendirme süreci kurulmuştur.

### 13.1 Amaç
Değerlendirme kapsamında üç temel metrik kullanılmıştır:

- **context_recall**: Retrieval aşamasının başarısını ölçer.
- **faithfulness**: Üretilen cevabın gerçekten getirilen dokümanlara dayanıp dayanmadığını ölçer.
- **answer_relevancy**: Üretilen cevabın, sorulan soru ile ne kadar alakalı olduğunu ölçer.

### 13.2 Test seti üretimi
Test seti manuel olarak yazılmamış, mevcut knowledge base üzerinden otomatik üretilmiştir.

- Test seti üretim script’i:  
  `scripts/build_ragas_testset.py`
- Üretilen test setleri:  
  `test_data/`
  - `ragas_testset_openai.jsonl`
  - `ragas_testset_gemini.jsonl`

Her test örneği şu alanları içerir:
- `question`
- `ground_truth`
- `reference_context_ids` (ürünün `product_id` değeri)

Bu yapı sayesinde test seti:
- Knowledge base ile tutarlı
- Tekrar üretilebilir
- Otomatik değerlendirmeye uygundur

### 13.3 Değerlendirme akışı
Değerlendirme şu script ile gerçekleştirilir:

- Değerlendirme script’i:  
  `scripts/run_ragas_eval.py`

Bu script:
1. Test setini okur
2. Her soruyu mevcut LangChain RAG zincirine sorar
3. `answer`, `contexts`, `retrieved_context_ids` ve `reference_context_ids` alanlarını toplar
4. RAGAS `evaluate()` fonksiyonunu çalıştırır

### 13.4 Sonuç dosyaları
Değerlendirme çıktıları `reports/` klasörüne kaydedilir:

- CSV sonuçları:
  - `ragas_report_openai.csv`
  - `ragas_report_gemini.csv`
- Markdown özet raporları:
  - `ragas_report_openai.md`
  - `ragas_report_gemini.md`

Ayrıca sonuçların manuel analizi için:
- `reports/report_analysis.ipynb` notebook’u kullanılmıştır.

### 13.5 NaN değerler hakkında
Bazı örneklerde metrik sonuçları **NaN** olarak raporlanabilir. Bu durum bir hata değildir.

Genellikle şu durumlarda ortaya çıkar:
- `ground_truth` veya `answer` çok kısa ise
- Liste / etiket formatında ifade içeriyorsa
- RAGAS anlamlı bir doğal dil iddiası (claim) çıkaramıyorsa

Bu nedenle NaN değerler:
- Retrieval’ın başarısız olduğu
- Modelin uydurma yaptığı

anlamına **doğrudan gelmez**.



## 14. Sınırlılıklar ve gelecek çalışmalar

### 14.1 Sınırlılıklar
- Ürün içerik analizi ve risk uyarıları LLM tarafından üretilir ve **kesin teşhis / kesin hüküm** amaçlamaz; “olabilir” dili bir guardrail olarak korunur.
- Varsayılan retrieval akışı semantic similarity üzerinedir; metadata alanları ileride daha güçlü filtreleme/sıralama için genişletilebilir.
- RAGAS metriklerinde bazı örneklerde NaN görülebilir (kısa/liste formatlı ground-truth gibi durumlar).

### 14.2 Gelecek çalışmalar
- `retrieved_context_ids` ve `reference_context_ids` kullanılarak **ID tabanlı custom recall** metriği eklenmesi (debug ve daha doğrudan retrieval ölçümü için).
- Soru tipine göre farklı retrieval stratejileri (ör. fiyat sorularında daha deterministik alan odaklı yaklaşım).
- Daha geniş test seti ve farklı soru türleriyle (öneri, karşılaştırma, içerik hassasiyeti gibi) RAGAS değerlendirmesinin genişletilmesi.

