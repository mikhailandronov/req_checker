import streamlit as st
import os

# --- Конфигурация ---
UPLOAD_FOLDER = "uploaded_files"  # Название папки для сохранения файлов
ALLOWED_EXTENSIONS = ["docx"]

# --- Функции ---
def save_uploaded_file(uploaded_file, folder_path):
    """Сохраняет загруженный файл в указанную папку."""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path) # Создаем папку, если её нет

    file_path = os.path.join(folder_path, uploaded_file.name)
    try:
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer()) # getbuffer() для BytesIO-подобных объектов
        return True, f"Файл '{uploaded_file.name}' успешно сохранен в '{folder_path}'"
    except Exception as e:
        return False, f"Ошибка при сохранении файла '{uploaded_file.name}': {e}"

# --- Интерфейс Streamlit ---
st.set_page_config(page_title="Загрузчик DOCX", layout="centered")

st.title("📄 Загрузка DOCX файла на сервер")
st.write(f"Файлы будут сохранены в папку: `{UPLOAD_FOLDER}` на сервере.")

# Виджет для загрузки файла
uploaded_file = st.file_uploader(
    "Выберите DOCX файл",
    type=ALLOWED_EXTENSIONS,
    accept_multiple_files=False  # Разрешить только один файл за раз
)

if uploaded_file is not None:
    st.write("---")
    st.write("Вы выбрали файл:")
    st.write(f"- **Имя файла:** {uploaded_file.name}")
    st.write(f"- **Тип файла:** {uploaded_file.type}")
    st.write(f"- **Размер файла:** {uploaded_file.size / 1024:.2f} KB")

    # Кнопка для подтверждения сохранения
    if st.button(f"💾 Загрузить '{uploaded_file.name}' на сервер"):
        success, message = save_uploaded_file(uploaded_file, UPLOAD_FOLDER)
        if success:
            st.success(message)
        else:
            st.error(message)
else:
    st.info("Пожалуйста, выберите DOCX файл для загрузки.")

st.sidebar.header("О приложении")
st.sidebar.info(
    "Это простое приложение для демонстрации загрузки DOCX файлов "
    "с помощью Streamlit и их сохранения на сервере."
)