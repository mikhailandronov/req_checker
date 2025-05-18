import streamlit as st

st.title("Minimal File Uploader Test")

# Используйте уникальный ключ, если предыдущий мог остаться в состоянии сессии
# Например, если вы запускали основной скрипт и этот в одном сеансе Streamlit
# (хотя обычно перезапуск сервера это решает)
uploaded_file = st.file_uploader(
    "Upload a small MD or TXT file",
    type=["md", "txt"],
    key="minimal_uploader_test_001" # Просто уникальный ключ
)

if uploaded_file is not None:
    try:
        st.success(f"File '{uploaded_file.name}' received by Streamlit on backend!")
        st.write(f"Size: {uploaded_file.size} bytes")
        st.write(f"Type: {uploaded_file.type}")
        
        # Попытаемся прочитать, но сначала убедимся, что файл получен
        content = uploaded_file.getvalue().decode("utf-8")
        st.subheader(f"Content of '{uploaded_file.name}':")
        st.text_area("File Content", content, height=200)
        st.success("File content displayed successfully!")
    except Exception as e:
        st.error(f"Error reading or displaying file: {e}")
        st.exception(e) # Показать полный traceback ошибки в Streamlit UI
else:
    st.info("Please upload a file.")

st.write("--- Test Footer ---") # Чтобы видеть, что скрипт доходит до конца