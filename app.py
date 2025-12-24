import os
import streamlit as st
from dotenv import load_dotenv

from services.ingestion import load_table_file
from services.document_builder import build_product_document
from services.rag import make_product_id, index_documents_to_chroma_with_embeddings
from services.rag import semantic_search_in_chroma
from services.llm import generate_answer
from utils.validators import validate_required_columns


def ensure_directories() -> None:
    os.makedirs("data/uploads", exist_ok=True)
    os.makedirs("db", exist_ok=True)


def save_uploaded_file(uploaded_file) -> str:
    file_path = os.path.join("data/uploads", uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


def init_chat_state() -> None:
    if "messages" not in st.session_state:
        st.session_state["messages"] = []  # [{"role":"user"/"assistant","content":"..."}]


def render_chat_tab() -> None:
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

        /* Cevap üretilirken input'u görünür bırak ama tıklanmasın (opsiyonel) */
        .input-disabled {
            pointer-events: none;
            opacity: 0.85;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "pending_question" not in st.session_state:
        st.session_state["pending_question"] = None

    # 1) Mesajları çiz (kronolojik)
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 2) Input HER ZAMAN GÖRÜNSÜN (pending olsa bile)
    # Pending varken yeni mesaj almayacağız (istersen alıp kuyruğa da atabiliriz ama MVP için gerek yok)
    if st.session_state["pending_question"]:
        st.markdown('<div class="input-disabled">', unsafe_allow_html=True)
        user_input = st.chat_input("Bir şey sor...")  # görünür kalır
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        user_input = st.chat_input("Bir şey sor...")

    # 3) Kullanıcı mesaj gönderirse: anında state'e yaz, pending'e al, rerun
    if (not st.session_state["pending_question"]) and user_input and user_input.strip():
        user_input = user_input.strip()
        st.session_state["messages"].append({"role": "user", "content": user_input})
        st.session_state["pending_question"] = user_input
        st.rerun()

    # 4) Eğer pending varsa: cevabı üret ve ekle (input zaten ekranda duruyor)
    if st.session_state["pending_question"]:
        pending_text = st.session_state["pending_question"]

        with st.chat_message("assistant"):
            with st.spinner("Yazıyor..."):
                is_ok, _, results = semantic_search_in_chroma(query_text=pending_text)
                context_docs = [r["document"] for r in results] if is_ok else []
                answer = generate_answer(user_question=pending_text, context_docs=context_docs)

            st.markdown(answer)

        st.session_state["messages"].append({"role": "assistant", "content": answer})
        st.session_state["pending_question"] = None
        st.rerun()




def render_admin_tab() -> None:
    st.subheader("Admin")
    st.caption("Yeni XLSX yükleyip ürün KB’yi indexleyebilirsin.")

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

    valid, missing = validate_required_columns(list(df.columns))
    if not valid:
        st.error(f"Eksik kolonlar: {missing}")
        return

    st.success("Kolon kontrolü başarılı.")
    st.dataframe(df.head(5))

    if st.button("KB oluştur ve indexle"):
        documents = []
        metadatas = []
        ids = []

        for _, row in df.iterrows():
            row_dict = row.to_dict()

            product_id = make_product_id(row_dict)
            doc_text = build_product_document(row_dict)

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

        ok, msg = index_documents_to_chroma_with_embeddings(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            persist_dir="db",
            collection_name="cosmetics_kb",
        )

        if ok:
            st.success(msg)
        else:
            st.error(msg)


def main() -> None:
    load_dotenv()
    ensure_directories()

    st.set_page_config(page_title="Cosmetic RAG Assistant", layout="wide")
    st.title("Cosmetic RAG Assistant")

    tab_chat, tab_admin = st.tabs(["Chat", "Admin"])

    with tab_chat:
        render_chat_tab()

    with tab_admin:
        render_admin_tab()


if __name__ == "__main__":
    main()
