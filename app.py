import streamlit as st
import pandas as pd
from datetime import datetime
import gspread

SPREADSHEET_ID = "1weNOVPKJk4UnCEufm8Sma_eFY5F6iYVKfCReRjORsuc"

@st.cache_resource
def get_gspread_client():
    # Convert st.secrets to a plain Python dictionary
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # Clean and replace double backslashes and escaped newlines
    if "private_key" in creds_dict:
        key = creds_dict["private_key"]
        key = key.replace("\\n", "\n").replace('\\\\n', '\n')
        creds_dict["private_key"] = key
        
    return gspread.service_account_from_dict(creds_dict)

client = get_gspread_client()
spreadsheet = client.open_by_key(SPREADSHEET_ID)

# Fetch all worksheet names
all_worksheets = [ws.title for ws in spreadsheet.worksheets()]

st.set_page_config(page_title="Multi-User Accounting Software", layout="wide")
st.title("📊 Online Accounting Software (Google Sheets Sync)")

# Sidebar Navigation
st.sidebar.header("Navigation")
sheet_choice = st.sidebar.selectbox("Select Register/Sheet", all_worksheets)

# Create a new worksheet/register
with st.sidebar.expander("➕ Add New Register / Bank Account"):
    new_sheet_name = st.text_input("New Register Name").strip()
    if st.button("Create Register"):
        if new_sheet_name and new_sheet_name not in all_worksheets:
            ws = spreadsheet.add_worksheet(title=new_sheet_name, rows=100, cols=20)
            ws.append_row([
                "Entry_ID", "Date", "Particulars", "Reference_No", 
                "GST_No", "Payment_Mode", "Debit", "Credit", "Narration"
            ])
            st.success(f"Register '{new_sheet_name}' created successfully!")
            st.rerun()
        elif new_sheet_name in all_worksheets:
            st.error("A register with this name already exists.")

st.header(f"Register: `{sheet_choice}`")
worksheet = spreadsheet.worksheet(sheet_choice)

# Form to input new entries
with st.form("transaction_form", clear_on_submit=True):
    st.subheader("Add New Entry")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        entry_date = st.date_input("Date", datetime.now())
        particulars = st.text_input("Particulars / Account Head")
        gst_no = st.text_input("GST No. (Optional)")
        
    with col2:
        ref_no = st.text_input("Invoice / Bill / Voucher No.")
        payment_mode = st.selectbox("Payment Mode", ["N/A", "Cash", "UPI", "NEFT/RTGS", "Cheque", "Card"])
        debit = st.number_input("Debit Amount", min_value=0.0, step=0.01)
        
    with col3:
        credit = st.number_input("Credit Amount", min_value=0.0, step=0.01)
        narration = st.text_input("Narration / Notes")
        
    submitted = st.form_submit_button("Record Entry")

if submitted:
    new_row = [
        datetime.now().strftime("%Y%m%d%H%M%S"),
        entry_date.strftime("%Y-%m-%d"),
        particulars,
        ref_no,
        gst_no,
        payment_mode,
        debit,
        credit,
        narration
    ]
    worksheet.append_row(new_row)
    st.success(f"Entry recorded directly in Google Sheets under `{sheet_choice}`!")

# Display current entries
col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.subheader("Current Register Entries")
with col_refresh:
    if st.button("🔄 Refresh"):
        st.rerun()

data = worksheet.get_all_records()
df = pd.DataFrame(data)
st.dataframe(df, use_container_width=True)
