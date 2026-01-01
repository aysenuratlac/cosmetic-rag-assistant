# services/langchain_rag.py
import os  # Ortam değişkeninden API key okumak için
from langchain_community.vectorstores import Chroma  # Chroma vector store
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings  # Gemini LLM + embedding
from langchain.chains import create_retrieval_chain  # Retriever + QA chain birleştirmek için
from langchain.chains.combine_documents import create_stuff_documents_chain  # Dokümanları "stuff" edip LLM'e vermek için
from langchain_core.prompts import ChatPromptTemplate  # System/human prompt şablonu oluşturmak için
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


def build_rag_chain(
    persist_dir: str = "db",
    collection_name: str = "cosmetics_kb",
    k: int = 5,
    provider: str = "gemini",  # "gemini" veya "openai"
):
    # Provider’a göre API key seç
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()  # OpenAI key (.env)
        if not api_key:
            raise ValueError("OPENAI_API_KEY bulunamadı (.env).")  # Key yoksa hata
    else:
        api_key = os.getenv("GOOGLE_API_KEY", "").strip()  # Gemini key (.env)
        if not api_key:
            raise ValueError("GOOGLE_API_KEY bulunamadı (.env).")  # Key yoksa hata

    # 1) Embeddings seçimi
    if provider == "openai":
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",  # Ucuz/hızlı embedding
            openai_api_key=api_key,          # OpenAI API key
        )
    else:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",  # Gemini embedding
            google_api_key=api_key,             # Gemini API key
        )

    # 2) Persist edilmiş Chroma DB’yi aç
    vectorstore = Chroma(
        persist_directory=persist_dir,      # db klasörü
        collection_name=collection_name,    # collection
        embedding_function=embeddings,      # embedding fonksiyonu
    )

    # 3) Retriever
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})  # En yakın k doküman

    # 4) LLM seçimi
    if provider == "openai":
        llm = ChatOpenAI(
            model="gpt-4o-mini",        # Ucuz/hızlı chat modeli
            temperature=0.3,            # Stabil cevaplar için düşük sıcaklık
            openai_api_key=api_key,     # OpenAI API key
        )
    else:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",   # Mevcut model
            google_api_key=api_key,     # Gemini API key
            temperature=0.3,
        )

    # 5) Prompt
    system_prompt = (
        "Sen kozmetik ürün verileriyle çalışan bir soru-cevap asistanısın.\n"
        "Yalnızca veri tabanındaki ürünlerle ilgili bilgi vermekten sorumlusun.\n"
        "Bilgi harici, selamlama vb konularda cevap verebilirsin.\n"
        "Cevabını sadece aşağıdaki bağlama (context) dayanarak üret.\n"
        "Bağlamda yoksa 'Bunu mevcut bilgi tabanında bulamadım.' de.\n"
        "Tıbbi teşhis veya kesin hüküm verme. Emin değilsen 'belirlenemedi' de.\n"
        "Cevabı kısa ve net tut.\n\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),     # Kurallar + context
            ("human", "Soru: {input}"),    # input zaten history+son soru şeklinde “şişik” gelebilir
        ]
    )

    question_answer_chain = create_stuff_documents_chain(
        llm=llm,        # Seçilen LLM
        prompt=prompt,  # Prompt
    )

    rag_chain = create_retrieval_chain(
        retriever=retriever,
        combine_docs_chain=question_answer_chain,
    )

    return rag_chain
