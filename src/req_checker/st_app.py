import unidecode
import re
import streamlit as st
import datetime
from req_checker.main import run_in_streamlit

# --- Функция для "обработки" и генерации отчета ---
def generate_report(topic: str, year: int) -> str:
    """
    Генерирует отформатированный Markdown-текст на основе темы и года.
    В реальном приложении здесь была бы сложная логика.
    """
    try:
        report_content = run_in_streamlit(topic=topic, current_year=year)
    except Exception as e:
        report_content = "Произошла ошибка:\n{e}"

    return report_content

def sanitize_filename(filename_base: str) -> str:
    # 1. Транслитерация не-ASCII символов в ASCII (например, "в" -> "v")
    #    unidecode отлично справляется с кириллицей и многими другими языками.
    ascii_base = unidecode.unidecode(filename_base)
    
    # 2. Замена пробелов и последовательностей пробелов на одно подчеркивание
    ascii_base = re.sub(r'\s+', '_', ascii_base)
    
    # 3. Удаление всех символов, не являющихся буквами, цифрами, подчеркиванием или точкой
    #    Точку оставляем, так как она может быть частью расширения, хотя мы добавляем .md позже.
    #    Если вы уверены, что в filename_base не будет точек, можно и их убрать.
    safe_base = re.sub(r'[^\w.-]', '', ascii_base) # \w эквивалентно [a-zA-Z0-9_]
    
    # 4. Замена нескольких подчеркиваний подряд на одно
    safe_base = re.sub(r'_+', '_', safe_base)
    
    # 5. Удаление подчеркиваний в начале или конце (если есть)
    safe_base = safe_base.strip('_')
    
    # 6. Преобразование в нижний регистр
    safe_base = safe_base.lower()
    
    # 7. Ограничение длины (опционально, но хорошая практика)
    max_len = 100 # Например
    if len(safe_base) > max_len:
        safe_base = safe_base[:max_len]
        # Можно добавить логику, чтобы не обрезать на середине слова или добавить хеш
        
    return safe_base

# --- Настройка страницы Streamlit ---
st.set_page_config(layout="wide", page_title="Генератор отчетов")

report_title = st.title("📝 Генерация / просмотр отчета")
report_subtitle = st.subheader("")
report_content = st.markdown("")

# Для сгенерированного отчета
if 'report_generated' not in st.session_state:
    st.session_state.report_generated = False
if 'report_text' not in st.session_state:
    st.session_state.report_text = ""
if 'current_topic' not in st.session_state:
    st.session_state.current_topic = "Искусственный интеллект в медицине"
if 'current_year_for_report' not in st.session_state:
    st.session_state.current_year_for_report = datetime.date.today().year

# Для загруженного файла
if 'file_uploaded' not in st.session_state:
    st.session_state.file_uploaded = False
if 'uploaded_file_content' not in st.session_state:
    st.session_state.uploaded_file_content = ""
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = ""


# --- Боковая панель для ввода данных и загрузки файла ---
with st.sidebar:
    st.header("⚙️ Управление")

    # Секция генерации отчета
    with st.expander("Генерация отчета", expanded=True):
        st.subheader("Параметры для генерации")
        
        topic_input = st.text_input(
            "Тема отчета (topic):", 
            value=st.session_state.current_topic,
            help="Введите основную тему для анализа.",
            key="topic_input_key" # Добавлен ключ для лучшего управления состоянием
        )
        
        current_year_input = st.number_input(
            "Год (current_year):", 
            min_value=1900, 
            max_value=datetime.date.today().year + 5, 
            value=st.session_state.current_year_for_report,
            step=1,
            help="Укажите год, для которого готовится отчет.",
            key="year_input_key" # Добавлен ключ
        )

        if st.button("🚀 Сгенерировать отчет", type="primary", use_container_width=True):
            if topic_input: 
                with st.spinner(f"Генерация отчета по теме: '{topic_input}' за {current_year_input} год..."):
                    st.session_state.report_text = generate_report(topic_input, current_year_input)
                    st.session_state.report_generated = True
                    st.session_state.current_topic = topic_input 
                    st.session_state.current_year_for_report = current_year_input
                st.success("Отчет успешно сгенерирован!")
            else:
                st.error("Пожалуйста, введите тему отчета.")
    
    st.markdown("---") 

    # Секция загрузки файла
    with st.expander("Загрузка своего файла", expanded=True):
        st.subheader("Загрузить Markdown файл")
        uploaded_file = st.file_uploader(
            "Выберите Markdown файл (.md или .txt)",
            type=["md", "txt"],
            accept_multiple_files=False,
            key="file_uploader_key" # Добавлен ключ
        )

        if uploaded_file is not None:
            # Этот блок будет выполняться каждый раз, когда файл выбран.
            # Сохраняем контент, только если он отличается от уже сохраненного, или если имя файла изменилось
            # (простой способ избежать лишней обработки, если файл не менялся)
            # Однако, getvalue() читает файл каждый раз. Для больших файлов нужна более сложная логика.
            # Для простоты, сейчас читаем всегда, когда uploaded_file не None.
            try:
                string_content = uploaded_file.getvalue().decode("utf-8")
                # Обновляем состояние только если контент или имя файла изменились,
                # или если это первая загрузка с этим именем.
                if (st.session_state.uploaded_file_name != uploaded_file.name or \
                    st.session_state.uploaded_file_content != string_content):
                    st.session_state.uploaded_file_content = string_content
                    st.session_state.uploaded_file_name = uploaded_file.name
                    st.session_state.file_uploaded = True
                    # Можно добавить st.toast для ненавязчивого уведомления
                    st.toast(f"Файл '{uploaded_file.name}' загружен.", icon="📄")
            except Exception as e:
                st.error(f"Ошибка при чтении файла '{uploaded_file.name}': {e}")
                st.session_state.file_uploaded = False 
                st.session_state.uploaded_file_content = ""
                st.session_state.uploaded_file_name = ""
        # Если пользователь удалил файл из загрузчика (нажал крестик), uploaded_file станет None
        # Мы можем сбросить состояние, если это произошло
        elif st.session_state.file_uploaded and uploaded_file is None:
            # Эта логика сработает, если файл был ранее загружен, а теперь поле очищено
            # (т.е. uploaded_file стал None, но file_uploaded все еще True)
            # Это помогает "очистить" отображение загруженного файла, если пользователь явно его убрал.
            # Для этого file_uploader должен быть "контролируемым" через key.
            # Если в session_state имя файла есть, а uploaded_file уже None, значит его удалили.
             if st.session_state.uploaded_file_name: # Проверяем, было ли что-то загружено ранее
                st.toast(f"Файл '{st.session_state.uploaded_file_name}' удален из загрузки.", icon="🗑️")
                st.session_state.file_uploaded = False
                st.session_state.uploaded_file_content = ""
                st.session_state.uploaded_file_name = ""


# --- Отображение результата в основной области ---
main_content_displayed = False

# 1. Отображение сгенерированного отчета
if st.session_state.report_generated:
    report_subtitle.subheader("📜 Сгенерированный отчет")
    report_content.markdown(st.session_state.report_text)
    
    st.download_button(
        label="📥 Скачать сгенерированный отчет (Markdown)",
        data=st.session_state.report_text,
        file_name=f"report_{sanitize_filename(st.session_state.current_topic)}_{st.session_state.current_year_for_report}.md",
        mime="text/markdown",
    )
    main_content_displayed = True

# 2. Отображение загруженного файла
if st.session_state.file_uploaded and st.session_state.uploaded_file_content:
    report_subtitle.subheader("📄 Содержимое загруженного файла")
    report_content.markdown(st.session_state.uploaded_file_content)
    main_content_displayed = True

# 3. Сообщение, если ничего не отображено
if not main_content_displayed:
    report_subtitle.subheader("📄 Нет данных")
    report_content.markdown("")
    st.info("ℹ️ Пока нет данных для отображения. Сгенерируйте отчет или загрузите файл, используя боковую панель.")