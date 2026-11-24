import streamlit as st
import database as db
import auth

st.set_page_config(page_title="Dance Class Manager", page_icon="💃")

db.create_tables()   # makes sure the database is ready
auth.require_login()
st.title("💃 Dance Class Manager")
st.write("Welcome! Use the menu on the left to open a page.")
st.info("Students page is ready. Batches, Attendance and Fees will be added step by step.")