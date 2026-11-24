import hashlib
import hmac
import os
import time

import streamlit as st

import database as db


def _ensure_table():
    conn = db.get_connection()
    conn.execute("""CREATE TABLE IF NOT EXISTS settings (
                        key   TEXT PRIMARY KEY,
                        value TEXT NOT NULL)""")
    conn.commit()
    conn.close()


def _get_setting(key):
    conn = db.get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def _set_setting(key, value):
    conn = db.get_connection()
    conn.execute(
        """INSERT INTO settings (key, value) VALUES (?, ?)
           ON CONFLICT (key) DO UPDATE SET value = excluded.value""",
        (key, value),
    )
    conn.commit()
    conn.close()


def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000).hex()


def _save_password(password):
    salt = os.urandom(16)
    _set_setting("password_salt", salt.hex())
    _set_setting("password_hash", _hash(password, salt))


def _check_password(password):
    salt_hex = _get_setting("password_salt")
    stored = _get_setting("password_hash")
    if not salt_hex or not stored:
        return False
    return hmac.compare_digest(_hash(password, bytes.fromhex(salt_hex)), stored)


def require_login():
    """Call this at the top of every page. Shows a login screen and stops the page
    until the correct password is entered."""
    _ensure_table()

    if st.session_state.get("logged_in"):
        with st.sidebar:
            if st.button("🔒 Log out"):
                st.session_state["logged_in"] = False
                st.rerun()
        return

    if _get_setting("password_hash") is None:
        # First time: ask the user to create a password
        st.title("🔐 Create a password")
        st.write("This password will be asked every time you open the app.")
        with st.form("setup_form"):
            p1 = st.text_input("New password (at least 6 characters)", type="password")
            p2 = st.text_input("Confirm password", type="password")
            ok = st.form_submit_button("Save password")
        if ok:
            if len(p1) < 6:
                st.error("Password must be at least 6 characters.")
            elif p1 != p2:
                st.error("The two passwords do not match.")
            else:
                _save_password(p1)
                st.session_state["logged_in"] = True
                st.rerun()
    else:
        st.title("🔐 Login")
        with st.form("login_form"):
            pw = st.text_input("Password", type="password")
            ok = st.form_submit_button("Log in")
        if ok:
            if _check_password(pw):
                st.session_state["logged_in"] = True
                st.rerun()
            else:
                time.sleep(1)   # slows down password guessing
                st.error("Wrong password.")

    st.stop()   # nothing below this line in the page runs until logged in