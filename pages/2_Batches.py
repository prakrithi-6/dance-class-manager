import datetime

import pandas as pd
import streamlit as st

import database as db

import auth

st.set_page_config(page_title="Batches", page_icon="🗓️")
db.create_tables()
auth.require_login()
st.title("🗓️ Batches")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"]
STANDARD_BATCHES = ["Junior", "Senior", "Pre Vidwat", "Vidwat"]


def format_time(t):
    """Turn '17:30' into '05:30 PM' for display. Empty stays empty."""
    if not t:
        return "—"
    return datetime.time.fromisoformat(t).strftime("%I:%M %p")


# Names already in use (to stop duplicates)
existing_names = [b["name"].lower() for b in db.get_all_batches()]

tab_list, tab_add, tab_edit, tab_delete = st.tabs(
    ["📋 Batch list", "➕ Add batch", "✏️ Edit batch", "🗑️ Delete batch"])
# ---------------- TAB 1: LIST ----------------
with tab_list:
    batches = db.get_batches_with_counts()
    if not batches:
        st.write("No batches yet. Use the button above or the Add batch tab.")
    else:
        rows = []
        for b in batches:
            rows.append({
                "Batch": b["name"],
                "Class days": b["day"] or "—",
                "Time": format_time(b["time"]),
                "Monthly fee (₹)": b["monthly_fee"],
                "Students": b["student_count"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ---------------- TAB 2: ADD ----------------
with tab_add:
    with st.form("add_batch_form", clear_on_submit=True):
        name = st.text_input("Batch name (e.g. Junior)")
        fee = st.number_input("Monthly fee (₹)", min_value=0, step=100, value=0)
        st.write("Class schedule (optional)")
        days = st.multiselect("Class days", DAYS)
        use_time = st.checkbox("Set a class time")
        class_time = st.time_input("Class time", value=datetime.time(17, 0), step=900)
        submitted = st.form_submit_button("Save batch")

    if submitted:
        name = name.strip()
        if name == "":
            st.error("Please enter the batch name.")
        elif name.lower() in existing_names:
            st.error("A batch with this name already exists.")
        else:
            days_text = ", ".join(d for d in DAYS if d in days)
            time_text = class_time.strftime("%H:%M") if use_time else ""
            db.add_batch(name, days_text, time_text, fee)
            st.success(f"Batch '{name}' was added.")

# ---------------- TAB 3: EDIT ----------------
with tab_edit:
    batches = db.get_batches_with_counts()
    if not batches:
        st.write("No batches to edit yet.")
    else:
        batch_ids = [b["id"] for b in batches]
        by_id = {b["id"]: b for b in batches}

        chosen_id = st.selectbox(
            "Choose a batch to edit",
            batch_ids,
            format_func=lambda i: by_id[i]["name"],
        )
        b = by_id[chosen_id]

        current_days = [d for d in (b["day"] or "").split(", ") if d in DAYS]
        has_time = bool(b["time"])
        current_time = (datetime.time.fromisoformat(b["time"])
                        if has_time else datetime.time(17, 0))

        with st.form(f"edit_batch_form_{chosen_id}"):
            new_name = st.text_input("Batch name", value=b["name"], key=f"bn{chosen_id}")
            new_fee = st.number_input("Monthly fee (₹)", min_value=0, step=100,
                                      value=int(b["monthly_fee"] or 0), key=f"bf{chosen_id}")
            st.write("Class schedule (optional)")
            new_days = st.multiselect("Class days", DAYS, default=current_days,
                                      key=f"bd{chosen_id}")
            new_use_time = st.checkbox("Set a class time", value=has_time,
                                       key=f"bc{chosen_id}")
            new_time = st.time_input("Class time", value=current_time, step=900,
                                     key=f"bt{chosen_id}")
            saved = st.form_submit_button("Update batch")

        if saved:
            new_name = new_name.strip()
            other_names = [x["name"].lower() for x in batches if x["id"] != chosen_id]
            if new_name == "":
                st.error("Batch name cannot be empty.")
            elif new_name.lower() in other_names:
                st.error("Another batch already has this name.")
            else:
                days_text = ", ".join(d for d in DAYS if d in new_days)
                time_text = new_time.strftime("%H:%M") if new_use_time else ""
                db.update_batch(chosen_id, new_name, days_text, time_text, new_fee)
                st.success("Batch updated. Open the Batch list tab to see the change.")

                # ---------------- TAB 4: DELETE ----------------
with tab_delete:
    batches = db.get_batches_with_counts()
    if not batches:
        st.write("No batches to delete.")
    else:
        by_id = {b["id"]: b for b in batches}
        del_id = st.selectbox(
            "Choose a batch to delete",
            list(by_id.keys()),
            format_func=lambda i: f'{by_id[i]["name"]} ({by_id[i]["student_count"]} students)',
            key="del_select",
        )
        d = by_id[del_id]

        if d["student_count"] > 0:
            st.warning(f"'{d['name']}' has {d['student_count']} student(s), so it cannot "
                       "be deleted. Move them to another batch on the Students page first.")
        else:
            confirm = st.checkbox(f"Yes, I want to delete '{d['name']}'",
                                  key=f"confirm_{del_id}")
            if st.button("Delete batch", disabled=not confirm):
                ok, msg = db.delete_batch(del_id)
                if ok:
                    st.toast(msg)
                    st.rerun()          # reload so the lists update
                else:
                    st.error(msg)