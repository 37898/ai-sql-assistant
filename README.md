# 🤖 AI SQL Assistant

An AI-powered SQL generator that allows users to query data using natural language.

## 🚀 Features

- 📂 Upload CSV datasets
- 🧠 Convert natural language → SQL using LLM
- 🔗 Automatic JOIN detection
- 🔄 Smart memory (context-aware queries)
- 📊 Auto visualization (charts)
- ⚡ FastAPI backend + Streamlit frontend

## 🛠 Tech Stack

- Python
- FastAPI
- Streamlit
- SQLite
- Ollama (LLM)

## 📸 Demo

Upload data → Ask questions → Get SQL + results + charts

## ▶️ Run Locally

```bash
# Start backend
uvicorn main:app --reload

# Start frontend
streamlit run app.py