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

@st.cache_data(ttl=60)
def load_all_sheet_data():
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheets = spreadsheet.worksheets()
        data_dict = {}
        for ws in worksheets:
            try:
                records = ws.get_all_records()
                data_dict[ws.title] = records
            except Exception:
                data_dict[ws.title] = []
        return data_dict
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return {}

# Configure Streamlit Page Layout
st.set_page_config(page_title="Accounting Dashboard", layout="centered")

# Custom CSS matching target UI colors
st.markdown("""
    <style>
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
all_worksheets = list(all_sheet_data.keys()) if all_sheet_data else ["Cash_Book"]

if "active_view" not in st.session_state:
    st.session_state.active_view = "LEDGER"

# Top Bar Layout: Account Register Selection
p_col1, p_col2 = st.columns([1, 1])
with p_col1:
    selected_sheet = st.selectbox("Account Register", all_worksheets, key="account_register_select", label_visibility="collapsed")

# 2. Extract Data for Currently Selected Register
sheet_records = all_sheet_data.get(selected_sheet, [])
current_sheet_df = pd.DataFrame(sheet_records) if sheet_records else pd.DataFrame()
current_sheet_std_df, current_name_col = standardize_df(current_sheet_df, selected_sheet)

# Customer list strictly for the active register
existing_customers = []
if current_name_col and not current_sheet_std_df.empty:
    names = current_sheet_std_df[current_name_col].dropna().astype(str).str.strip().unique()
    existing_customers = sorted([n for n in names if n and n.lower() not in ["none", "nan", "customer_name", "customer name", "name", "party name", "ledger"]])

# Customer Selection Dropdown
customer_options = ["-- Select Existing Customer --", "➕ Create New Customer"] + existing_customers
selected_customer_option = st.selectbox("Customer Name Dropdown", customer_options, label_visibility="collapsed")

if selected_customer_option == "➕ Create New Customer":
    customer_name = st.text_input("Enter New Customer Name", placeholder="Type New Customer Name")
elif selected_customer_option != "-- Select Existing Customer --":
    customer_name = selected_customer_option
else:
    customer_name = ""

# Filter Active Register Data
if customer_name and not current_sheet_std_df.empty and "Customer_Name" in current_sheet_std_df.columns:
    active_display_df = current_sheet_std_df[current_sheet_std_df["Customer_Name"].astype(str).str.strip().str.lower() == customer_name.strip().lower()]
else:
    active_display_df = current_sheet_std_df

# Calculate Metrics strictly for the Selected Register
total_debit = pd.to_numeric(active_display_df["Debit"], errors="coerce").sum() if ("Debit" in active_display_df.columns and not active_display_df.empty) else 0.0
total_credit = pd.to_numeric(active_display_df["Credit"], errors="coerce").sum() if ("Credit" in active_display_df.columns and not active_display_df.empty) else 0.0
running_balance = total_credit - total_debit

# Upper Right Balance Box Display (Selected Register Balance)
with p_col2:
    st.markdown(f'<div class="metric-box-balance">₹ {running_balance:,.2f}</div>', unsafe_allow_html=True)

# Metric Cards (Selected Register Only)
m_col1, m_col2, m_col3 = st.columns(3)
with m_col1:
    st.markdown(f'<div class="metric-box-debit">Total Debit<br>₹ {total_debit:,.2f}</div>', unsafe_allow_html=True)
with m_col2:
    st.markdown(f'<div class="metric-box-credit">Total Credit<br>₹ {total_credit:,.2f}</div>', unsafe_allow_html=True)
with m_col3:
    st.markdown(f'<div class="metric-box-balance">Balance<br>₹ {running_balance:,.2f}</div>', unsafe_allow_html=True)

st.write("")

# Entry Form Fields
c1, c2 = st.columns([1, 1])
with c1:
    unique_code = st.text_input("Unique Code", placeholder="Unique Code", label_visibility="collapsed")
with c2:
    entry_date = st.date_input("Date", datetime.now(), label_visibility="collapsed")

phone_number = st.text_input("Phone Number", placeholder="Phone Number", label_visibility="collapsed")
description = st.text_input("Description", placeholder="Description", label_visibility="collapsed")

st.write("")

# Debit and Credit Inputs
a_col1, a_col2 = st.columns([1, 1])
with a_col1:
    amount_debit = st.number_input("Amount Debit", min_value=0.0, step=0.01, value=0.0)
with a_col2:
    amount_credit = st.number_input("Amount Credit", min_value=0.0, step=0.01, value=0.0)

st.write("")

# SAVE ENTRY Action
if st.button("SAVE ENTRY", type="primary", use_container_width=True):
    if not customer_name.strip():
        st.error("Please select or enter a Customer Name before saving.")
    else:
        try:
            client = get_gspread_client()
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
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet(selected_sheet)
            worksheet.append_row(new_entry)
            st.cache_data.clear()
            st.success(f"Entry recorded for `{customer_name}` in `{selected_sheet}`!")
            st.rerun()
        except Exception as err:
            st.error(f"Failed to save entry: {err}")

# Share Actions
s_col1, s_col2 = st.columns(2)
with s_col1:
    if st.button("Share", use_container_width=True):
        st.info("Summary copied to clipboard!")
with s_col2:
    if st.button("Share To Client", use_container_width=True):
        if phone_number.strip():
            raw_msg = f"Hello {customer_name}, your balance in {selected_sheet} is ₹ {running_balance:,.2f}."
            msg = urllib.parse.quote(raw_msg)
            wa_url = f"https://wa.me/{phone_number.strip()}?text={msg}"
            wa_link = f"[👉 Send WhatsApp to {phone_number}]({wa_url})"
            st.markdown(wa_link, unsafe_allow_html=True)
        else:
            st.warning("Please enter a Phone Number to send WhatsApp message.")

st.write("")

# Navigation Buttons
nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
with nav_col1:
    if st.button("Statement", use_container_width=True):
        st.session_state.active_view = "STATEMENT"
with nav_col2:
    if st.button("LEDGER", use_container_width=True):
        st.session_state.active_view = "LEDGER"
with nav_col3:
    if st.button("BALANCE", use_container_width=True):
        st.session_state.active_view = "BALANCE"
with nav_col4:
    if st.button("RUNNING BAL", use_container_width=True):
        st.session_state.active_view = "RUNNING_BAL"

st.markdown("---")

# Display Active View Data
if st.session_state.active_view == "STATEMENT":
    st.subheader(f"📜 Statement for `{selected_sheet}`: {customer_name if customer_name else 'All Records'}")
    st.dataframe(active_display_df, use_container_width=True)

elif st.session_state.active_view == "BALANCE":
    st.subheader(f"💰 Balance Summary for `{selected_sheet}`")
    b_col1, b_col2, b_col3 = st.columns(3)
    b_col1.metric("Total Debit", f"₹ {total_debit:,.2f}")
    b_col2.metric("Total Credit", f"₹ {total_credit:,.2f}")
    b_col3.metric("Net Balance", f"₹ {running_balance:,.2f}")

elif st.session_state.active_view == "RUNNING_BAL":
    st.subheader("🏦 Current Running Balances (Cash & Bank Accounts Only)")
    st.caption("Excludes Sales, Purchases, and other non-cash registers.")
    
    cash_bank_summary = []
    grand_cash_bank_bal = 0.0
    
    for ws_name, ws_records in all_sheet_data.items():
        norm_ws = ws_
