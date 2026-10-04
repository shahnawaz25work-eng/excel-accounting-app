import streamlit as st
import pandas as pd
from datetime import datetime
import openpyxl
import os
import time

EXCEL_FILE = "Accounting_Database.xlsx"

# 1. Safe write function to handle simultaneous user saves gracefully
def safe_write_to_excel(df_to_add, sheet_name):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                existing_df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
                updated_df = pd.concat([existing_df, df_to_add], ignore_index=True)
                updated_df.to_excel(writer, sheet_name=sheet_name, index=False)
            return True
        except PermissionError:
            time.sleep(0.5)  # Wait half a second if another user is writing to the file
    return False

# 2. Initialize default workbook structure if it doesn't exist
def initialize_excel():
    if not os.path.exists(EXCEL_FILE):
        wb = openpyxl.Workbook()
        sheets = [
            "Sales_Register", 
            "Purchase_Register", 
            "Cash_Book", 
            "Journal_Register", 
            "Bank_HDFC", 
            "Bank_SBI"
        ]
        for i, sheet_name in enumerate(sheets):
            if i == 0:
                ws = wb.active
                ws.title = sheet_name
            else:
                ws = wb.create_sheet(title=sheet_name)
            
            # Standardized column headers across all registers
            ws.append([
                "Entry_ID", 
                "Date", 
                "Particulars", 
                "Reference_No", 
                "GST_No", 
                "Payment_Mode", 
                "Debit", 
                "Credit", 
                "Narration"
            ])
        wb.save(EXCEL_FILE)

initialize_excel()

# 3. Streamlit Page Configuration
st.set_page_config(page_title="Multi-User Excel Accounting Software", layout="wide")
st.title("📊 Multi-User Online Accounting Software")

# Load all sheet names dynamically from the Excel file
excel_file_obj = pd.ExcelFile(EXCEL_FILE)
all_sheets = excel_file_obj.sheet_names

# Sidebar Navigation
st.sidebar.header("Navigation")
sheet_choice = st.sidebar.selectbox("Select Register/Sheet", all_sheets)

# Create a new sheet/register directly from the Web UI
with st.sidebar.expander("➕ Add New Register / Bank Account"):
    new_sheet_name = st.text_input("New Register Name (e.g., Bank_ICICI)").strip()
    if st.button("Create Register"):
        if new_sheet_name and new_sheet_name not in all_sheets:
            wb = openpyxl.load_workbook(EXCEL_FILE)
            ws = wb.create_sheet(title=new_sheet_name)
            ws.append([
                "Entry_ID", 
                "Date", 
                "Particulars", 
                "Reference_No", 
                "GST_No", 
                "Payment_Mode", 
                "Debit", 
                "Credit", 
                "Narration"
            ])
            wb.save(EXCEL_FILE)
            st.success(f"Register '{new_sheet_name}' created successfully!")
            st.rerun()
        elif new_sheet_name in all_sheets:
            st.error("A register with this name already exists.")

st.header(f"Register: `{sheet_choice}`")

# 4. Entry Input Form
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

# 5. Handle Form Submission
if submitted:
    new_entry = {
        "Entry_ID": [datetime.now().strftime("%Y%m%d%H%M%S")],
        "Date": [entry_date.strftime("%Y-%m-%d")],
        "Particulars": [particulars],
        "Reference_No": [ref_no],
        "GST_No": [gst_no],
        "Payment_Mode": [payment_mode],
        "Debit": [debit],
        "Credit": [credit],
        "Narration": [narration]
    }
    new_df = pd.DataFrame(new_entry)
    
    if safe_write_to_excel(new_df, sheet_choice):
        st.success(f"Entry recorded successfully in `{sheet_choice}`!")
    else:
        st.error("The system is busy saving another transaction. Please try clicking submit again.")

# 6. Refresh Button & Display Data
col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.subheader("Current Register Entries")
with col_refresh:
    if st.button("🔄 Refresh Entries"):
        st.rerun()

df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_choice)
st.dataframe(df, use_container_width=True)