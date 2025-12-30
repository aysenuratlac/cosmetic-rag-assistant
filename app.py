import os
import streamlit as st
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI  # Indexleme sırasında LLM ile doküman üretmek için

from services.ingestion import load_table_file  # xlsx okuma
from services.document_builder import build_product_document  # doküman oluşturma
from services.rag import make_product_id, index_documents_to_chroma_with_embeddings  # rag işlemleri
from utils.validators import validate_required_columns  # kolon doğrulama
from services.langchain_rag import build_rag_chain  # rag zinciri oluşturma
from langchain_openai import ChatOpenAI

PROVIDER = "openai"  

def save_uploaded_file(uploaded_file) -> str:
    """
    Yüklenen dosyayı diskte saklar ve dosya yolunu döner.
    """
    file_path = os.path.join("data/uploads", uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


def build_recent_history_text(messages: list[dict], max_messages: int = 6) -> str:
    """
    Son max_messages adet mesajı (user + assistant) tek bir metne çevirir.
    Retriever'a bağlam vermek için kullanılır.
    """
    recent = messages[-max_messages:]  # Son N mesajı al
    lines = []

    for m in recent:
        role = m.get("role", "")
        content = str(m.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content}")

    return "\n".join(lines)


def init_chat_state() -> None:
    """
    Chat ile ilgili session_state değişkenlerini başlatır.
    """
    if "messages" not in st.session_state:
        st.session_state["messages"] = []  # mesajlar
    if "pending_question" not in st.session_state:
        st.session_state["pending_question"] = None  # cevabı bekleyen soru
    if "rag_chain" not in st.session_state:
        st.session_state["rag_chain"] = None  # rag zinciri


def render_chat_tab() -> None:
    """
    Chat tabını render eder. Input alanını altta sabitler. Pendingde input devre dışı bırakılır.
    """
    st.subheader("Chat")

    init_chat_state()

    # Input sabit + altta boşluk
    st.markdown(
        """
        <style>
        section.main > div { padding-bottom: 6rem; }

        div[data-testid="stChatInput"]{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #0e1117;
            border-top: 1px solid rgba(255,255,255,0.10);
            padding: 0.75rem 1rem;
            z-index: 999;
        }

        .input-disabled {
            pointer-events: none;
            opacity: 0.85;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 1) Mesajları kronolojik çiz
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 2) Input HER ZAMAN görünsün (pending olsa bile)
    if st.session_state["pending_question"]:
        st.markdown('<div class="input-disabled">', unsafe_allow_html=True)
        user_input = st.chat_input("Bir şey sor...")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        user_input = st.chat_input("Bir şey sor...")

    # 3) Kullanıcı mesaj gönderirse: user mesajını ekle + pending’e al + rerun
    if (not st.session_state["pending_question"]) and user_input and user_input.strip():
        user_input = user_input.strip()
        st.session_state["messages"].append({"role": "user", "content": user_input})
        st.session_state["pending_question"] = user_input
        st.rerun()

    # 4) Pending varsa: LangChain chain ile cevap üret
    if st.session_state["pending_question"]:
        pending_text = st.session_state["pending_question"]

        # Chain’i bir kere kurup session’da tut (her mesajda yeniden kurmayalım)
        if st.session_state["rag_chain"] is None:
            st.session_state["rag_chain"] = build_rag_chain(
                persist_dir=f"db_{PROVIDER}",                 # db_openai / db_gemini
                collection_name=f"cosmetics_kb_{PROVIDER}",  # collection ayır
                k=5,
                provider=PROVIDER,                            # <<< EN KRİTİK SATIR
            )


        chain = st.session_state["rag_chain"]

        with st.chat_message("assistant"):
            with st.spinner("Yazıyor..."):
                try:
                    # Son 6 mesajdan bağlam oluştur (retriever için)
                    recent_history_text = build_recent_history_text(
                        st.session_state["messages"],
                        max_messages=6,
                    )

                    # Retriever'a gidecek nihai soru
                    final_question = (
                       f"{recent_history_text}"
                        # f"Konuşma bağlamı:\n{recent_history_text}\n\n"
                        # f"Son soru:\n{pending_text}"
                    )

                    # Zinciri çağır
                    result = chain.invoke(
                        {
                            "input": final_question  # retriever bunu kullanır
                        }
                    )

                    answer = str(result.get("answer", "")).strip()
                    if not answer:
                        answer = "Cevap üretilemedi (boş döndü)."

                except Exception as exc:
                    answer = f"Hata: {exc}"

            st.markdown(answer)

        st.session_state["messages"].append({"role": "assistant", "content": answer})
        st.session_state["pending_question"] = None
        st.rerun()


def render_admin_tab() -> None:
    st.subheader("Admin")
    st.caption("Yeni XLSX yükleyip ürün KB’yi indexleyebilirsin. (Her indexlemede KB sıfırlanır.)")

    uploaded_file = st.file_uploader("XLSX dosyası yükle", type=["xlsx"])

    if uploaded_file is None:
        st.info("Indexlemek için XLSX yükle.")
        return

    saved_path = save_uploaded_file(uploaded_file)

    is_ok, message, df = load_table_file(saved_path)
    if not is_ok or df is None:
        st.error(message)
        return

    st.success(message)

    valid = validate_required_columns(list(df.columns))
    if not valid:
        st.error("Eksik kolonlar var.")
        return

    st.success("Kolon kontrolü başarılı.")
    st.dataframe(df.head(5))

    if st.button("KB oluştur ve indexle"):
        # Indexleme sırasında LLM ile doküman alanlarını dolduracağız
        if PROVIDER.strip().lower() == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not api_key:
                st.error("OPENAI_API_KEY bulunamadı (.env).")
                return

            llm = ChatOpenAI(
                model="gpt-4o-mini",  # hızlı model
                openai_api_key=api_key,      # API key
                temperature=0.2,             # doküman üretiminde daha stabil
            )
        else:
            api_key = os.getenv("GOOGLE_API_KEY", "").strip()
            if not api_key:
                st.error("GOOGLE_API_KEY bulunamadı (.env).")
                return

            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",  # hızlı model
                google_api_key=api_key,  # API key
                temperature=0.2,  # doküman üretiminde daha stabil
            )

        documents: list[str] = []
        metadatas: list[dict] = []
        ids: list[str] = []

        total = len(df)  # Toplam satır sayısı
        progress = st.progress(0)  # Progress bar (0-100)
        status = st.empty()  # Durum metnini güncellemek için placeholder

        # 0 satır edge-case (çok nadir)
        if total == 0:
            st.warning("Dosyada hiç satır yok.")
            return

        for i, (_, row) in enumerate(df.iterrows(), start=1):
            row_dict = row.to_dict()

            product_id = make_product_id(row_dict)

            # LLM'li doküman üretimi (intro + içerik analizi)
            doc_text = build_product_document(row_dict, llm=llm)

            metadata = {
                "product_id": product_id,
                "name": str(row_dict.get("Name", "")).strip(),
                "brand": str(row_dict.get("Brand", "")).strip(),
                "label": str(row_dict.get("Label", "")).strip(),
                "price": float(row_dict.get("Price", 0) or 0),
                "rank": float(row_dict.get("Rank", 0) or 0),
            }

            documents.append(doc_text)
            metadatas.append(metadata)
            ids.append(product_id)

            # Progress güncelle
            pct = int((i / total) * 100)  # yüzde hesabı
            progress.progress(pct)
            status.write(f"İşleniyor: {i}/{total} (%{pct})")

        status.write("Chroma indexleme başlıyor...")

        ok, msg = index_documents_to_chroma_with_embeddings(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            persist_dir=f"db_{PROVIDER}",                 # db_openai / db_gemini
            collection_name=f"cosmetics_kb_{PROVIDER}",  # collection ayır
            provider=PROVIDER,                            # <<< EN KRİTİK SATIR
        )


        if ok:
            progress.progress(100)
            status.write("Indexleme tamamlandı.")
            st.success(msg)
            # Yeni KB gelince retriever zinciri eski indexi cache’lemesin diye chain’i sıfırla
            st.session_state["rag_chain"] = None
        else:
            status.write("Indexleme hata verdi.")
            st.error(msg)
    


def main() -> None:
    load_dotenv()

    st.set_page_config(page_title="Cosmetic RAG Assistant", layout="wide")
    st.title("Cosmetic RAG Assistant")

    tab_chat, tab_admin = st.tabs(["Chat", "Admin"])

    with tab_chat:
        render_chat_tab()

    with tab_admin:
        render_admin_tab()


if __name__ == "__main__":
    main()
