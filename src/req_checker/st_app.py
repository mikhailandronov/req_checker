import streamlit as st
from dotenv import load_dotenv, find_dotenv
import os
from io import BytesIO
import pypandoc
import json
import time

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.text_splitter import MarkdownHeaderTextSplitter
# Если MarkdownHeaderTextSplitter не найден в langchain.text_splitter, попробуйте:
# from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document # для fallback
from req_checker.main import run_crew_in_streamlit

# Загрузка переменных окружения (для OPENAI_API_KEY)
load_dotenv(find_dotenv())

# Проверка наличия ключа API
if not os.getenv("OPENAI_API_KEY"):
    st.error("Ключ OPENAI_API_KEY не найден. Пожалуйста, установите его в .env файле или переменных окружения.")
    st.stop()

# Структура вопросов ПО УМОЛЧАНИЮ
DEFAULT_QUESTIONS_STRUCTURE = [
    {
        "aspect": "Общие требования к системе",
        "questions": [
            "Что система должна делать? Для чего она разрабатывается?",
            "Каковы сценарии использования системы? Кто в них участвует?",
            "Кто вводит данные в систему? Какие?",
            "Кто получает данные из системы? Какие?"
        ]
    }
]
# Для краткости я сократил списки вопросов в DEFAULT_QUESTIONS_STRUCTURE,
# но вы должны использовать свою полную структуру.

# Константа для ответа "Нет сведений"
NO_INFORMATION_FOUND_TEXT = "Информация отсутствует в предоставленном документе."
NO_INFORMATION_FOUND_MARKDOWN = f"<span style='color:red;'>{NO_INFORMATION_FOUND_TEXT}</span>"

# --- Функции для работы с вопросами ---
def validate_questions_structure(data):
    """Простая валидация структуры загруженных вопросов."""
    if not isinstance(data, list):
        return False
    for item in data:
        if not isinstance(item, dict) or "aspect" not in item or "questions" not in item:
            return False
        if not isinstance(item["aspect"], str) or not isinstance(item["questions"], list):
            return False
        for q_item in item["questions"]:
            if not isinstance(q_item, str): # Или dict, если вопросы сложнее
                 return False
    return True

# Функция для генерации вопросов ---
def generate_questions():
    """
    Генерирует детальную структуру вопросов.
    Возвращает список вопросов в той же структуре, что и DEFAULT_QUESTIONS_STRUCTURE.
    """
    generated_structure = run_crew_in_streamlit()
    # Важно: убедиться, что структура валидна перед возвратом
    if validate_questions_structure(generated_structure):
        return generated_structure
    else:
        st.sidebar.error("Ошибка: Сгенерированная структура вопросов невалидна.")
        return None # Возвращаем None, чтобы обработчик мог это учесть

# --- Основные функции RAG (остаются без изменений) ---
def setup_rag_pipeline_from_bytes(file_bytes: bytes) -> RetrievalQA:
    """
    Настраивает RAG пайплайн на основе байтов Markdown файла.
    """
    try:
        markdown_content = file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        st.error("Ошибка декодирования файла. Убедитесь, что это текстовый файл в кодировке UTF-8.")
        return None

    headers_to_split_on = [
        ("#", "H1"), ("##", "H2"), ("###", "H3"), ("####", "H4"),
    ]
    try:
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on, return_each_line=False) # Убрал strip_headers=False, если не нужно
        docs = markdown_splitter.split_text(markdown_content)
    except Exception as e:
        st.warning(f"Ошибка при использовании MarkdownHeaderTextSplitter: {e}. Попытка базового разделения.")
        docs = []

    if not docs:
        st.info("MarkdownHeaderTextSplitter не нашел подходящих заголовков или документ пуст. Используется CharacterTextSplitter.")
        from langchain_text_splitters import CharacterTextSplitter
        fallback_splitter = CharacterTextSplitter(
            separator="\n\n", chunk_size=1000, chunk_overlap=200,
            length_function=len, is_separator_regex=False,
        )
        chunks = fallback_splitter.split_text(markdown_content)
        if not chunks:
            st.error("Не удалось разделить документ даже с помощью CharacterTextSplitter. Документ может быть пустым.")
            return None
        docs = [Document(page_content=chunk) for chunk in chunks]

    try:
        embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"), model='text-embedding-3-small')
    except Exception as e:
        st.error(f"Ошибка при инициализации OpenAI Embeddings: {e}")
        return None

    try:
        vectorstore = FAISS.from_documents(docs, embeddings)
    except Exception as e:
        st.error(f"Ошибка при создании векторного хранилища FAISS: {e}")
        return None

    try:
        llm = ChatOpenAI(
            temperature=0,
            model_name="gpt-4.1", 
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
    except Exception as e:
        st.error(f"Ошибка при инициализации ChatOpenAI LLM: {e}")
        return None

    prompt_template_string = f"""Используй следующие фрагменты контекста, чтобы ответить на вопрос в конце.
Если ты не знаешь ответа или информация для ответа отсутствует в предоставленном контексте, четко скажи: "{NO_INFORMATION_FOUND_TEXT}".
Не пытайся придумать ответ. Отвечай только на основе предоставленного контекста.

Контекст:
{{context}}

Вопрос: {{question}}
Ответ:"""
    QA_PROMPT = PromptTemplate(
        template=prompt_template_string,
        input_variables=["context", "question"]
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm, chain_type="stuff", retriever=vectorstore.as_retriever(),
        chain_type_kwargs={"prompt": QA_PROMPT}, return_source_documents=False
    )
    return qa_chain


def get_answers_for_structure(qa_chain: RetrievalQA, questions_data: list) -> list:
    """
    Получает ответы на все вопросы из структуры, используя RAG пайплайн.
    """
    results_by_aspect = []
    if not qa_chain: # Если пайплайн не создан, возвращаем пустые результаты
        for aspect_item in questions_data:
            processed_questions = [{"question": q_text, "answer": NO_INFORMATION_FOUND_MARKDOWN} for q_text in aspect_item["questions"]]
            results_by_aspect.append({"aspect": aspect_item["aspect"], "qa_pairs": processed_questions})
        return results_by_aspect

    total_questions_count = sum(len(item["questions"]) for item in questions_data)
    questions_processed_count = 0
    if total_questions_count == 0:
        st.warning("Список вопросов пуст. Нечего обрабатывать.")
        return []

    progress_bar_container = st.empty() # Контейнер для прогресс-бара

    for aspect_item in questions_data:
        aspect_name = aspect_item["aspect"]
        st.write(f"Обработка аспекта: {aspect_name}...") # Для отладки или информации
        processed_questions = []
        for question_text in aspect_item["questions"]:
            questions_processed_count += 1
            progress_fraction = questions_processed_count / total_questions_count
            progress_text = f"Обработка аспекта: {aspect_name} | Вопрос {questions_processed_count}/{total_questions_count}"
            progress_bar_container.progress(progress_fraction, text=progress_text)

            try:
                response = qa_chain.invoke({"query": question_text})
                answer = response["result"].strip()
                if NO_INFORMATION_FOUND_TEXT in answer or not answer:
                    answer_markdown = NO_INFORMATION_FOUND_MARKDOWN
                else:
                    answer_markdown = answer.replace("\n", "<br>")
            except Exception as e:
                st.warning(f"Ошибка при обработке вопроса '{question_text}': {e}")
                answer_markdown = f"<span style='color:orange;'>Ошибка при получении ответа</span>"
            processed_questions.append({"question": question_text, "answer": answer_markdown})
        results_by_aspect.append({"aspect": aspect_name, "qa_pairs": processed_questions})
    progress_bar_container.empty() # Убираем прогресс-бар
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
            question_md = qa_pair['question'].replace('|', '\\|')
            answer_md = qa_pair['answer']
            markdown_output += f"| {question_md} | {answer_md} |\n"
        markdown_output += "\n"
    return markdown_output

# --- Streamlit UI ---
st.set_page_config(layout="wide", page_title="Анализ документа по вопросам")
st.title("Анализ документа с требованиями")

# --- Управление вопросами ---
st.sidebar.header("Управление списком вопросов")

# Инициализация структуры вопросов в session_state, если ее там еще нет
if 'current_questions_structure' not in st.session_state:
    st.session_state.current_questions_structure = DEFAULT_QUESTIONS_STRUCTURE

# Загрузка файла с вопросами
uploaded_questions_file = st.sidebar.file_uploader(
    "Загрузить свой список вопросов (JSON)",
    type=['json']
)

if uploaded_questions_file is not None:
    try:
        questions_data = json.load(uploaded_questions_file)
        if validate_questions_structure(questions_data):
            st.session_state.current_questions_structure = questions_data
            st.sidebar.success(f"Файл вопросов '{uploaded_questions_file.name}' успешно загружен и применен.")
        else:
            st.sidebar.error("Файл JSON имеет неверную структуру. Используется набор вопросов по умолчанию.")
    except json.JSONDecodeError:
        st.sidebar.error("Ошибка декодирования JSON. Убедитесь, что файл корректен. Используется набор вопросов по умолчанию.")
    except Exception as e:
        st.sidebar.error(f"Не удалось прочитать файл вопросов: {e}. Используется набор вопросов по умолчанию.")

# === НАЧАЛО ВСТАВЛЕННОГО КОДА ===
if st.sidebar.button("Сгенерировать вопросы для детального анализа"):
    with st.spinner("Генерация вопросов... Пожалуйста, подождите."):
        try:
            # Вызов функции генерации вопросов
            # ЗАМЕНИТЕ generate_questions() вашей реальной функцией
            new_questions_structure = generate_questions()

            if new_questions_structure: # Если функция вернула структуру
                st.session_state.current_questions_structure = new_questions_structure
                st.sidebar.success("Новый список вопросов успешно сгенерирован и применен!")
            else:
                # Это условие сработает, если generate_questions() вернула None (например, из-за ошибки валидации)
                st.sidebar.warning("Не удалось сгенерировать новый список вопросов. Используется предыдущий набор.")
        except Exception as e:
            st.sidebar.error(f"Произошла ошибка при генерации вопросов: {e}")
# === КОНЕЦ ВСТАВЛЕННОГО КОДА ===

# Кнопка для скачивания текущего шаблона вопросов
current_questions_json = json.dumps(st.session_state.current_questions_structure, indent=4, ensure_ascii=False)
st.sidebar.download_button(
    label="Скачать текущий список вопросов (JSON)",
    data=current_questions_json,
    file_name="questions_template.json",
    mime="application/json"
)

if st.sidebar.button("Сбросить к вопросам по умолчанию"):
    st.session_state.current_questions_structure = DEFAULT_QUESTIONS_STRUCTURE
    st.sidebar.info("Используется набор вопросов по умолчанию.")

# Отображение текущего количества аспектов и вопросов
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Текущая структура вопросов:**")
st.sidebar.markdown(f"- Аспектов: {len(st.session_state.current_questions_structure)}")
total_q = sum(len(aspect.get("questions", [])) for aspect in st.session_state.current_questions_structure)
st.sidebar.markdown(f"- Всего вопросов: {total_q}")


# --- Основная часть приложения ---
st.header("1. Загрузка документа для анализа")
st.write("""
Загрузите документ с требованиями, анализ которого Вы хотите провести.
""")
uploaded_document_file = st.file_uploader("Загрузите ваш документ (.md, .txt, .docx)", type=['md', 'txt', 'docx'])

if uploaded_document_file is not None:
    st.info(f"Документ '{uploaded_document_file.name}' загружен.")

    if not st.session_state.current_questions_structure or total_q == 0: # Проверяем обновленный total_q
        st.warning("Список вопросов пуст. Загрузите или сгенерируйте вопросы на боковой панели.")
    else:
        st.header("2. Анализ документа")
        if st.button("Начать анализ документа"):
            file_bytes_content = uploaded_document_file.getvalue()
            _, file_ext = os.path.splitext(uploaded_document_file.name)
            # st.toast(file_ext.upper()) # Можно убрать или оставить для отладки

            if file_ext.lower() == ".docx": # Используем lower() для надежности
                with st.spinner("Конвертация DOCX в Markdown... Пожалуйста, подождите."):
                    try:
                        markdown_output_str = pypandoc.convert_text(
                            source=file_bytes_content, # Используем исходные байты DOCX
                            to='gfm',
                            format='docx',
                        )
                        file_bytes_content = markdown_output_str.encode('utf-8') # Обновляем file_bytes_content
                        st.info("DOCX успешно сконвертирован в Markdown.")
                    except Exception as e:
                        st.error(f"Ошибка во время конвертации DOCX: {e}")
                        if "pandoc" in str(e).lower():
                            st.warning("Убедитесь, что Pandoc корректно установлен и доступен в системном PATH.")
                        st.stop() # Останавливаем выполнение, если конвертация не удалась
            elif file_ext.lower() not in ['.md', '.txt']:
                st.error(f"Неподдерживаемый формат файла: {file_ext}. Пожалуйста, загрузите .md, .txt или .docx.")
                st.stop()
            # Для .md и .txt file_bytes_content уже содержит нужные байты

            with st.spinner("Индексирую документ..."):
                qa_chain = setup_rag_pipeline_from_bytes(file_bytes_content)

            if qa_chain:
                st.success("Индекс для RAG построен!")

                st.write("Получаю ответы на вопросы...")
                # Используем структуру вопросов из session_state
                answers_data = get_answers_for_structure(qa_chain, st.session_state.current_questions_structure)

                if answers_data:
                    with st.spinner("Форматирую результаты..."):
                        markdown_report = format_results_to_markdown(answers_data)

                    st.success("Анализ завершен!")
                    st.header("3. Результаты анализа")
                    st.markdown(markdown_report, unsafe_allow_html=True)

                    st.download_button(
                        label="Скачать отчет в Markdown",
                        data=markdown_report,
                        file_name=f"report_{os.path.splitext(uploaded_document_file.name)[0]}.md", # Более чистое имя файла
                        mime="text/markdown",
                    )
                else:
                    st.info("Нет данных для отображения. Возможно, список вопросов был пуст или не удалось получить ответы.")
            else:
                st.error("Не удалось создать индекс для RAG. Проверьте ошибки выше.")
else:
    st.info("Пожалуйста, загрузите документ для начала анализа.")

st.sidebar.markdown("---")
st.sidebar.header("О проекте")
st.sidebar.info(
    "Этот инструмент использует LangChain и LLM-модели для извлечения информации "
    "из документов по заданному списку вопросов. \n"
    "Список вопросов для детального анализа генерируется командой агентов на базе фреймворка CrewAI."
)