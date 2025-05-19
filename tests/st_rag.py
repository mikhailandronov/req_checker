import streamlit as st
import os
from dotenv import load_dotenv, find_dotenv
from io import BytesIO

# Langchain компоненты для RAG
from langchain_community.document_loaders import Docx2txtLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.tools import Tool

# CrewAI компоненты
from crewai import Agent, Task, Crew, Process

# Загрузка переменных окружения (OPENAI_API_KEY)
load_dotenv(find_dotenv())

# --- Глобальные переменные и конфигурация ---
# Инициализируем LLM и Embeddings один раз
# Важно: Для Streamlit лучше инициализировать тяжелые объекты вне функций,
# которые вызываются при каждом взаимодействии, или использовать st.cache_resource
try:
    llm = ChatOpenAI(model="gpt-4.1-nano", temperature=0.1) 
    embeddings_model = OpenAIEmbeddings(model='text-embedding-3-small')
except Exception as e:
    st.error(f"Ошибка инициализации OpenAI: {e}. Убедитесь, что OPENAI_API_KEY установлен.")
    llm = None
    embeddings_model = None

# --- Функции для RAG ---

@st.cache_resource(show_spinner="Обработка документа...")
def create_rag_pipeline(_uploaded_file):
    """
    Создает RAG пайплайн (векторное хранилище и ретривер) из загруженного файла.
    Используем _uploaded_file как аргумент, чтобы кеш знал, когда файл изменился.
    """
    if not _uploaded_file or not llm or not embeddings_model:
        return None

    file_contents = _uploaded_file.getvalue()
    file_name = _uploaded_file.name
    temp_file_path = os.path.join(".", file_name) # Сохраняем временно для загрузчиков

    try:
        with open(temp_file_path, "wb") as f:
            f.write(file_contents)

        if file_name.endswith(".docx"):
            loader = Docx2txtLoader(temp_file_path)
        elif file_name.endswith(".md"):
            loader = UnstructuredMarkdownLoader(temp_file_path)
        else:
            st.error("Неподдерживаемый формат файла.")
            return None
        
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        docs_split = text_splitter.split_documents(documents)

        if not docs_split:
            st.warning("Документ пуст или не удалось извлечь текст.")
            return None

        vector_store = FAISS.from_documents(docs_split, embeddings_model)
        retriever = vector_store.as_retriever(search_kwargs={"k": 3}) # Получать топ-3 релевантных чанка

        # Создаем цепочку RetrievalQA
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff", # "stuff" просто передает все найденные чанки в LLM
            retriever=retriever,
            return_source_documents=False # Можно включить, если нужны исходные чанки
        )
        return qa_chain # Возвращаем цепочку, которая может отвечать на вопросы

    except Exception as e:
        st.error(f"Ошибка при обработке документа: {e}")
        return None
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


# --- CrewAI Инструмент, Агент и Задача ---

def get_document_search_tool(rag_chain):
    """Создает инструмент CrewAI для поиска по документу."""
    if not rag_chain:
        return None
        
    # @tool decorator не нужен, если мы создаем Tool объект вручную
    # Вместо него, мы передадим функцию в конструктор Tool
    def search_document(question: str) -> str:
        """
        Ищет ответ на вопрос в загруженном документе.
        Если ответ не найден, указывает на это.
        """
        try:
            # Используем __call__ или invoke на rag_chain
            response = rag_chain.invoke({"query": question})
            answer = response.get("result", "Не удалось получить результат из RAG цепочки.")

            # Дополнительная проверка, чтобы LLM не "выдумывал"
            if "не могу найти ответ" in answer.lower() or \
               "не найдено информации" in answer.lower() or \
               "документ не содержит" in answer.lower() or \
               "i don't know" in answer.lower() or \
               "i do not know" in answer.lower() or \
               "no information" in answer.lower(): # Добавьте больше фраз, если нужно
                return f"Ответ на вопрос '{question}' не найден в документе."
            return answer
        except Exception as e:
            return f"Ошибка при поиске ответа на вопрос '{question}': {e}"

    return Tool(
        name="DocumentSearchTool",
        func=search_document,
        description="Используется для поиска ответов на конкретные вопросы в загруженном документе. Входные данные - это вопрос в виде строки."
    )

# --- Streamlit UI ---
st.set_page_config(page_title="Анализатор документов с CrewAI", layout="wide")
st.title("Анализатор документов с помощью CrewAI и RAG")

st.sidebar.header("1. Загрузите документ")
uploaded_file = st.sidebar.file_uploader("Выберите DOCX или Markdown файл", type=["docx", "md"])

# Сохраняем RAG цепочку в session_state, чтобы не пересоздавать при каждом реране
if "rag_chain" not in st.session_state:
    st.session_state.rag_chain = None

if uploaded_file:
    # Если загружен новый файл, или RAG цепочка еще не создана для текущего файла
    # Для простоты, мы просто проверяем, есть ли uploaded_file и была ли цепочка создана.
    # В более сложном сценарии, можно кешировать по имени файла или хешу.
    if st.session_state.rag_chain is None or st.session_state.get("current_file_name") != uploaded_file.name:
        with st.spinner("Индексация документа... Это может занять некоторое время."):
            st.session_state.rag_chain = create_rag_pipeline(uploaded_file)
            if st.session_state.rag_chain:
                st.session_state.current_file_name = uploaded_file.name # Сохраняем имя файла
                st.sidebar.success(f"Документ '{uploaded_file.name}' успешно обработан!")
            else:
                st.sidebar.error("Не удалось обработать документ.")
                # Сбрасываем, если обработка не удалась
                st.session_state.rag_chain = None 
                st.session_state.current_file_name = None

else: # Если файл не загружен (или удален из загрузчика)
    st.session_state.rag_chain = None
    st.session_state.current_file_name = None


st.sidebar.header("2. Ваши вопросы")
st.sidebar.info("Введите вопросы по одному в поле ниже или используйте примеры.")

# Пример вопросов (можно сделать редактируемым списком)
default_questions_dicts = [
    {"id": 1, "question": "Какова цель проекта?"},
    {"id": 2, "question": "Кем является Белинская Е.А?"},
]

# Используем st.session_state для хранения вопросов, чтобы они не сбрасывались
if "questions_to_ask" not in st.session_state:
    st.session_state.questions_to_ask = [q["question"] for q in default_questions_dicts]

# Отображение и редактирование списка вопросов
st.sidebar.subheader("Список вопросов:")
for i, q_text in enumerate(st.session_state.questions_to_ask):
    new_q = st.sidebar.text_input(f"Вопрос {i+1}", value=q_text, key=f"q_input_{i}")
    st.session_state.questions_to_ask[i] = new_q

new_question_text = st.sidebar.text_input("Добавить новый вопрос:", key="new_q_text_input")
if st.sidebar.button("Добавить вопрос", key="add_q_button") and new_question_text:
    st.session_state.questions_to_ask.append(new_question_text)
    # Очищаем поле ввода после добавления, чтобы избежать дублирования при реране
    # Это требует немного JS или более сложного управления состоянием,
    # поэтому пока оставим как есть или пользователь должен сам очищать.
    # Для простоты примера, пока не очищаем.
    st.experimental_rerun() # Перезапустить, чтобы обновить список


if st.session_state.rag_chain and llm:
    document_search_tool = get_document_search_tool(st.session_state.rag_chain)

    if document_search_tool:
        document_analyst = Agent(
            role='Аналитик Документов',
            goal='Точно отвечать на вопросы, основываясь исключительно на содержании предоставленного документа. Если ответ не найден, четко указать это.',
            backstory=(
                "Вы - высококвалифицированный ИИ-ассистент, специализирующийся на анализе текстовых документов. "
                "Ваша задача - извлекать точную информацию и отвечать на вопросы пользователей, "
                "строго придерживаясь контекста документа. Вы не должны додумывать или использовать внешние знания. "
                "Если информации для ответа в документе нет, вы прямо об этом сообщаете."
            ),
            tools=[document_search_tool],
            llm=llm,
            verbose=True, # Показывает мыслительный процесс агента
            allow_delegation=False
        )

        if st.button("Найти ответы на вопросы", type="primary"):
            if not st.session_state.questions_to_ask:
                st.warning("Пожалуйста, добавьте хотя бы один вопрос.")
            else:
                st.subheader("Результаты анализа:")
                results_placeholder = st.empty() # Для обновления результатов по мере их поступления
                
                all_results = []
                for i, question_text in enumerate(st.session_state.questions_to_ask):
                    if not question_text.strip(): # Пропускаем пустые вопросы
                        continue

                    task = Task(
                        description=f"Проанализируй документ и найди ответ на следующий вопрос: '{question_text}'. "
                                    "Основывай свой ответ исключительно на информации из документа. "
                                    "Если ответ не может быть найден в документе, явно укажи: 'Ответ на вопрос не найден в документе'.",
                        agent=document_analyst,
                        expected_output="Текстовый ответ на вопрос или указание, что ответ не найден."
                    )

                    # Создаем и запускаем Crew для каждой задачи отдельно
                    # Это проще для отображения прогресса, но можно и все задачи в один Crew
                    crew = Crew(
                        agents=[document_analyst],
                        tasks=[task],
                        process=Process.sequential,
                        verbose=1 # 0, 1 или 2 для разной степени детализации логов
                    )
                    
                    with st.spinner(f"Агент обрабатывает вопрос {i+1}: '{question_text}'..."):
                        try:
                            answer = crew.kickoff()
                            all_results.append({"question": question_text, "answer": answer.raw})
                            
                            # Обновляем плейсхолдер с текущими результатами
                            current_results_html = "<ul>"
                            for res in all_results:
                                current_results_html += f"<li><b>Вопрос:</b> {st.markdown.escape(res['question'])}<br>"
                                current_results_html += f"  <b>Ответ:</b> {st.markdown.escape(res['answer'])}</li><hr>"
                            current_results_html += "</ul>"
                            results_placeholder.markdown(current_results_html, unsafe_allow_html=True)

                        except Exception as e:
                            st.error(f"Ошибка при выполнении задачи для вопроса '{question_text}': {e}")
                            all_results.append({"question": question_text, "answer": f"Ошибка: {e}"})
                
                st.success("Все вопросы обработаны!")
    else:
        st.warning("Инструмент поиска по документу не был инициализирован. Возможно, документ не был обработан.")
elif not uploaded_file:
    st.info("Пожалуйста, загрузите документ DOCX или Markdown для начала анализа.")
elif not llm or not embeddings_model:
    st.error("LLM или модель эмбеддингов не инициализированы. Проверьте API ключ.")