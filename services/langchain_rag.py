# services/langchain_rag.py
import os  # Ortam değişkeninden API key okumak için
from langchain_community.vectorstores import Chroma  # Chroma vector store
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings  # Gemini LLM + embedding
from langchain.chains import create_retrieval_chain  # Retriever + QA chain birleştirmek için
from langchain.chains.combine_documents import create_stuff_documents_chain  # Dokümanları "stuff" edip LLM'e vermek için
from langchain_core.prompts import ChatPromptTemplate  # System/human prompt şablonu oluşturmak için


def build_rag_chain(
    persist_dir: str = "db",
    collection_name: str = "cosmetics_kb",
    k: int = 5,
):
    """
    RAG zincirini (retriever + prompt + LLM) kurar.

    - ChatPromptTemplate (system prompt + {context})
    - create_stuff_documents_chain
    - create_retrieval_chain
    """
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()  # .env içinden GOOGLE_API_KEY okur
    if not api_key:
        raise ValueError("GOOGLE_API_KEY bulunamadı (.env).")  # Key yoksa hata

    # 1) Embedding fonksiyonu (Chroma'nın arkasında vektör üretmek için)
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",  # Embedding modeli
        google_api_key=api_key,  # Gemini API key
    )

    # 2) Persist edilmiş Chroma DB’yi aç
    vectorstore = Chroma(
        persist_directory=persist_dir,  # db klasörü
        collection_name=collection_name,  # cosmetics_kb collection
        embedding_function=embeddings,  # embedding fonksiyonu
    )

    # 3) Retriever (benzerlik araması)
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})  # En yakın k dokümanı getir

    # 4) LLM (cevap üretimi)
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",  # model
        google_api_key=api_key,  # Gemini API key
        temperature=0.3,  # Daha stabil cevaplar için düşük sıcaklık
    )

    # 5) System prompt: RAG cevap kuralları + {context}
    system_prompt = (
        "Sen kozmetik ürün verileriyle çalışan bir soru-cevap asistanısın.\n"
        "Yalnızca veri tabanındaki ürünlerle ilgili bilgi vermekten sorumlusun.\n"
        "Cevabını sadece aşağıdaki bağlama (context) dayanarak üret.\n"
        "Bağlamda yoksa 'Bunu mevcut bilgi tabanında bulamadım.' de.\n"
        "Tıbbi teşhis veya kesin hüküm verme. Emin değilsen 'belirlenemedi' de.\n"
        "Cevabı kısa ve net tut.\n\n"
        "{context}"
    )  # RAG'e gelen dokümanlar {context} olarak buraya gömülür

    # 6) Prompt template: system + human
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),  # Sistem mesajı: kurallar + context
            # Not: chat history'yi burada basitçe input'a ekliyoruz 
            ("human", "Soru: {input}"),  # Kullanıcı sorusu
        ]
    )

    # 7) Dokümanları LLM'e "stuff" yöntemiyle veren zincir
    question_answer_chain = create_stuff_documents_chain(
        llm=llm,  # Cevabı üretecek LLM
        prompt=prompt,  # Az önce oluşturduğumuz prompt
    )

    # 8) Retriever + QA chain birleşimi = RAG
    rag_chain = create_retrieval_chain(
        retriever=retriever,  # Dokümanları getiren parça
        combine_docs_chain=question_answer_chain,  # Dokümanları kullanarak cevap üreten parça
    )

    return rag_chain  # app.py bunu invoke ederek kullanacak
