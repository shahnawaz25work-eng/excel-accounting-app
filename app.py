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

# Custom CSS matching exact UI screenshot colors
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
    /* Primary Green Save Button */
    div.stButton > button[kind="primary"] {
        background-color: #28a745 !important;
        color: white !important;
        border-radius: 8px;
        font-weight: bold;
        height: 48px;
        border: none;
    }
    /* Secondary Action Buttons */
    div.stButton > button {
        border-radius: 8px;
        font-weight: bold;
        height: 42px;
    }
    </style>
""", unsafe_allow_html=True)

# Title Header
st.markdown('<div class="main-title">Welcome Rahmat Sir</div>', unsafe_allow_html=True)

# 1. Fetch available worksheets first
all_worksheets = [ws.title for ws in spreadsheet.worksheets()]

# Initialize state view
if "active_view" not in st.session_state:
    st.session_state.active_view = "LEDGER"

# 2. Input Fields
customer_name = st.text_input("Customer Name", placeholder="Customer Name", label_visibility="collapsed")

# 3. Account Register Select Box (Placed where CASH was in screenshot)
p_col1, p_col2 = st.columns([1, 1])
with p_col1:
    selected_sheet = st.selectbox(
        "Account Register", 
        all_worksheets, 
        key="account_register_select", 
        label_visibility="collapsed"
    )

# Load data from the selected worksheet
worksheet = spreadsheet.worksheet(selected_sheet)
data = worksheet.get_all_records()
df = pd.DataFrame(data) if data else pd.DataFrame(columns=["Debit", "Credit"])

# Filter dataframe by Customer Name
if customer_name.strip() and "Customer_Name" in df.columns:
    filtered_df = df[df["Customer_Name"].astype(str).str.contains(customer_name, case=False, na=False)]
else:
    filtered_df = df

# Compute Debit, Credit & Running Balance
total_debit = pd.to_numeric(filtered_df["Debit"], errors="coerce").sum() if "Debit" in filtered_df.columns else 0.0
total_credit = pd.to_numeric(filtered_df["Credit"], errors="coerce").sum() if "Credit" in filtered_df.columns else 0.0
running_balance = total_credit - total_debit

# Place Balance metric next to Account Register dropdown
with p_col2:
    st.markdown(f'<div class="metric-box-balance">₹ {running_balance:,.2f}</div>', unsafe_allow_html=True)

# Metrics Row: Total Debit, Total Credit, Net Balance
m_col1, m_col2, m_col3 = st.columns(3)
with m_col1:
    st.markdown(f'<div class="metric-box-debit">Total Debit<br>₹ {total_debit:,.2f}</div>', unsafe_allow_html=True)
with m_col2:
    st.markdown(f'<div class="metric-box-credit">Total Credit<br>₹ {total_credit:,.2f}</div>', unsafe_allow_html=True)
with m_col3:
    st.markdown(f'<div class="metric-box-balance">Balance<br>₹ {running_balance:,.2f}</div>', unsafe_allow_html=True)

st.write("")

# Unique Code & Date Row
c1, c2 = st.columns([1, 1])
with c1:
    unique_code = st.text_input("Unique Code", placeholder="Unique Code", label_visibility="collapsed")
with c2:
    entry_date = st.date_input("Date", datetime.now(), label_visibility="collapsed")

# Phone Number & Description
phone_number = st.text_input("Phone Number", placeholder="Phone Number", label_visibility="collapsed")
description = st.text_input("Description", placeholder="Description", label_visibility="collapsed")

st.write("")

# Amount Debit & Amount Credit
