Cosmetic RAG Assistant – Teknik Proje Açıklaması
1. Projenin Amacı

Bu proje, kozmetik ürün verilerinin (Excel/XLSX formatında) bir knowledge base (KB) haline getirilip, kullanıcıların doğal dilde sordukları sorulara RAG (Retrieval-Augmented Generation) yaklaşımıyla cevap verilmesini amaçlayan bir web uygulamasıdır.

Sistem:

Ürün verilerini dışarıdan yükler

Bu verilerden sentetik dokümanlar üretir

Dokümanları vektör veritabanına indeksler

Kullanıcı sorularını semantik olarak bu verilerle eşleştirir

Büyük dil modeli (Gemini) ile yalnızca bu veriye dayanarak cevap üretir

Son kullanıcı yalnızca sohbet ekranını görür.
Ürün güncelleme ve indeksleme işlemleri ayrı bir Admin sekmesinden yapılır.

2. Genel Mimari

Uygulama üç ana katmandan oluşur:

Arayüz (Streamlit)

Veri & Retrieval Katmanı (ChromaDB + Embeddings)

Cevap Üretim Katmanı (Gemini LLM)

Bu katmanlar bilinçli olarak birbirinden ayrılmıştır.

3. Kullanıcı Arayüzü (Streamlit)

Uygulama tek bir app.py dosyası üzerinden çalışır ve iki sekmeye ayrılmıştır:

3.1 Chat Sekmesi (Son Kullanıcı)

Kullanıcı uygulamaya girdiğinde bu sekmeyi görür

Klasik bir chat ekranı gibi çalışır

Mesajlar kronolojik olarak yukarıdan aşağıya dizilir

Input alanı her zaman ekranın en altında sabit kalır

Kullanıcı:

Normal sohbet edebilir (selam, soru vb.)

Ürün önerisi isteyebilir

Ürünlerle ilgili detay sorabilir

Kullanıcı:

Excel yüklemez

İndeksleme yapmaz

Veritabanına doğrudan erişmez

3.2 Admin Sekmesi

Ürün verisinin yönetildiği teknik ekrandır

Sadece XLSX dosyası kabul edilir

Yüklenen dosya:

Pandas ile okunur

Zorunlu kolonlar kontrol edilir

Her satır bir ürün olarak işlenir

Admin “KB oluştur ve indexle” butonuna bastığında:

Eski vektör koleksiyonu silinir

Yeni ürünler embedding’lenerek yeniden indekslenir

Bu sekme, son kullanıcıdan izole edilmiştir.

4. Veri İşleme ve Doküman Üretimi
4.1 Excel → DataFrame

Admin sekmesinde yüklenen XLSX dosyası:

services/ingestion.py üzerinden pandas ile okunur

Kolonlar utils/validators.py içinde tanımlı kurallara göre doğrulanır

Her satır:

Tek bir ürünü temsil eder

4.2 Sentetik Doküman Üretimi

Her ürün satırı için:

services/document_builder.py kullanılarak

1 ürün = 1 doküman prensibiyle

Metinsel bir ürün dokümanı üretilir

Bu doküman:

Ürün adı

Marka

Kategori

Fiyat

Puan

Uygun cilt tipleri

Ingredients bilgisi

gibi alanları içerir.

Amaç:

LLM’in çalışabileceği, tutarlı ve normalize edilmiş bir metin üretmektir.

5. Vektör Veritabanı ve Retrieval (ChromaDB)
5.1 Embedding

Dokümanlar Google Gemini’nin embedding modeli (text-embedding-004) ile vektöre çevrilir

Her doküman 768 boyutlu bir embedding vektörü haline gelir

5.2 ChromaDB

Vektörler ChromaDB içinde saklanır

Persist edilen bir yapı vardır (db/ klasörü)

Her indeksleme işleminde:

Eski collection tamamen silinir

Boyut uyuşmazlığı ve kirli veri riski ortadan kaldırılır

5.3 Semantic Search

Kullanıcı mesajı geldiğinde:

Mesaj embedding’e çevrilir

ChromaDB’de en yakın vektörler aranır

En alakalı dokümanlar geri getirilir

Bu dokümanlar LLM için context oluşturur

Bu aşamada:

Keyword match değil

Tamamen semantik benzerlik kullanılır

6. LLM Katmanı (Gemini)
6.1 Model Seçimi

Google Gemini Chat modeli kullanılır

Projede çalışan model: gemini-2.5-flash

Düşük temperature ile daha tutarlı cevaplar hedeflenir

6.2 Prompt Tasarımı

Tek bir ana prompt vardır ve şu görevleri modele verir:

Önce kullanıcının mesajını yorumla

Normal sohbetse:

Ürün listeleme

Kısa, doğal cevap ver

Ürün sorusuysa:

Cevabın başında KB’ye dayandığını belirt

2–5 ürün öner

İlk yanıtta kısa tanıtım yap

Detay istenmedikçe uzun analiz yapma

Emin olunmayan yerde:

“belirlenemedi”

“olabilir / risk taşıyabilir” dili kullan

Bu yaklaşım sayesinde:

Intent sınıflandırması için ekstra kod yazılmamıştır

Karar mekanizması prompt içine gömülmüştür

7. Chat Akışı ve State Yönetimi

Tüm mesajlar st.session_state["messages"] içinde tutulur

Her mesaj:

role: user / assistant

content: mesaj metni

Mesaj gönderildiğinde:

Kullanıcı mesajı anında ekranda gösterilir

Asistan tarafında “Yazıyor…” spinner’ı görünür

Retrieval + LLM cevabı üretilir

Cevap ekrana yazılır

Input alanı bu süreçte:

Kaybolmaz

Ekranın en altında sabit kalır

8. Bilinçli Olarak Yapılmayanlar

Bu projede özellikle şunlar bilinçli olarak yapılmamıştır:

CSV desteği

Manuel filtreleme (kategori, fiyat, checkbox vb.)

Slot filling

Intent classifier modeli

Çoklu kullanıcı / auth

Chat geçmişi özetleme

Prompt zincirleme

Ama mimari bu özelliklerin ileride eklenmesine uygundur.

9. Sonuç

Bu proje:

Gerçek bir RAG mimarisini

Basit ama doğru bir şekilde

Uçtan uca çalışan bir sistem olarak

Web arayüzüyle birleştirmektedir

Amaç:

“Demo” değil

Genişletilebilir, temiz bir temel oluşturmaktır

Bu haliyle proje:

Teknik olarak anlatılabilir

Akademik veya portföy amaçlı sunulabilir

Üzerine rahatça yeni özellikler eklenebilir