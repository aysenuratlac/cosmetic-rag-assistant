import os  # Dosya yolları ve klasör işlemleri için
import streamlit as st  # Streamlit arayüz bileşenleri için

from services.ingestion import load_table_file  # Yüklenen dosyayı tabloya çevirmek için
from utils.validators import validate_required_columns  # Kolon doğrulamak için

from dotenv import load_dotenv  # .env dosyasından ortam değişkenlerini okumak için

def ensure_directories() -> None:
    """
    Proje için gerekli klasörler var mı kontrol eder, yoksa oluşturur.
    """
    os.makedirs("data/uploads", exist_ok=True)  # Yüklenen dosyaların saklanacağı klasör
    os.makedirs("db", exist_ok=True)  # ChromaDB verisinin saklanacağı klasör


def save_uploaded_file(uploaded_file) -> str:
    """
    Streamlit üzerinden gelen dosyayı data/uploads altına kaydeder.

    Args:
        uploaded_file: Streamlit UploadedFile nesnesi.

    Returns:
        Kaydedilen dosyanın disk yolu.
    """
    file_path = os.path.join("data/uploads", uploaded_file.name)  # Dosyanın kaydedileceği yol
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())  # Dosyayı byte olarak diske yazar
    return file_path  # Kaydedilen yolu döndürür


def main() -> None:
    ensure_directories()  # Gerekli klasörler hazır mı kontrol eder

    load_dotenv()  # .env içindeki GOOGLE_API_KEY gibi değerleri ortam değişkeni olarak yükler

    st.set_page_config(page_title="Cosmetic RAG Assistant", layout="wide")  # Sayfa ayarları
    st.title("Cosmetic RAG Assistant")  # Uygulama başlığı
 

    st.sidebar.header("Adım 1: Veri Yükleme")  # Sol menü başlığı
    uploaded_file = st.sidebar.file_uploader(
        "XLSX dosyası yükle",  # Kullanıcıya gösterilecek metin
        type=["xlsx"],  # Kabul edilen dosya uzantıları
        accept_multiple_files=False,  # Tek dosya
    )  # Dosya yükleme alanı

    index_button_clicked = st.sidebar.button("KB oluştur ve indexle")  # Indexleme işlemini başlatan buton

    st.divider()  # Ayraç

    st.header("Chat / Öneri")  # Chat bölümü başlığı
    st.info("Henüz indexleme ve RAG bağlı değil. Bu adımda sadece dosya okuma ve kolon kontrolü yapıyoruz.")  # Bilgi kutusu

    user_message = st.text_input("Sorunu yaz")  # Kullanıcıdan soru alır
    send_clicked = st.button("Gönder")  # Gönder butonu

    if uploaded_file is None:
        st.sidebar.warning("Henüz dosya yüklenmedi.")  # Dosya yoksa uyarı
        st.stop()  # Dosya yokken aşağısı çalışmasın

    st.sidebar.success(f"Yüklendi: {uploaded_file.name}")  # Dosya seçildi bilgisi

    saved_path = save_uploaded_file(uploaded_file)  # Dosyayı diske kaydeder

    is_ok, message, df = load_table_file(saved_path)  # Dosyayı pandas ile okur
    if not is_ok or df is None:
        st.error(message)  # Okuma hatasını ekranda göster
        st.stop()  # Hata varsa devam etme

    st.success(message)  # Okuma başarılı mesajı

    actual_columns = list(df.columns)  # DataFrame kolonlarını listeye çevirir
    is_valid, missing = validate_required_columns(actual_columns)  # Zorunlu kolonları kontrol eder

    if not is_valid:
        st.error("Eksik kolonlar bulundu:")  # Kullanıcıya hata başlığı
        st.write(missing)  # Eksik kolonların listesini göster
        st.stop()  # Eksik kolon varsa devam etme

    st.success("Kolon kontrolü başarılı. Dosya formatı uygun.")  # Her şey uygunsa başarı mesajı
    st.subheader("Önizleme (ilk 5 satır)")  # Önizleme başlığı
    st.dataframe(df.head(5))  # İlk 5 satırı tabloda gösterir
    

    if index_button_clicked:
        from services.document_builder import build_product_document  # Doküman üretmek için
        from services.rag import index_documents_to_chroma_with_embeddings, make_product_id  # Embedding'li indexleme kullanır

        documents = []  # Üretilecek doküman metinlerini tutar
        metadatas = []  # Üretilecek metadata listesini tutar
        ids = []  # Üretilecek product_id listesini tutar

        for _, row in df.iterrows():
            row_dict = row.to_dict()  # Satırı dict'e çevirir
            product_id = make_product_id(row_dict)  # Stabil product_id üretir
            doc_text = build_product_document(row_dict)  # Sentetik doküman metnini üretir

            metadata = {
                "product_id": product_id,  # Metadata: ürün id
                "name": str(row_dict.get("Name", "")).strip(),  # Metadata: ürün adı
                "brand": str(row_dict.get("Brand", "")).strip(),  # Metadata: marka
                "label": str(row_dict.get("Label", "")).strip(),  # Metadata: kategori
                "price": float(row_dict.get("Price", 0) or 0),  # Metadata: fiyat
                "rank": float(row_dict.get("Rank", 0) or 0),  # Metadata: puan
            }  # Blueprint'te metadata filter için gerekli alanları genişlettik


            documents.append(doc_text)  # Dokümanı listeye ekler
            metadatas.append(metadata)  # Metadata'yı listeye ekler
            ids.append(product_id)  # Id'yi listeye ekler

        is_ok, msg = index_documents_to_chroma_with_embeddings(
            documents=documents,  # Embedding üretilecek dokümanlar
            metadatas=metadatas,  # Metadata
            ids=ids,  # Id'ler
            persist_dir="db",  # Persist klasörü
            collection_name="cosmetics_kb",  # Collection adı
        )


        if is_ok:
            st.success(msg)  # Başarılı mesajı gösterir
        else:
            st.error(msg)  # Hata mesajı gösterir

    ##################
    if send_clicked:
        message = user_message.strip()  # Kullanıcı mesajını temizler

        if not message:
            st.warning("Lütfen bir soru yaz.")  # Boş mesaj engeli
            st.stop()  # Boşsa devam etme

        from services.rag import semantic_search_in_chroma  # Embedding tabanlı semantic search için

        is_ok, msg, results = semantic_search_in_chroma(query_text=message)  # Semantic arama yapar

        from services.llm import generate_answer  # Gemini ile cevap üretmek için

        context_docs = []  # Bağlam dokümanlarını tutar

        for item in results:
            context_docs.append(item["document"])  # Her sonuçtan doküman metnini ekler

        answer_text = generate_answer(user_question=message, context_docs=context_docs)  # RAG cevabını üretir

        st.subheader("Cevap")  # Cevap başlığı
        st.write(answer_text)  # Cevabı ekrana basar


        if not is_ok:
            st.error(msg)  # Arama hatasını gösterir
            st.stop()  # Hata varsa dur

        st.success(msg)  # Kaç sonuç bulunduğunu gösterir

        if not results:
            st.info("Hiç sonuç bulunamadı. Farklı bir kelime deneyin.")  # Sonuç yoksa bilgi
            st.stop()  # Sonuç yoksa dur

        st.subheader("Bulunan ürünler (metadata)")  # Sonuç başlığı

        for item in results:
            md = item["metadata"]  # Metadata
            dist = item.get("distance", None)  # Semantic aramadaki mesafe

            st.write(
                f"- {md.get('brand', '')} | {md.get('name', '')} | {md.get('label', '')} | Rank={md.get('rank', '')} | Price={md.get('price', '')} | Distance={dist}"
            )  # Distance ekleyerek semantic çalıştığını görünür yapar


    ###################
    st.subheader("Sentetik doküman örneği (ilk ürün)")  # İlk ürün için doküman örneği başlığı

    from services.document_builder import build_product_document  # Döngüsel import riskini azaltmak için burada import ederiz

    first_row = df.iloc[0].to_dict()  # İlk satırı dict'e çevirir
    sample_doc = build_product_document(first_row)  # İlk ürün için sentetik doküman metnini üretir

    st.text_area("Doküman metni", value=sample_doc, height=300)  # Metni ekranda gösterir


if __name__ == "__main__":
    main()  # Uygulamayı başlatır
