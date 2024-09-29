import streamlit as st
from openai import OpenAI
import fitz  # PyMuPDF para manipulación de PDF
import os
import nltk
from nltk.tokenize import sent_tokenize
import sqlite3

# Título de la app en Streamlit
st.title("💬 Chatbot con Extracción de PDF")
st.write(
    "Este chatbot utiliza el modelo GPT-4 de OpenAI y permite extraer conocimiento legal de archivos PDF para responder tus preguntas."
)

# Pedir la API key de OpenAI
openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Por favor, agrega tu OpenAI API key para continuar.", icon="🗝️")
else:
    # Inicializar cliente OpenAI
    client = OpenAI(api_key=openai_api_key)

    # Definir ruta para los archivos PDF
    pdf_paths = [
        "https://github.com/ddiazeTHESIS/chatbot/blob/main/1.pdf",
        "https://github.com/ddiazeTHESIS/chatbot/blob/main/2.pdf",
        "https://github.com/ddiazeTHESIS/chatbot/blob/main/3.pdf",
        "https://github.com/ddiazeTHESIS/chatbot/blob/main/4.pdf"
    ]

    # Variable para almacenar todo el texto extraído
    pdf_content = ""

    # Función para extraer texto de los PDFs
    def extract_text_from_pdf(pdf_path):
        text = ""
        with fitz.open(pdf_path) as pdf:
            for page_num in range(len(pdf)):
                page = pdf.load_page(page_num)
                text += page.get_text()
        return text

    # Iterar sobre cada archivo PDF en la lista y extraer el texto
    for pdf_path in pdf_paths:
        if os.path.exists(pdf_path):
            st.write(f"Extrayendo texto de: {pdf_path}")
            pdf_content += extract_text_from_pdf(pdf_path) + "\n"
        else:
            st.error(f"El archivo {pdf_path} no se encuentra en la ruta especificada.")
    
    # Tokenizar el contenido del PDF
    nltk.download('punkt')
    sentences = sent_tokenize(pdf_content)

    # Mostrar las primeras oraciones extraídas
    st.write("Primeras oraciones extraídas de los PDFs:")
    for sentence in sentences[:5]:
        st.write(sentence)

    # Guardar el contenido en una base de datos SQLite
    conn = sqlite3.connect('base_de_conocimiento.db')
    cursor = conn.cursor()

    # Crear una tabla si no existe
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conocimiento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        oracion TEXT NOT NULL
    )
    ''')

    # Insertar las oraciones en la base de datos
    for sentence in sentences:
        cursor.execute("INSERT INTO conocimiento (oracion) VALUES (?)", (sentence,))

    # Confirmar los cambios y cerrar la conexión
    conn.commit()
    conn.close()

    st.write("Base de datos creada con el contenido extraído de los PDFs.")

    # Función para buscar en la base de conocimiento
    def search_legal_knowledge(keyword):
        conn = sqlite3.connect('base_de_conocimiento.db')
        cursor = conn.cursor()
        cursor.execute("SELECT oracion FROM conocimiento WHERE oracion LIKE ?", ('%' + keyword + '%',))
        results = cursor.fetchall()
        conn.close()
        if not results:
            return "No se encontró información relevante en la base de conocimiento."
        return "\n".join([row[0] for row in results])

    # Crear un campo de input para que el usuario ingrese su consulta
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Crear el campo de entrada para que el usuario ingrese la consulta
    if prompt := st.chat_input("¿Qué pregunta legal tienes?"):

        # Guardar y mostrar la consulta del usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Buscar conocimiento relevante en la base de datos
        relevant_knowledge = search_legal_knowledge(prompt)
        
        # Crear el contexto para la llamada a GPT-4
        context = f"Contexto legal: {relevant_knowledge}\n\nPregunta del usuario: {prompt}"

        # Generar respuesta con GPT-4
        stream = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Eres un asistente experto en leyes."},
                {"role": "user", "content": context}
            ],
            stream=True,
        )

        # Mostrar la respuesta del asistente
        with st.chat_message("assistant"):
            response = st.write_stream(stream)

        # Guardar la respuesta en el estado de la sesión
        st.session_state.messages.append({"role": "assistant", "content": response})
