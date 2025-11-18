# ClimateActionPolicy-RAG-Application

## Overview

ClimateActionPolicy-RAG-Application is a project designed to support climate action policy recommendations using a Retrieval-Augmented Generation (RAG) system. The application leverages a retrieval component to fetch relevant documents and a generative model to create contextually enriched responses based on the retrieved documents.

## Features

- **Streamlit Interface**: Provides an interactive web interface for querying and displaying responses.
- **Document Retrieval**: Utilizes a retriever to fetch relevant documents based on user queries.
- **Contextual Response Generation**: Generates responses using the Ollama LLaMA 3 model, enriched with context from retrieved documents.
- **Chat History Management**: Supports managing multiple chat sessions and maintaining chat histories.

## Files

- **app.py**: Main Streamlit application file that sets up the web interface and handles user interactions.
- **requirements.txt**: Lists all the Python dependencies required to run the application.

## Folders

- **Chroma**: Directory for the Chroma database used for document retrieval.
- **components**: Contains the retrieval and generation modules.
  - **generator.py**: Handles response generation using the Ollama LLaMA 3 model.
  - **retriever.py**: Manages document retrieval using Chroma and HuggingFace embeddings.


### Running the Application

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/your-username/ClimateActionPolicy-RAG-Application.git
    cd ClimateActionPolicy-RAG-Application
    ```

2. **Create and Activate a Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install the Required Packages**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Start the Streamlit Application**:
    ```bash
    streamlit run app.py
    ```
    Open your web browser and navigate to `http://localhost:8501`.

### Configure Groq API

The app now uses Groq’s OpenAI-compatible endpoint with Llama 3 models. Set these environment variables before running:

- `GROQ_API_KEY` – your Groq API key (required).
- `GROQ_API_BASE_URL` – optional override (defaults to `https://api.groq.com/openai/v1`).
- `MAX_CONTEXT_CHARS` – optional cap on context size to avoid token limits (default: 15000 chars).

How to get a Groq API key:
1. Sign up or log in at [https://console.groq.com](https://console.groq.com).
2. Go to **API Keys** and click **Create API Key**.
3. Copy the key and store it securely (e.g., add to `.env`: `GROQ_API_KEY="gsk_..."`).

In the UI you can choose between `llama-3.3-70b-versatile` (default) and `llama-3.1-8b-instant`. If you hit token-per-minute limits, lower the context size, use the 8B instant model, or set `MAX_CONTEXT_CHARS` to a smaller value.

## Dependencies

The following Python packages are required to run the application:

- streamlit
- langchain
- langchain_community
- chromadb
- transformers
- torch
- pandas
- langchain_chroma
- sentence_transformers

Install the required packages using pip:

```bash
pip install -r requirements.txt
