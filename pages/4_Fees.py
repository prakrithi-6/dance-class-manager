import datetime

import pandas as pd
import streamlit as st

import database as db

import auth

st.set_page_config(page_title="Fees", page_icon="💰")
db.create_tables()
auth.require_login()
st.title("💰 Fees")

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
today = datetime.date.today()


def month_label(for_month):
    """Turn '2026-11' into 'Nov 2026'."""
    y, m = for_month.split("-")
    return datetime.date(int(y), int(m), 1).strftime("%b %Y")


def months_due(joining_date_text):
    """Months from the joining month up to this month, counting both."""
    if not joining_date_text:
        return 0
    j = datetime.date.fromisoformat(joining_date_text)
    return max(0, (today.year - j.year) * 12 + (today.month - j.month) + 1)


tab_pay, tab_history, tab_pending = st.tabs(
    ["➕ Record payment", "🧾 Payment history", "⚠️ Pending fees"])

# ---------------- TAB 1: RECORD PAYMENT ----------------
with tab_pay:
    status = db.get_fee_status()
    if not status:
        st.write("No students yet. Add students first.")
    else:
        by_id = {s["id"]: s for s in status}
        sid = st.selectbox(
            "Student",
            list(by_id.keys()),
            format_func=lambda i: f'{by_id[i]["name"]} ({by_id[i]["batch"] or "no batch"})',
        )
        s = by_id[sid]

        if s["monthly_fee"] == 0:
            st.warning("This student has no batch, or the batch has no monthly fee set. "
                       "Set it on the Batches and Students pages so pending fees "
                       "can be calculated.")

        with st.form(f"pay_form_{sid}"):
            amount = st.number_input("Amount paid (₹)", min_value=0, step=100,
                                     value=int(s["monthly_fee"]), key=f"amt{sid}")
            paid_on = st.date_input("Date paid", value=today, key=f"pd{sid}")
            col1, col2 = st.columns(2)
            month_name = col1.selectbox("Fee for month", MONTHS,
                                        index=today.month - 1, key=f"pm{sid}")
            year = col2.number_input("Year", min_value=2000, max_value=2100,
                                     value=today.year, step=1, key=f"py{sid}")
            submitted = st.form_submit_button("Save payment")

        if submitted:
            if amount <= 0:
                st.error("Amount must be more than 0.")
            else:
                for_month = f"{int(year)}-{MONTHS.index(month_name) + 1:02d}"
                db.add_payment(sid, amount, paid_on.isoformat(), for_month)
                st.success(f"Saved ₹{amount} for {s['name']} ({month_name} {int(year)}).")

# ---------------- TAB 2: HISTORY ----------------
with tab_history:
    payments = db.get_payments()
    if not payments:
        st.write("No payments recorded yet.")
    else:
        rows = [{
            "Student": p["name"],
            "Amount (₹)": p["amount"],
            "Date paid": p["paid_on"],
            "For month": month_label(p["for_month"]),
        } for p in payments]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
                     height=400)

        st.divider()
        st.write("**Entered a payment by mistake?**")
        pay_by_id = {p["id"]: p for p in payments}
        del_id = st.selectbox(
            "Choose a payment to delete",
            list(pay_by_id.keys()),
            format_func=lambda i: (f'{pay_by_id[i]["name"]} - ₹{pay_by_id[i]["amount"]:.0f} '
                                   f'on {pay_by_id[i]["paid_on"]}'),
            key="del_pay",
        )
        confirm = st.checkbox("Yes, delete this payment", key=f"confirm_pay_{del_id}")
        if st.button("Delete payment", disabled=not confirm):
            db.delete_payment(del_id)
            st.rerun()

# ---------------- TAB 3: PENDING ----------------
with tab_pending:
    status = db.get_fee_status()
    pending_rows = []
    no_fee_count = 0

    for s in status:
        if s["monthly_fee"] == 0:
            no_fee_count += 1
            continue
        m = months_due(s["joining_date"])
        fee_due = m * s["monthly_fee"]
        pending = fee_due - s["total_paid"]
        if pending > 0:
            pending_rows.append({
                "Name": s["name"],
                "Phone": s["phone"] or "—",
                "Batch": s["batch"],
                "Months due": m,
                "Fee due (₹)": fee_due,
                "Paid (₹)": s["total_paid"],
                "Pending (₹)": pending,
            })

    if not pending_rows:
        st.success("No pending fees. 🎉")
    else:
        pending_rows.sort(key=lambda r: r["Pending (₹)"], reverse=True)
        total_pending = sum(r["Pending (₹)"] for r in pending_rows)
        c1, c2 = st.columns(2)
        c1.metric("Students with pending fees", len(pending_rows))
        c2.metric("Total pending", f"₹{total_pending:,.0f}")
        st.dataframe(pd.DataFrame(pending_rows), use_container_width=True,
                     hide_index=True, height=400)

    st.caption("Fee due = months since joining (including this month) × the batch's "
               "monthly fee. Pending = fee due − total paid.")
    if no_fee_count:
        st.caption(f"{no_fee_count} student(s) are not counted because they have no batch "
                   "or their batch fee is ₹0.")