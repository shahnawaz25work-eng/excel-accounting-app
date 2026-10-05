import streamlit as st
import pandas as pd
from datetime import datetime
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

# Configure Streamlit Page
st.set_page_config(page_title="Accounting Software", layout="centered")

# Custom CSS for UI styling matching the screenshot
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
    div.stButton > button:first-child {
        border-radius: 8px;
        font-weight: bold;
        height: 45px;
    }
    </style>
""", unsafe_allow_html=True)

# App Title Header
st.markdown('<div class="main-title">Welcome Rahmat Sir</div>', unsafe_allow_html=True)

# Select Sheet Register
all_worksheets = [ws.title for ws in spreadsheet.worksheets()]
selected_sheet = st.sidebar.selectbox("Select Account / Register", all_worksheets)
worksheet = spreadsheet.worksheet(selected_sheet)

# Load existing data to compute metrics
data = worksheet.get_all_records()
df = pd.DataFrame(data) if data else pd.DataFrame(columns=["Debit", "Credit"])

# Calculate Totals
total_debit = pd.to_numeric(df["Debit"], errors="coerce").sum() if "Debit" in df.columns else 0.0
total_credit = pd.to_numeric(df["Credit"], errors="coerce").sum() if "Credit" in df.columns else 0.0
running_balance = total_credit - total_debit

# Customer Name Input
customer_name = st.text_input("Customer Name", placeholder="Customer Name", label_visibility="collapsed")

# Metrics Row 1: Total Debit, Total Credit, Balance
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

# Phone Number
phone_number = st.text_input("Phone Number", placeholder="Phone Number", label_visibility="collapsed")

# Description
description = st.text_input("Description", placeholder="Description", label_visibility="collapsed")

# Payment Mode & Current Balance Display Row
p_col1, p_col2 = st.columns([1, 1])
with p_col1:
    payment_mode = st.selectbox("Payment Mode", ["CASH", "BANK", "UPI", "CHEQUE"], label_visibility="collapsed")
with p_col2:
    st.markdown(f'<div class="metric-box-balance">₹ {running_balance:,.2f}</div>', unsafe_allow_html=True)

st.write("")

# Amount Debit & Amount Credit Row
a_col1, a_col2 = st.columns([1, 1])
with a_col1:
    amount_debit = st.number_input("Amount Debit", min_value=0.0, step=0.01, placeholder="Amount Debit")
with a_col2:
    amount_credit = st.number_input("Amount Credit", min_value=0.0, step=0.01, placeholder="Amount Credit")

st.write("")

# SAVE ENTRY Button
if st.button("SAVE ENTRY", type="primary", use_container_width=True):
    new_entry = [
        datetime.now().strftime("%Y%m%d%H%M%S"),
        entry_date.strftime("%Y-%m-%d"),
        customer_name,
        unique_code,
        phone_number,
        payment_mode,
        amount_debit,
        amount_credit,
        description
    ]
    worksheet.append_row(new_entry)
    st.success("Entry saved successfully!")
    st.rerun()

# Action Buttons: Share & Share To Client
s_col1, s_col2 = st.columns(2)
with s_col1:
    st.button("Share", use_container_width=True)
with s_col2:
    st.button("Share To Client", use_container_width=True)

# Navigation Buttons: Statement, LEDGER, BALANCE
nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    st.button("Statement", use_container_width=True)
with nav_col2:
    st.button("LEDGER", use_container_width=True)
with nav_col3:
    st.button("BALANCE", use_container_width=True)

# Ledger Data Table View
if not df.empty:
    st.markdown("### Transaction Records")
    st.dataframe(df, use_container_width=True)
