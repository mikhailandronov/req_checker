import streamlit as st
from dotenv import load_dotenv, find_dotenv
import os
import io

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Загрузка переменных окружения (для OPENAI_API_KEY)
load_dotenv(find_dotenv())

# Проверка наличия ключа API
if not os.getenv("OPENAI_API_KEY"):
    st.error("Ключ OPENAI_API_KEY не найден. Пожалуйста, установите его в .env файле или переменных окружения.")
    st.stop()

# Структура вопросов (предоставленная вами)
QUESTIONS_STRUCTURE = [
    {
        "aspect": "Общие требования к системе",
        "questions": [
            "Что такое CVD?",
            "Как алмазы используются в медицине?"
        ]
    },
    {
        "aspect": "Технические требования",
        "questions": [
            "Какие платформы и операционные системы должны поддерживаться системой (например, Windows, Linux, macOS, мобильные платформы)?",
            "Какая предполагается архитектура системы: монолитная, микросервисная, сервис-ориентированная или облачная, или их комбинации?",
            "Зачем инвестировать в развитие лазерных и радиационных методов модификации алмазов?"
        ]
    },
    {
        "aspect": "Требования к безопасности",
        "questions": [
            "Какие международные и национальные стандарты и нормативы по информационной безопасности должны быть соблюдены при разработке системы (например, ISO/IEC 27001, ГОСТ Р, IEC 62443, GDPR, Федеральный закон №152-ФЗ)?",
            "Какие организационные меры безопасности должны быть реализованы (политики безопасности, резервное копирование, управление инцидентами и т.д.)?",
            "Какие механизмы аутентификации и авторизации должны быть внедрены (например, многофакторная аутентификация, роль-based access control, Attribute-Based Access Control)?"
        ]
    }
]

# Константа для ответа "Нет сведений"
NO_INFORMATION_FOUND_TEXT = "Информация отсутствует в предоставленном документе."
NO_INFORMATION_FOUND_MARKDOWN = f"<span style='color:red;'>{NO_INFORMATION_FOUND_TEXT}</span>"


def setup_rag_pipeline_from_bytes(file_bytes: bytes) -> RetrievalQA:
    """
    Настраивает RAG пайплайн на основе байтов Markdown файла.
    """
    try:
        # 1. Декодирование байтов в строку
        markdown_content = file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        st.error("Ошибка декодирования файла. Убедитесь, что это текстовый файл в кодировке UTF-8.")
        return None

    # 2. Разделение документа на чанки
    # MarkdownHeaderTextSplitter хорошо подходит для документов с четкой структурой заголовков
    headers_to_split_on = [
        ("#", "H1"),
        ("##", "H2"),
        ("###", "H3"),
        ("####", "H4"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    docs = markdown_splitter.split_text(markdown_content)

    if not docs:
        st.warning("Документ не содержит текста или не удалось его разделить на части. Убедитесь, что Markdown размечен корректно.")
        # Можно создать один большой документ, если разделение не удалось, но это менее эффективно
        from langchain_text_splitters import CharacterTextSplitter
        from langchain_core.documents import Document
        # fallback_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        # docs = fallback_splitter.split_documents([Document(page_content=markdown_content)])
        # if not docs:
        st.error("Не удалось обработать документ.")
        return None


    # 3. Создание эмбеддингов
    # Используем OpenAIEmbeddings, но можно заменить на HuggingFaceEmbeddings для локальных моделей
    try:
        embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"), model='text-embedding-3-small')
    except Exception as e:
        st.error(f"Ошибка при инициализации OpenAI Embeddings: {e}")
        return None

    # 4. Создание векторного хранилища в памяти (FAISS)
    try:
        vectorstore = FAISS.from_documents(docs, embeddings)
    except Exception as e:
        st.error(f"Ошибка при создании векторного хранилища FAISS: {e}")
        return None

    # 5. Создание языковой модели (LLM)
    try:
        llm = ChatOpenAI(
            temperature=0,  
            model_name="gpt-4.1-nano", 
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
    except Exception as e:
        st.error(f"Ошибка при инициализации ChatOpenAI LLM: {e}")
        return None

    # 6. Определение промпта для RAG
    # Важно указать LLM, как поступать, если информация не найдена.
    prompt_template_string = f"""Используй следующие фрагменты контекста, чтобы ответить на вопрос в конце.
Если ты не знаешь ответа или информация для ответа отсутствует в предоставленном контексте, четко скажи: "{NO_INFORMATION_FOUND_TEXT}".
Не пытайся придумать ответ. Отвечай только на основе предоставленного контекста.

Контекст:
{{context}}

Вопрос: {{question}}
Ответ:"""

    QA_PROMPT = PromptTemplate(
        template=prompt_template_string, # Передаем строку, где NO_INFORMATION_FOUND_TEXT уже вставлено, а {context} и {question} - плейсхолдеры
        input_variables=["context", "question"]
    )

    # 7. Создание цепочки RetrievalQA
    # chain_type="stuff" просто передает все найденные чанки в промпт.
    # Для больших документов могут понадобиться другие типы (map_reduce, refine).
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(),
        chain_type_kwargs={"prompt": QA_PROMPT},
        return_source_documents=False # Можно установить True для отладки, чтобы видеть извлеченные чанки
    )
    return qa_chain


def get_answers_for_structure(qa_chain: RetrievalQA, questions_data: list) -> list:
    """
    Получает ответы на все вопросы из структуры, используя RAG пайплайн.
    """
    results_by_aspect = []
    if not qa_chain:
        # Возвращаем пустые результаты, если пайплайн не был создан
        for aspect_item in questions_data:
            aspect_name = aspect_item["aspect"]
            processed_questions = []
            for question_text in aspect_item["questions"]:
                processed_questions.append({
                    "question": question_text,
                    "answer": NO_INFORMATION_FOUND_MARKDOWN
                })
            results_by_aspect.append({
                "aspect": aspect_name,
                "qa_pairs": processed_questions
            })
        return results_by_aspect

    for aspect_item in questions_data:
        aspect_name = aspect_item["aspect"]
        st.write(f"Обработка аспекта: {aspect_name}...")
        processed_questions = []
        for i, question_text in enumerate(aspect_item["questions"]):
            st.progress((i + 1) / len(aspect_item["questions"]), text=f"Вопрос {i+1}/{len(aspect_item['questions'])}")
            try:
                response = qa_chain.invoke({"query": question_text})
                answer = response["result"].strip()
                if NO_INFORMATION_FOUND_TEXT in answer or not answer:
                    answer_markdown = NO_INFORMATION_FOUND_MARKDOWN
                else:
                    answer_markdown = answer.replace("\n", "<br>") # Для корректного отображения переносов строк в Markdown таблице
            except Exception as e:
                st.warning(f"Ошибка при обработке вопроса '{question_text}': {e}")
                answer_markdown = f"<span style='color:orange;'>Ошибка при получении ответа</span>"

            processed_questions.append({
                "question": question_text,
                "answer": answer_markdown
            })
        results_by_aspect.append({
            "aspect": aspect_name,
            "qa_pairs": processed_questions
        })
        st.success(f"Аспект '{aspect_name}' обработан.")
    return results_by_aspect


def format_results_to_markdown(results_data: list) -> str:
    """
    Форматирует результаты в виде Markdown текста с таблицами.
    """
    markdown_output = ""
    for aspect_result in results_data:
        markdown_output += f"## {aspect_result['aspect']}\n\n"
        markdown_output += "| Вопрос | Ответ |\n"
        markdown_output += "|---|---|\n"
        for qa_pair in aspect_result['qa_pairs']:
            # Экранирование символа пайплайна в вопросе, если он там есть
            question_md = qa_pair['question'].replace('|', '\\|')
            answer_md = qa_pair['answer'] # HTML для цвета уже включен
            markdown_output += f"| {question_md} | {answer_md} |\n"
        markdown_output += "\n"
    return markdown_output

# --- Streamlit UI ---
st.set_page_config(layout="wide", page_title="Анализ документа по вопросам")
st.title("Анализ Markdown документа на основе списка вопросов")
st.write("""
Загрузите Markdown файл и система попытается найти ответы на предопределенный список вопросов,
используя RAG (Retrieval Augmented Generation) с OpenAI.
""")

uploaded_file = st.file_uploader("Загрузите ваш Markdown файл (.md)", type=['md', 'txt'])

if uploaded_file is not None:
    st.info(f"Файл '{uploaded_file.name}' загружен. Начинаю обработку...")

    # Получаем байты из загруженного файла
    file_bytes = uploaded_file.getvalue()

    # 1. Создаем RAG пайплайн
    with st.spinner("Индексирую документ и настраиваю RAG пайплайн... Это может занять некоторое время."):
        qa_chain = setup_rag_pipeline_from_bytes(file_bytes)

    if qa_chain:
        st.success("RAG пайплайн успешно создан!")

        # 2. Получаем ответы на вопросы
        with st.spinner("Получаю ответы на вопросы... Это может занять несколько минут в зависимости от количества вопросов."):
            answers_data = get_answers_for_structure(qa_chain, QUESTIONS_STRUCTURE)

        # 3. Форматируем результаты в Markdown
        with st.spinner("Форматирую результаты..."):
            markdown_report = format_results_to_markdown(answers_data)

        st.success("Анализ завершен!")
        st.subheader("Результаты анализа:")
        st.markdown(markdown_report, unsafe_allow_html=True)

        # Кнопка для скачивания отчета
        st.download_button(
            label="Скачать отчет в Markdown",
            data=markdown_report,
            file_name=f"report_{uploaded_file.name}.md",
            mime="text/markdown",
        )
    else:
        st.error("Не удалось создать RAG пайплайн. Проверьте ошибки выше.")

else:
    st.info("Пожалуйста, загрузите Markdown файл для начала анализа.")

st.sidebar.header("О проекте")
st.sidebar.info(
    "Этот инструмент использует LangChain и OpenAI для извлечения информации из "
    "Markdown документов по заданному списку вопросов. "
    "Он демонстрирует простой RAG-пайплайн с индексацией в памяти."
)