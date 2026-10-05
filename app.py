import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import gspread

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

@st.cache_data(ttl=60)
def load_all_sheet_data():
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheets = spreadsheet.worksheets()
    data_dict = {}
    for ws in worksheets:
        data_dict[ws.title] = ws.get_all_records()
    return data_dict

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

# Standardize DataFrame columns across different sheets
def standardize_df(temp_df, sheet_name):
    if temp_df.empty:
        return temp_df, None
    
    col_mapping = {}
    name_col_found = None
    
    for col in temp_df.columns:
        norm = clean_col_str(col)
        if any(k in norm for k in ["customer", "name", "client", "ledger", "party"]):
            col_mapping[col] = "Customer_Name"
            name_col_found = "Customer_Name"
        elif norm in ["debit", "debits", "amountdebit", "dr"]:
            col_mapping[col] = "Debit"
        elif norm in ["credit", "credits", "amountcredit", "cr"]:
            col_mapping[col] = "Credit"
        elif any(k in norm for k in ["date", "time", "day"]):
            col_mapping[col] = "Date"
        elif any(k in norm for k in ["desc", "particulars", "detail", "narration", "remark"]):
            col_mapping[col] = "Description"
            
    std_df = temp_df.rename(columns=col_mapping)
    std_df["Source_Book"] = sheet_name
    return std_df, name_col_found

# 1. Fetch Worksheets & Load Data
all_sheet_data = load_all_sheet_data()
all_worksheets = list(all_sheet_data.keys())

if "active_view" not in st.session_state:
    st.session_state.active_view = "LEDGER"

# 2. Account Register Select Box
p_col1, p_col2 = st.columns([1, 1])
with p_col1:
    selected_sheet = st.selectbox("Account Register", all_worksheets, key="account_register_select", label_visibility="collapsed")

# 3. Load Active Sheet Data
raw_records = all_sheet_data.get(selected_sheet, [])
active_df = pd.DataFrame(raw_records) if raw_records else pd.DataFrame()
std_active_df, _ = standardize_df(active_df, selected_sheet)

# 4. Extract Customer Names & Build Master Dataset across ALL Books
existing_customers_set = set()
all_standardized_dfs = []

for ws_name, ws_records in all_sheet_data.items():
    if ws_records:
        t_df = pd.DataFrame(ws_records)
        std_t_df, name_col = standardize_df(t_df, ws_name)
        
        if name_col in std_t_df.columns:
            names = std_t_df[name_col].dropna().astype(str).str.strip().unique()
            for n in names:
                if n and n.lower() not in ["none", "nan", "customer_name", "customer name", "name", "party name", "ledger"]:
                    existing_customers_set.add(n)
                    
        all_standardized_dfs.append(std_t_df)

existing_customers = sorted(list(existing_customers_set))

# Calculate Grand Master Combined Totals Across ALL Books
if all_standardized_dfs:
    master_df = pd.concat(all_standardized_dfs, ignore_index=True)
    grand_debit = pd.to_numeric(master_df["Debit"], errors="coerce").sum() if "Debit" in master_df.columns else 0.0
    grand_credit = pd.to_numeric(master_df["Credit"], errors="coerce").sum() if "Credit" in master_df.columns else 0.0
    grand_balance = grand_credit - grand_debit
else:
    grand_debit, grand_credit, grand_balance = 0.0, 0.0, 0.0

# 5. Customer Selection Dropdown
customer_options = ["-- Select Existing Customer --", "➕ Create New Customer"] + existing_customers
