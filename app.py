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

# 1. Fetch Worksheets & Setup Session State
all_worksheets = [ws.title for ws in spreadsheet.worksheets()]
if "active_view" not in st.session_state:
    st.session_state.active_view = "LEDGER"

# 2. Account Register Select Box
p_col1, p_col2 = st.columns([1, 1])
with p_col1:
    selected_sheet = st.selectbox(
        "Account Register", 
        all_worksheets, 
        key="account_register_select", 
        label_visibility="collapsed"
    )

# 3. Load Selected Sheet Data
worksheet = spreadsheet.worksheet(selected_sheet)
data = worksheet.get_all_records()
df = pd.DataFrame(data) if data else pd.DataFrame()

# Standardize column names (lowercase, no spaces/underscores)
def normalize_col(c):
    return str(c).strip().lower().replace("_", "").replace(" ", "")

if not df.empty:
    df.columns = [str(c).strip() for c in df.columns]

# 4. Extract Existing Customer Names from ALL worksheets
existing_customers_set = set()

for ws in spreadsheet.worksheets():
    ws_data = ws.get_all_records()
    if ws_data:
        ws_df = pd.DataFrame(ws_data)
        for col in ws_df.columns:
            if normalize_col(col) in ["customername", "customer", "name", "client"]:
                names = ws_df[col].dropna().astype(str).str.strip().tolist()
                for name in names:
                    if name and name.lower() not in ["customer_name", "customer name", "none", "nan"]:
                        existing_customers_set.add(name)

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

# 6. Filter Selected Worksheet Data and Compute Totals
customer_col = None
for col in df.columns:
    if normalize_col(col) in ["customername", "customer", "name", "client"]:
        customer_col = col
        break

if customer_name and customer_col:
    filtered_df = df[df[customer_col].astype(str).str.strip().str.lower() == customer_name.strip().lower()]
else:
    filtered_df = df

debit_col = next((c for c in df.columns if normalize_col(c) == "debit"), None)
credit_col = next((c for c in df.columns if normalize_col(c) == "credit"), None)

total_debit = pd.to_numeric(filtered_df[debit_col], errors="coerce").sum() if debit_col else 0.0
total_credit = pd.to_numeric(filtered_df[credit_col], errors="coerce").sum() if credit_col else 0.0
running_balance = total_credit - total_debit

# Place Balance metric next to Account Register dropdown
with p_col2:
    st.markdown(f'<div class="metric-box-balance">₹ {running_balance:,.2f}</div>', unsafe_allow_html=True)

# Metrics Cards Row
m_col1, m_col2, m_col3 = st.columns(3)
with m_col1:
    st.markdown(f'<div class="metric-box-debit">Total Debit<br>₹ {total_debit:,.2f}</div>', unsafe_allow_html=True)
with m_col2:
    st.markdown(f'<div class="metric-box-credit">Total Credit<br>₹ {total_credit:,.2f}</div>', unsafe_allow_html=True)
with m_col3:
    st.markdown(f'<div class="metric-box-balance">Balance<br>₹ {running_balance:,.2f}</div>', unsafe_allow_html=True)

st.write("")

# 7. Additional Entry Form Fields
c1, c2 = st.columns([1, 1])
with c1:
    unique_code = st.text_input("Unique Code", placeholder="Unique Code", label_visibility="collapsed")
with c2:
    entry_date = st.date_input("Date", datetime.now(), label_visibility="collapsed")

phone_number = st.text_input("Phone Number", placeholder="Phone Number", label_visibility="collapsed")
description = st.text_input("Description", placeholder="Description", label_visibility="collapsed")

st.write("")

# 8. Amount Inputs
a_col1, a_col2 = st.columns([1, 1])
with a_col1:
    amount_debit = st.number_input("Amount Debit", min_value=0.0, step=0.01, value=0.0)
with a_col2:
    amount_credit = st.number_input("Amount Credit", min_value=0.0, step=0.01, value=0.0)

st.write("")

# 9. SAVE ENTRY Action
if st.button("SAVE ENTRY", type="primary", use_container_width=True):
    if not customer_name.strip():
        st.error("Please select or enter a Customer Name before saving.")
    else:
        new_entry = [
            datetime.now().strftime("%Y%m%d%H%M%S"),
            entry_date.strftime("%Y-%m-%d"),
            customer_name.strip(),
            unique_code,
            phone_number,
            selected_sheet,
            amount_debit,
            amount_credit,
            description
        ]
        worksheet.append_row(new_entry)
        st.success(f"Entry recorded for `{customer_name}` in `{selected_sheet}`!")
        st.rerun()

# 10. Share Actions
s_col1, s_col2 = st.columns(2)
with s_col1:
    if st.button("Share", use_container_width=True):
        st.info("Summary copied to clipboard!")
with s_col2:
    if st.button("Share To Client", use_container_width=True):
        if phone_number.strip():
            msg = urllib.parse.quote(f"Hello {customer_name}, your current account balance is ₹ {running_balance:,.2f
