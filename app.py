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
active_df = pd.DataFrame(raw_records) if raw_records else pd.DataFrame()
std_active_df, _ = standardize_df(active_df, selected_sheet)

# 4. Extract Customer Names & Build Master Dataset across ALL Books
existing_customers_set = set()
all_standardized_dfs = []

for ws_name in all_worksheets:
    try:
        ws_data = spreadsheet.worksheet(ws_name).get_all_records()
        if ws_data:
            t_df = pd.DataFrame(ws_data)
            std_t_df, name_col = standardize_df(t_df, ws_name)
            
            if name_col in std_t_df.columns:
                names = std_t_df[name_col].dropna().astype(str).str.strip().unique()
                for n in names:
                    if n and n.lower() not in ["none", "nan", "customer_name", "customer name", "name", "party name", "ledger"]:
                        existing_customers_set.add(n)
                        
            all_standardized_dfs.append(std_t_df)
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
filtered_records = []

if customer_name:
    for book_df in all_standardized_dfs:
        if "Customer_Name" in book_df.columns and not book_df.empty:
            matched = book_df[book_df["Customer_Name"].astype(str).str.strip().str.lower() == customer_name.strip().lower()]
            if not matched.empty:
                filtered_records.append(matched)

if customer_name and filtered_records:
    filtered_df = pd.concat(filtered_records, ignore_index=True)
elif customer_name and not filtered_records:
    filtered_df = pd.DataFrame(columns=["Source_Book", "Date", "Customer_Name", "Debit", "Credit", "Description"])
else:
    filtered_df = std_active_df

# Calculate Balances
total_debit = pd.to_numeric(filtered_df["Debit"], errors="coerce").sum()
