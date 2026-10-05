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

def rename_client_in_sheets(old_name, new_name):
    client = get_gspread_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheets = spreadsheet.worksheets()
    updated_count = 0
    
    for ws in worksheets:
        try:
            records = ws.get_all_records()
            if not records:
                continue
            
            headers = list(records[0].keys()) if records else []
            customer_col_idx = None
            
            for idx, h in enumerate(headers, start=1):
                norm_h = str(h).strip().lower().replace("_", "").replace(" ", "")
                if any(k in norm_h for k in ["customer", "name", "client", "ledger", "party"]):
                    customer_col_idx = idx
                    break
            
            if customer_col_idx:
                cell_list = ws.findall(old_name)
                cells_to_update = []
                for cell in cell_list:
                    if cell.col == customer_col_idx:
                        cell.value = new_name
                        cells_to_update.append(cell)
                        updated_count += 1
                if cells_to_update:
                    ws.update_cells(cells_to_update)
        except Exception as ex:
            st.warning(f"Could not update in sheet {ws.title}: {ex}")
            
    return updated_count

def update_client_phone_in_sheets(target_client, phone_num):
    if not target_client or not phone_num:
        return 0
    client = get_gspread_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheets = spreadsheet.worksheets()
    updated_count = 0
    
    for ws in worksheets:
        try:
            records = ws.get_all_records()
            if not records:
                continue
            
            headers = list(records[0].keys()) if records else []
            customer_col_idx = None
            phone_col_idx = None
            
            for idx, h in enumerate(headers, start=1):
                norm_h = str(h).strip().lower().replace("_", "").replace(" ", "")
                if any(k in norm_h for k in ["customer", "name", "client", "ledger", "party"]):
                    customer_col_idx = idx
                elif any(k in norm_h for k in ["phone", "mobile", "contact", "number", "cell"]):
                    phone_col_idx = idx
            
            if customer_col_idx and phone_col_idx:
                cell_list = ws.findall(target_client)
                cells_to_update = []
                for cell in cell_list:
                    if cell.col == customer_col_idx:
                        p_cell = ws.cell(cell.row, phone_col_idx)
                        if str(p_cell.value).strip() != str(phone_num).strip():
                            p_cell.value = str(phone_num).strip()
                            cells_to_update.append(p_cell)
                            updated_count += 1
                if cells_to_update:
                    ws.update_cells(cells_to_update)
        except Exception as ex:
            pass
            
    return updated_count

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
        elif any(k in norm for k in ["phone", "mobile", "contact", "number", "cell"]):
            col_mapping[col] = "Phone_Number"
            
    std_df = temp_df.rename(columns=col_mapping)
    std_df["Source_Book"] = sheet_name
    return std_df, name_col_found

# 1. Fetch Worksheets & Load Data
all_sheet_data = load_all_sheet_data()
all_worksheets = list(all_sheet_data.keys()) if all_sheet_data else ["Cash_Book"]

if "active_view" not in st.session_state:
    st.session_state.active_view = "LEDGER"

# Build Master Combined Dataset across ALL Registers
all_standardized_dfs = []
all_customers_set = set()
client_phone_map = {}

for ws_name, ws_records in all_sheet_data.items():
    if ws_records:
        t_df = pd.DataFrame(ws_records)
        std_t_df, name_col = standardize_df(t_df, ws_name)
        if name_col in std_t_df.columns:
            names = std_t_df[name_col].dropna().astype(str).str.strip().unique()
            for n in names:
                if n and n.lower() not in ["none", "nan", "customer_name", "customer name", "name", "party name", "ledger"]:
                    all_customers_set.add(n)
                    if "Phone_Number" in std_t_df.columns:
                        p_val = std_t_df[std_t_df[name_col].astype(str).str.strip() == n]["Phone_Number"].dropna().astype(str).str.strip().tolist()
                        valid_p = [p for p in p_val if p and p.lower() not in ["none", "nan", "0", ""]]
                        if valid_p and n not in client_phone_map:
                            client_phone_map[n] = valid_p[0]
        all_standardized_dfs.append(std_t_df)

master_df = pd.concat(all_standardized_dfs, ignore_index=True) if all_standardized_dfs else pd.DataFrame()
all_existing_customers = sorted(list(all_customers_set))

# Top Bar Layout: Account Register Selection
p_col1, p_col2 = st.columns([1, 1])
with p_col1:
    selected_sheet = st.selectbox("Account Register", all_worksheets, key="account_register_select", label_visibility="collapsed")

# 2. Customer Selection Dropdown
customer_options = ["-- Select Existing Customer --", "➕ Create New Customer"] + all_existing_customers
selected_customer_option = st.selectbox("Customer Name Dropdown", customer_options, label_visibility="collapsed")

if selected_customer_option == "➕ Create New Customer":
    customer_name = st.text_input("Enter New Customer Name", placeholder="Type New Customer Name")
elif selected_customer_option != "-- Select Existing Customer --":
    customer_name = selected_customer_option
else:
    customer_name = ""

# Active Register Data
sheet_records = all_sheet_data.get(selected_sheet, [])
current_sheet_df = pd.DataFrame(sheet_records) if sheet_records else pd.DataFrame()
current_sheet_std_df, _ = standardize_df(current_sheet_df, selected_sheet)

if customer_name and not current_sheet_std_df.empty and "Customer_Name" in current_sheet_std_df.columns:
    active_display_df = current_sheet_std_df[current_sheet_std_df["Customer_Name"].astype(str).str.strip().str.lower() == customer_name.strip().lower()]
else:
    active_display_df = current_sheet_std_df

# Filter Combined Master Data across ALL Registers
if customer_name and not master_df.empty and "Customer_Name" in master_df.columns:
    customer_master_df = master_df[master_df["Customer_Name"].astype(str).str.strip().str.lower() == customer_name.strip().lower()]
else:
    customer_master_df = master_df

# Calculate Grand Totals across ALL Registers
if not customer_master_df.empty:
    combined_debit = pd.to_numeric(customer_master_df["Debit"], errors="coerce").sum() if "Debit" in customer_master_df.columns else 0.0
    combined_credit = pd.to_numeric(customer_master_df["Credit"], errors="coerce").sum() if "Credit" in customer_master_df.columns else 0.0
else:
    combined_debit = 0.0
    combined_credit = 0.0

combined_balance = combined_debit - combined_credit

# Display Upper Right Combined Balance Box
with p_col2:
    st.markdown(f'<div class="metric-box-balance">₹ {combined_balance:,.2f}</div>', unsafe_allow_html=True)

# Main Dashboard Metric Cards (Combined Across ALL Registers)
m_col1, m_col2, m_col3 = st.columns(3)
with m_col1:
    st.markdown(f'<div class="metric-box-debit">Total Amt (Debit)<br>₹ {combined_debit:,.2f}</div>', unsafe_allow_html=True)
with m_col2:
    st.markdown(f'<div class="metric-box-credit">Rec. Amt (Credit)<br>₹ {combined_credit:,.2f}</div>', unsafe_allow_html=True)
with m_col3:
    st.markdown(f'<div class="metric-box-balance">Bal. Amt<br>₹ {combined_balance:,.2f}</div>', unsafe_allow_html=True)

st.write("")

# Auto-fill saved phone number if available
saved_phone = client_phone_map.get(customer_name, "")

# Entry Form Fields
c1, c2 = st.columns([1, 1])
with c1:
    unique_code = st.text_input("Unique Code", placeholder="Unique Code", label_visibility="collapsed")
with c2:
    entry_date = st.date_input("Date", datetime.now(), label_visibility="collapsed")

phone_number = st.text_input("Phone Number", value=saved_phone, placeholder="Phone Number", label_visibility="collapsed")
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
                phone_number.strip(),
                selected_sheet,
                amount_debit,
                amount_credit,
                description
            ]
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet(selected_sheet)
            worksheet.append_row(new_entry)
            
            # Save phone number across all records if provided
            if phone_number.strip():
                update_client_phone_in_sheets(customer_name.strip(), phone_number.strip())

            st.cache_data.clear()
            st.success(f"Entry recorded for `{customer_name}` in `{selected_sheet}`!")
            st.rerun()
        except Exception as err:
            st.error(f"Failed to save entry: {err}")

# Build WhatsApp Formatted Statement Text
def build_whatsapp_statement(c_name, c_debit, c_credit, c_bal, df_trans):
    today_str = datetime.now().strftime("%d/%m/%Y")
    lines = [
        "─────────────",
        f"Updated : {today_str}",
        "─────────────",
        f"Name : {c_name}",
        "─────────────",
        f"Total Amt : Rs {c_debit:,.2f}/-",
        f"Rec. Amt : Rs {c_credit:,.2f}/-",
        "─────────────",
        f"Bal. Amt : Rs {c_bal:,.2f}/-",
        "─────────────",
        "Credit Statement",
        "Date | Mode | Amount"
    ]
    
    if not df_trans.empty:
        # Filter for credit transactions
        credit_rows = df_trans[pd.to_numeric(df_trans["Credit"], errors="coerce") > 0]
        if not credit_rows.empty:
            for _, r in credit_rows.iterrows():
                dt = str(r.get("Date", "")).strip()
                mode = str(r.get("Source_Book", "")).replace("_", " ").upper()
                amt = float(r.get("Credit", 0.0))
                lines.append(f"{dt} | {mode} | ₹ {amt:,.2f}")
        else:
            lines.append("No credit entries found.")
    else:
        lines.append("No transactions recorded.")
        
    lines.extend([
        "─────────────",
        "If there is any mistake or confusion, please let us know.",
        "Thank you for choosing Green City",
        "RADEV INFRA PVT. LTD."
    ])
    return "\n".join(lines)

# Share Actions
s_col1, s_col2 = st.columns(2)
with s_col1:
    if st.button("Share Summary Text", use_container_width=True):
        wa_text = build_whatsapp_statement(customer_name, combined_debit, combined_credit, combined_balance, customer_master_df)
        st.code(wa_text, language="text")

with s_col2:
    if st.button("Share To Client", use_container_width=True):
        if phone_number.strip():
            # Update phone in Google Sheets if updated in input
            if phone_number.strip() != saved_phone:
                update_client_phone_in_sheets(customer_name.strip(), phone_number.strip())
                st.cache_data.clear()

            raw_msg = build_whatsapp_statement(customer_name, combined_debit, combined_credit, combined_balance, customer_master_df)
            msg = urllib.parse.quote(raw_msg)
            clean_p = "".join(filter(str.isdigit, phone_number.strip()))
            wa_url = f"https://wa.me/{clean_p}?text={msg}"
            wa_link = f"[👉 Click Here to Send WhatsApp to {customer_name}]({wa_url})"
            st.markdown(wa_link, unsafe_allow_html=True)
        else:
            st.warning("Please enter a Phone Number to send WhatsApp message.")

st.write("")

# Navigation Buttons
nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns(5)
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
with nav_col5:
    if st.button("EDIT CLIENT", use_container_width=True):
        st.session_state.active_view = "EDIT_CLIENT"

st.markdown("---")

# Display Active View Data
if st.session_state.active_view == "STATEMENT":
    st.subheader(f"📜 All Register Statement: {customer_name if customer_name else 'All Records'}")
    st.dataframe(customer_master_df, use_container_width=True)

elif st.session_state.active_view == "BALANCE":
    st.subheader(f"💰 Combined Totals for `{customer_name if customer_name else 'All Registers'}`")
    b_col1, b_col2, b_col3 = st.columns(3)
    b_col1.metric("Total Amt (Debit)", f"₹ {combined_debit:,.2f}")
    b_col2.metric("Rec. Amt (Credit)", f"₹ {combined_credit:,.2f}")
    b_col3.metric("Bal. Amt", f"₹ {combined_balance:,.2f}")

elif st.session_state.active_view == "RUNNING_BAL":
    st.subheader("🏦 Current Running Balances (Cash & Bank Accounts Only)")
    st.caption("Excludes Sales, Purchases, and other non-cash registers.")
    
    cash_bank_summary = []
    grand_cash_bank_bal = 0.0
    
    for ws_name, ws_records in all_sheet_data.items():
        norm_ws = ws_name.lower().replace("_", "").replace(" ", "")
        if not any(ex in norm_ws for ex in ["sale", "purchase", "item", "stock"]):
            if ws_records:
                w_df = pd.DataFrame(ws_records)
                std_w_df, _ = standardize_df(w_df, ws_name)
                c_deb = pd.to_numeric(std_w_df["Debit"], errors="coerce").sum() if "Debit" in std_w_df.columns else 0.0
                c_cred = pd.to_numeric(std_w_df["Credit"], errors="coerce").sum() if "Credit" in std_w_df.columns else 0.0
                c_bal = c_cred - c_deb
                grand_cash_bank_bal += c_bal
                cash_bank_summary.append({
                    "Account / Register": ws_name,
                    "Total Debit (₹)": f"{c_deb:,.2f}",
                    "Total Credit (₹)": f"{c_cred:,.2f}",
                    "Running Balance (₹)": f"{c_bal:,.2f}"
                })
    
    st.markdown(f"### **Total Liquid Balance: ₹ {grand_cash_bank_bal:,.2f}**")
    if cash_bank_summary:
        st.table(pd.DataFrame(cash_bank_summary))
    else:
        st.info("No cash or bank registers found.")

elif st.session_state.active_view == "EDIT_CLIENT":
    st.subheader("✏️ Edit / Rename Client Name & Contact")
    st.caption("Update client details across all registers in Google Sheets.")
    
    if all_existing_customers:
        target_client = st.selectbox("Select Client to Edit", all_existing_customers, key="edit_client_select")
        new_client_name = st.text_input("New Client Name", value=target_client, key="edit_client_new_name")
        curr_p = client_phone_map.get(target_client, "")
        new_client_phone = st.text_input("Client Phone Number", value=curr_p, key="edit_client_new_phone")
        
        if st.button("UPDATE CLIENT DETAILS", type="primary", use_container_width=True):
            with st.spinner("Updating client details..."):
                if new_client_name.strip() and target_client.strip().lower() != new_client_name.strip().lower():
                    rename_client_in_sheets(target_client.strip(), new_client_name.strip())
                if new_client_phone.strip():
                    update_client_phone_in_sheets(new_client_name.strip() if new_client_name.strip() else target_client.strip(), new_client_phone.strip())
                st.cache_data.clear()
                st.success("Client details updated successfully!")
                st.rerun()
    else:
        st.info("No existing clients found to edit.")

else:  # LEDGER
    if customer_name:
        st.subheader(f"📖 Combined Ledger across ALL Registers for `{customer_name}`")
        st.dataframe(customer_master_df, use_container_width=True)
    else:
        st.subheader(f"📖 Current Register `{selected_sheet}` Transactions")
        st.dataframe(active_display_df, use_container_width=True)
