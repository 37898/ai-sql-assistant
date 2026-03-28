import streamlit as st
import requests
import pandas as pd

st.info("⚠️ Demo Mode: Backend not connected. Showing sample results.")
# =====================================================
# 🧠 SESSION MEMORY (SMART SQL MEMORY)
# =====================================================
if "last_sql" not in st.session_state:
    st.session_state.last_sql = None


# =====================================================
# 🎨 PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="AI SQL Assistant",
    page_icon="🤖",
    layout="wide"
)

# =====================================================
# 🎯 HEADER
# =====================================================
st.title("🤖 AI SQL Assistant")
st.markdown(
    "Upload data → Ask questions → Get SQL, results, and charts instantly 📊"
)

st.divider()

# =====================================================
# 📂 SIDEBAR: CSV UPLOAD
# =====================================================
st.sidebar.header("📂 Upload Dataset")

uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])

if uploaded_file is not None:
    with st.sidebar:
        with st.spinner("Uploading dataset..."):
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/upload_csv",
                    files={"file": uploaded_file}
                )
                result = response.json()

                if "error" in result:
                    st.error(result["error"])
                else:
                    st.success("✅ Dataset uploaded")
                    st.write(f"Rows: {result['rows']}")

            except:
                st.warning("⚠️ Backend not available (Demo mode)")

st.sidebar.divider()

# =====================================================
# ➕ SIDEBAR: CREATE TABLE
# =====================================================
st.sidebar.header("➕ Create Table")

table_name = st.sidebar.text_input("Table Name")

columns_input = st.sidebar.text_area(
    "Columns (format: name TYPE)",
    "id INTEGER, name TEXT"
)

if st.sidebar.button("Create Table"):
    try:
        columns = []
        for col in columns_input.split(","):
            name, col_type = col.strip().split()
            columns.append({"name": name, "type": col_type})

        response = requests.post(
            "http://127.0.0.1:8000/create_table",
            json={"table_name": table_name, "columns": columns}
        )

        res = response.json()

        if "error" in res:
            st.sidebar.error(res["error"])
        else:
            st.sidebar.success("✅ Table created")

    except Exception as e:
        st.sidebar.error(f"Invalid format: {e}")

# =====================================================
# 💬 QUERY INPUT
# =====================================================
st.subheader("💬 Ask your data")

question = st.text_input(
    "Enter your question",
    placeholder="e.g., total revenue by customer"
)

col1, col2 = st.columns([1, 5])

with col1:
    run_btn = st.button("Run Query 🚀")

# =====================================================
# 🔍 QUERY EXECUTION (WITH FALLBACK DEMO)
# =====================================================
if run_btn and question:
    with st.spinner("Analyzing... 🤖"):

        try:
            response = requests.post(
                "http://127.0.0.1:8000/query",
                json={
                    "question": question,
                    "last_sql": st.session_state.last_sql
                }
            )
            data = response.json()

        except:
            # 🔥 FALLBACK DEMO MODE
            data = {
                "sql": """SELECT name, SUM(revenue) AS total_revenue
FROM customers
JOIN orders USING(customer_id)
GROUP BY name;""",
                "result": {
                    "columns": ["name", "total_revenue"],
                    "rows": [
                        ["Alice", 1250],
                        ["Bob", 100],
                        ["Charlie", 300]
                    ]
                }
            }

    # =================================================
    # 🧠 SAVE LAST SQL (SMART MEMORY)
    # =================================================
    st.session_state.last_sql = data.get("sql")

    st.divider()

    # =================================================
    # 🧾 SHOW SQL
    # =================================================
    if "sql" in data:
        st.subheader("🧾 Generated SQL")
        st.code(data["sql"], language="sql")

    # =================================================
    # ⚠️ ERROR HANDLING
    # =================================================
    if "error" in data:
        st.error(f"⚠️ Error: {data['error']}")

        if "fixed_sql" in data:
            st.subheader("🔧 Fixed SQL")
            st.code(data["fixed_sql"], language="sql")

    # =================================================
    # 📊 RESULTS
    # =================================================
    result = data.get("result", {})

    if "columns" in result and "rows" in result:
        df = pd.DataFrame(result["rows"], columns=result["columns"])

        st.subheader("📊 Results")
        st.dataframe(df, use_container_width=True)

        # =====================================================
        # 📈 AUTO CHART GENERATION
        # =====================================================
        try:
            numeric_cols = df.select_dtypes(include=['number']).columns

            if len(df.columns) >= 2 and len(numeric_cols) > 0:

                st.subheader("📈 Visualization")

                y_col = numeric_cols[0]
                x_col = df.columns[0]

                chart_type = st.selectbox(
                    "Select Chart Type",
                    ["Bar", "Line", "Area"]
                )

                chart_data = df.set_index(x_col)[y_col]

                if chart_type == "Bar":
                    st.bar_chart(chart_data)

                elif chart_type == "Line":
                    st.line_chart(chart_data)

                elif chart_type == "Area":
                    st.area_chart(chart_data)

        except:
            st.warning("Chart not available for this query")

    elif "error" in result:
        st.error(f"Execution Error: {result['error']}")