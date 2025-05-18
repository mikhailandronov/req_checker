import streamlit as st
import pypandoc
import os # Для работы с именами файлов

# Попытка проверить наличие Pandoc при запуске (опционально, но полезно для пользователя)
try:
    pandoc_version = pypandoc.get_pandoc_version()
    st.sidebar.success(f"Pandoc v{pandoc_version} найден.")
    PANDOC_AVAILABLE = True
except OSError:
    st.sidebar.error("Pandoc не найден! Установите Pandoc и убедитесь, что он доступен в PATH.")
    st.sidebar.markdown("Инструкции по установке: [pandoc.org/installing.html](https://pandoc.org/installing.html)")
    PANDOC_AVAILABLE = False
    # Можно остановить приложение, если Pandoc критичен
    # st.stop()

st.title("📄 DOCX в Markdown Конвертер")

uploaded_file = st.file_uploader(
    "Загрузите DOCX файл для конвертации в Markdown",
    type=["docx"], # Ограничиваемся только docx
    key="docx_uploader"
)

if uploaded_file is not None and PANDOC_AVAILABLE:
    st.write(f"Вы загрузили: `{uploaded_file.name}` (Тип: {uploaded_file.type})")

    # Кнопка для запуска конвертации
    if st.button("Конвертировать в Markdown"):
        with st.spinner("Конвертация... Пожалуйста, подождите."):
            try:
                # Получаем байты из загруженного файла
                docx_bytes = uploaded_file.getvalue() # или uploaded_file.read()

                # Конвертируем байты DOCX в строку Markdown
                # 'markdown_strict' - хороший базовый вариант
                # 'gfm' (GitHub Flavored Markdown) - популярный вариант с расширениями
                # 'commonmark' - другой стандарт
                # Можно добавить опции, например, для таблиц: 'markdown_strict+pipe_tables'
                # Указываем 'docx' как исходный формат
                markdown_output = pypandoc.convert_text(
                    source=docx_bytes,
                    to='gfm',  # Выбираем GitHub Flavored Markdown, он довольно популярен
                    format='docx',
                    # extra_args=['--wrap=none'] # Пример дополнительного аргумента Pandoc
                )

                st.subheader("Результат в Markdown:")
                st.markdown(markdown_output, unsafe_allow_html=True) # Показать отрендеренный Markdown

                st.subheader("Текст Markdown (для копирования):")
                st.text_area("Markdown", markdown_output, height=300)

                # Кнопка для скачивания .md файла
                # Формируем имя файла для скачивания
                base_name, _ = os.path.splitext(uploaded_file.name)
                md_file_name = f"{base_name}.md"

                st.download_button(
                    label="📥 Скачать .md файл",
                    data=markdown_output,
                    file_name=md_file_name,
                    mime="text/markdown"
                )

            except Exception as e:
                st.error(f"Ошибка во время конвертации: {e}")
                st.error("Убедитесь, что загруженный файл является корректным DOCX файлом.")
                if "pandoc document" in str(e).lower() or "pandoc exception" in str(e).lower():
                     st.warning("Проверьте, что Pandoc корректно установлен и доступен.")


elif uploaded_file is None and PANDOC_AVAILABLE:
    st.info("Пожалуйста, загрузите файл DOCX.")
elif not PANDOC_AVAILABLE:
    st.warning("Конвертация невозможна, так как Pandoc не найден в системе.")