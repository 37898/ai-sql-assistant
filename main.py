from fastapi import FastAPI, UploadFile, File, Body
from pydantic import BaseModel
from typing import List
import requests
import re
import sqlite3
import pandas as pd
import os

app = FastAPI()

# =========================================================
# 🧹 RESET DATABASE ON SERVER START (FOR FRESH RUNS)
# =========================================================
if os.path.exists("sales.db"):
    os.remove("sales.db")


# =========================================================
# 🔹 STEP 1: FETCH DATABASE SCHEMA (LLM CONTEXT)
# =========================================================
def get_schema():
    conn = sqlite3.connect("sales.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    schema = ""

    for table in tables:
        table_name = table[0]

        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()

        schema += f"\nTable: {table_name}\n"
        for col in columns:
            schema += f"{col[1]} ({col[2]}), "

    conn.close()
    return schema


# =========================================================
# 🔹 STEP 2: GET TABLE NAMES
# =========================================================
def get_table_names():
    conn = sqlite3.connect("sales.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    conn.close()
    return tables


# =========================================================
# 🔹 STEP 3: DETECT RELATIONSHIPS (AUTO JOIN)
# =========================================================
def detect_relationships():
    conn = sqlite3.connect("sales.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    table_columns = {}

    for table in tables:
        cursor.execute(f"PRAGMA table_info({table});")
        cols = [col[1] for col in cursor.fetchall()]
        table_columns[table] = cols

    relationships = []

    for i in range(len(tables)):
        for j in range(i + 1, len(tables)):
            t1, t2 = tables[i], tables[j]

            common_cols = set(table_columns[t1]) & set(table_columns[t2])

            for col in common_cols:
                relationships.append(f"{t1}.{col} = {t2}.{col}")

    conn.close()
    return relationships


# =========================================================
# 🔹 STEP 4: EXTRACT SQL FROM LLM OUTPUT
# =========================================================
def extract_sql(text):
    if not text:
        return ""

    match = re.search(r"(SELECT .*?;)", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return ""


# =========================================================
# 🔹 STEP 5: FIX TABLE NAMES DYNAMICALLY
# =========================================================
def fix_table_names(sql: str):
    tables = get_table_names()

    cleaned_map = {
        re.sub(r'\W+', '', t).lower(): t for t in tables
    }

    words = sql.split()
    corrected_words = []

    for word in words:
        clean_word = re.sub(r'\W+', '', word).lower()

        if clean_word in cleaned_map:
            corrected_words.append(cleaned_map[clean_word])
        else:
            corrected_words.append(word)

    return " ".join(corrected_words)


# =========================================================
# 🔹 STEP 6: GENERATE SQL (LLM)
# =========================================================
def generate_sql(question: str):
    try:
        schema = get_schema()
        relationships = detect_relationships()

        prompt = f"""
        You are an expert SQL generator.

        Database Schema:
        {schema}

        Detected Relationships:
        {relationships}

        RULES:
        - Use joins when needed
        - NEVER use SELECT *
        - Use table.column format
        - Ensure unique column names
        - Return ONLY SQL

        Question:
        {question}
        """

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False}
        )

        raw_output = response.json().get("response", "")

        sql = extract_sql(raw_output)
        return fix_table_names(sql)

    except Exception as e:
        print("ERROR generate_sql:", e)
        return ""


# =========================================================
# 🔹 STEP 7: MODIFY SQL USING SMART MEMORY
# =========================================================
def modify_sql_with_memory(last_sql: str, question: str):
    try:
        schema = get_schema()

        prompt = f"""
        You are an expert SQL assistant.

        Schema:
        {schema}

        Previous SQL:
        {last_sql}

        User Request:
        {question}

        TASK:
        Modify previous SQL.

        RULES:
        - Do NOT rewrite from scratch
        - Keep joins intact
        - Add filters / LIMIT / ORDER BY
        - Return ONLY SQL
        """

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False}
        )

        raw_output = response.json().get("response", "")

        sql = extract_sql(raw_output)
        return fix_table_names(sql)

    except Exception as e:
        print("ERROR modify_sql:", e)
        return last_sql


# =========================================================
# 🔹 STEP 8: EXECUTE SQL
# =========================================================
def execute_sql(query: str):
    try:
        if not query.lower().startswith("select"):
            return {"error": "Invalid SQL"}

        conn = sqlite3.connect("sales.db")
        cursor = conn.cursor()

        cursor.execute(query)

        columns = []
        seen = {}

        for desc in cursor.description:
            col = desc[0]
            if col in seen:
                seen[col] += 1
                col = f"{col}_{seen[col]}"
            else:
                seen[col] = 0
            columns.append(col)

        rows = cursor.fetchall()
        conn.close()

        return {"columns": columns, "rows": rows}

    except Exception as e:
        return {"error": str(e)}


# =========================================================
# 🔹 STEP 9: MAIN QUERY API
# =========================================================
@app.post("/query")
def run_query(data: dict = Body(...)):
    question = data.get("question")
    last_sql = data.get("last_sql")

    if last_sql:
        sql_query = modify_sql_with_memory(last_sql, question)
    else:
        sql_query = generate_sql(question)

    result = execute_sql(sql_query)

    return {"question": question, "sql": sql_query, "result": result}


# =========================================================
# 🔹 STEP 10: CSV UPLOAD
# =========================================================
@app.post("/upload_csv")
def upload_csv(file: UploadFile = File(...)):
    try:
        df = pd.read_csv(file.file)

        table_name = re.sub(r'\W+', '_', file.filename.split(".")[0])

        conn = sqlite3.connect("sales.db")
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.close()

        return {
            "message": f"Table '{table_name}' created",
            "columns": list(df.columns),
            "rows": len(df)
        }

    except Exception as e:
        return {"error": str(e)}


# =========================================================
# 🔹 STEP 11: RESET DATABASE
# =========================================================
@app.post("/reset_db")
def reset_db():
    if os.path.exists("sales.db"):
        os.remove("sales.db")
    return {"message": "Database reset successfully"}


# =========================================================
# 🔹 HEALTH CHECK
# =========================================================
@app.get("/")
def home():
    return {"message": "SQL Generator API is running 🚀"}