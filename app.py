import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import gspread

# Spreadsheet ID from your Google Sheet URL
SPREADSHEET_ID = "1weNOVPKJk4UnCEufm8Sma_eFY5F6iYVKfCReRjORsuc"

@st.cache_resource
def get_gspread_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        key = str(creds_dict["private_key"])
        key = key.replace("\\\\n", "\n").replace("\\n", "\n")
        creds_dict["private_key"] = key
    return gspread.service_account_from_dict(creds_dict)

client = get_gspread_client()
spreadsheet = client.open_by_key(SPREADSHEET_ID)

# Configure Streamlit Page Layout
st.set_page_config(page_title="Accounting Dashboard", layout="centered")

# Custom CSS matching target UI colors
st.markdown("""
    <style>
    .main-title {
        font-size: 24px;
        font-weight: bold;
        color: #000000;
        margin-bottom: 20px;
    }
    .metric-box-debit {
        background-color: #fde8e8;
        border: 1px solid #f8b4b4;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        color: #9b1c1c;
        font-weight: bold;
    }
    .metric-box-credit {
        background-color: #e5f7ed;
        border: 1px solid #a3e6cd;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        color: #03543f;
        font-weight: bold;
    }
    .metric-box-balance {
        background-color: #e5f7ed;
        border: 1px solid #a3e6cd;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        color: #03543f;
        font-weight: bold;
        font-size: 18px;
    }
    div.stButton > button[kind="primary"] {
        background-color: #28a745 !important;
        color: white !important;
        border-radius: 8px;
        font-weight: bold;
        height: 48px;
        border: none;
    }
    div.stButton > button {
        border-radius: 8px;
        font-weight: bold;
        height: 42px;
    }
    </style>
""", unsafe_allow_html=True)

# Title Header
st.markdown('<div class="main-title">Welcome Rahmat Sir</div>', unsafe_allow_html=True)

# Helper function to normalize column strings
def clean_col_str(c):
    return str(c).strip().lower().replace("_", "").replace(" ", "")

# 1. Fetch Worksheets & Setup Session State
all_worksheets = [ws.title for ws in spreadsheet.worksheets()]
if "active_view" not in st.session_state:
    st.session_state.active_view = "LEDGER"

# 2. Account Register Select Box
p_col1, p_col2 = st.columns([1, 1])
with p_col1:
    selected_sheet = st.selectbox("Account Register", all_worksheets, key="account_register_select", label_visibility="collapsed")

# 3. Load Active Sheet Data
worksheet = spreadsheet.worksheet(selected_sheet)
raw_records = worksheet.get_all_records()
df = pd.DataFrame(raw_records) if raw_records else pd.DataFrame()

# 4. Extract Customer Names & Aggregated Data Across ALL Books
existing_customers_set = set()
all_books_records = []

for ws_name in all_worksheets:
    try:
        ws_data = spreadsheet.worksheet(ws_name).get_all_records()
        if ws_data:
            temp_df = pd.DataFrame(ws_data)
            temp_df["Source_Book"] = ws_name  # Track source book tab
            
            # Identify name column
            c_col = None
            for col in temp_df.columns:
                norm = clean_col_str(col)
                if any(k in norm for k in ["customer", "name", "client", "ledger", "party"]):
                    c_col = col
                    names = temp_df[col].dropna().astype(str).str.strip().unique()
                    for n in names:
                        if n and n.lower() not in ["none", "nan", "customer_name", "customer name", "name", "party name", "ledger"]:
                            existing_customers_set.add(n)
                    break
            
            all_books_records.append((temp_df, c_col))
    except Exception:
        continue

existing_customers = sorted(list(existing_customers_set))

# 5. Customer Selection Dropdown
customer_options = ["-- Select Existing Customer --", "➕ Create New Customer"] + existing_customers
selected_customer_option = st.selectbox("Customer Name Dropdown", customer_options, label_visibility="collapsed")

if selected_customer_option == "➕ Create New Customer":
    customer_name = st.text_input("Enter New Customer Name", placeholder="Type New Customer Name")
elif selected_customer_option != "-- Select Existing Customer --":
    customer_name = selected_customer_option
else:
    customer_name = ""

# 6. Filter Combined Data Across ALL Books
combined_customer_dfs = []

if customer_name:
    for book_df, name_col in all_books_records:
        if name_col and not book_df.empty:
            matched = book_df[book_df[name_col].astype(str).str.strip().str.lower() == customer_name.strip().lower()]
            if not matched.empty:
                combined_customer_dfs.append(matched)

if combined_customer_dfs:
    filtered_df = pd.concat(combined_customer_dfs, ignore_index=True)
else:
    filtered_df = df  # Default fallback to active sheet if no customer selected

# Identify Debit / Credit columns in filtered data
debit_col = None
credit_col = None

if not filtered_df.empty:
    for col in filtered_df.columns:
        norm = clean_col_str(col)
        if norm in ["debit", "debits", "amountdebit", "dr"]:
            debit_col = col
        elif norm in ["credit", "credits", "amountcredit", "cr"]:
            credit_col = col

total_debit = pd.to_numeric(filtered_df[debit_col], errors="coerce").sum() if debit_col and not filtered_df.empty else 0.0
total_credit = pd.to_numeric
