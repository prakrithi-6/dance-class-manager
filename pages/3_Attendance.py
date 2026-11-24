import datetime

import pandas as pd
import streamlit as st

import database as db

import auth

st.set_page_config(page_title="Attendance", page_icon="✅")
db.create_tables()
auth.require_login()
st.title("✅ Attendance")

batches = db.get_all_batches()
if not batches:
    st.info("No batches yet. Add batches on the Batches page first.")
    st.stop()

by_id = {b["id"]: b for b in batches}
batch_ids = list(by_id.keys())


def batch_label(i):
    return by_id[i]["name"]


tab_mark, tab_view = st.tabs(["📝 Mark attendance", "📊 Attendance summary"])

# ---------------- TAB 1: MARK ----------------
with tab_mark:
    batch_id = st.selectbox("Batch", batch_ids, format_func=batch_label, key="mark_batch")
    date = st.date_input("Date", value=datetime.date.today(), key="mark_date")
    date_text = date.isoformat()

    students = db.get_students_in_batch(batch_id)

    if not students:
        st.warning("This batch has no students yet. Assign students on the Students page.")
    else:
        saved = db.get_attendance(batch_id, date_text)
        if saved:
            st.info("Attendance is already saved for this date. "
                    "You can change it and save again.")
        else:
            st.caption("Everyone starts as present. Untick the students who are absent.")

        # Students not saved yet default to present (True)
        df = pd.DataFrame(
            {
                "Name": [s["name"] for s in students],
                "Present": [bool(saved.get(s["id"], 1)) for s in students],
            },
            index=[s["id"] for s in students],
        )

        edited = st.data_editor(
            df,
            hide_index=True,
            disabled=["Name"],
            use_container_width=True,
            key=f"att_{batch_id}_{date_text}",
        )

        present_count = int(edited["Present"].sum())
        st.write(f"Present: **{present_count}** / {len(students)}")

        if st.button("💾 Save attendance"):
            records = [(sid, bool(p)) for sid, p in edited["Present"].items()]
            db.save_attendance(batch_id, date_text, records)
            st.success(f"Attendance saved for {batch_label(batch_id)} on "
                       f"{date.strftime('%d %b %Y')}.")

# ---------------- TAB 2: SUMMARY ----------------
with tab_view:
    view_batch = st.selectbox("Batch", batch_ids, format_func=batch_label, key="view_batch")
    summary = db.get_attendance_summary(view_batch)

    if not summary:
        st.write("This batch has no students yet.")
    else:
        rows = []
        for r in summary:
            percent = round(r["attended"] * 100 / r["total"]) if r["total"] else None
            rows.append({
                "Name": r["name"],
                "Classes marked": r["total"],
                "Attended": r["attended"],
                "Attendance %": f"{percent}%" if percent is not None else "—",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)