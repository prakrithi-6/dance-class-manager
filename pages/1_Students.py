import datetime

import pandas as pd
import streamlit as st

import database as db

import auth

st.set_page_config(page_title="Students", page_icon="🎓")
db.create_tables()
auth.require_login()
st.title("🎓 Students")

# Load batches once; we need them for the dropdowns
batches = db.get_all_batches()
batch_ids = [None] + [b["id"] for b in batches]            # None = no batch
batch_names = {b["id"]: b["name"] for b in batches}


def show_batch(batch_id):
    """Text shown in the dropdown for a batch id."""
    return "Not assigned" if batch_id is None else batch_names[batch_id]


def phone_is_valid(phone):
    """Phone is optional, but if given it must be 10 digits."""
    return phone == "" or (phone.isdigit() and len(phone) == 10)


if not batches:
    st.info("No batches exist yet. You can still add students now and "
            "assign batches after we build the Batches page (Step 2).")

tab_list, tab_add, tab_edit = st.tabs(["📋 Student list", "➕ Add student", "✏️ Edit student"])

# ---------------- TAB 1: LIST ----------------
with tab_list:
    students = db.get_all_students()
    if not students:
        st.write("No students yet. Add one in the next tab.")
    else:
        # Filter choices: "all", each batch id, or "none" (no batch)
        filter_options = ["all"] + [b["id"] for b in batches] + ["none"]

        def show_filter(option):
            if option == "all":
                return "All batches"
            if option == "none":
                return "Not assigned"
            return batch_names[option]

        col1, col2 = st.columns(2)
        chosen_filter = col1.selectbox("Show batch", filter_options,
                                       format_func=show_filter)
        search = col2.text_input("Search by name or phone").strip().lower()

        # Apply the batch filter
        if chosen_filter == "all":
            filtered = list(students)
        elif chosen_filter == "none":
            filtered = [s for s in students if s["batch_id"] is None]
        else:
            filtered = [s for s in students if s["batch_id"] == chosen_filter]

        # Apply the search
        if search:
            filtered = [s for s in filtered
                        if search in s["name"].lower()
                        or search in (s["phone"] or "")]

        if not filtered:
            st.write("No students match this filter.")
        else:
            df = pd.DataFrame([dict(s) for s in filtered])
            df = df[["name", "phone", "batch", "joining_date"]]
            df.columns = ["Name", "Phone", "Batch", "Joining date"]
            df["Batch"] = df["Batch"].fillna("Not assigned")
            st.dataframe(df, use_container_width=True, hide_index=True, height=400)

        st.caption(f"Showing {len(filtered)} of {len(students)} students")

# ---------------- TAB 2: ADD ----------------
with tab_add:
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("Student name")
        phone = st.text_input("Phone number (10 digits)")
        batch_id = st.selectbox("Batch", batch_ids, format_func=show_batch)
        joining_date = st.date_input("Joining date", value=datetime.date.today())
        submitted = st.form_submit_button("Save student")

    if submitted:
        name = name.strip()
        phone = phone.strip()
        if name == "":
            st.error("Please enter the student's name.")
        elif not phone_is_valid(phone):
            st.error("Phone number must be exactly 10 digits.")
        else:
            db.add_student(name, phone, batch_id, joining_date.isoformat())
            st.success(f"{name} was added.")

# ---------------- TAB 3: EDIT ----------------
with tab_edit:
    students = db.get_all_students()
    if not students:
        st.write("No students to edit yet.")
    else:
        student_ids = [s["id"] for s in students]
        by_id = {s["id"]: s for s in students}

        chosen_id = st.selectbox(
            "Choose a student to edit",
            student_ids,
            format_func=lambda i: f'{by_id[i]["name"]} ({by_id[i]["phone"] or "no phone"})',
        )
        s = by_id[chosen_id]

        # A batch may have been removed, so fall back to "Not assigned"
        current_batch = s["batch_id"] if s["batch_id"] in batch_ids else None

        # Keys include the student id so the form refreshes when you pick someone else
        with st.form(f"edit_form_{chosen_id}"):
            new_name = st.text_input("Student name", value=s["name"], key=f"n{chosen_id}")
            new_phone = st.text_input("Phone number (10 digits)", value=s["phone"] or "",
                                      key=f"p{chosen_id}")
            new_batch = st.selectbox("Batch", batch_ids, format_func=show_batch,
                                     index=batch_ids.index(current_batch),
                                     key=f"b{chosen_id}")
            new_date = st.date_input(
                "Joining date",
                value=datetime.date.fromisoformat(s["joining_date"]),
                key=f"d{chosen_id}",
            )
            saved = st.form_submit_button("Update student")

        if saved:
            new_name = new_name.strip()
            new_phone = new_phone.strip()
            if new_name == "":
                st.error("Name cannot be empty.")
            elif not phone_is_valid(new_phone):
                st.error("Phone number must be exactly 10 digits.")
            else:
                db.update_student(chosen_id, new_name, new_phone, new_batch,
                                  new_date.isoformat())
                st.success("Student updated. Open the Student list tab to see the change.")