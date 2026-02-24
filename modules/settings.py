import streamlit as st
import pandas as pd
from db.database import get_session
from db.models import User, UserRole
from modules.auth import hash_password


def show_settings_page():
    st.header("⚙️ Settings & Staff Management")

    # Security check: Only admins can view this page
    if st.session_state.current_user.get("role") != "admin":
        st.error("🚫 Access Denied: You must be an Administrator to view this page.")
        return

    tab1, tab2, tab3 = st.tabs(["Staff Roster", "Create New User", "Delete User"])

    session_gen = get_session()
    session = next(session_gen)

    try:
        # --- TAB 1: USER LIST ---
        with tab1:
            st.subheader("Current Staff Accounts")
            users = session.query(User).all()

            if users:
                data = []
                for u in users:
                    data.append({
                        "Name": u.full_name,
                        "Email": u.email,
                        "Role": u.role.value.capitalize(),
                        "Status": "✅ Active" if u.is_active else "❌ Inactive"
                    })
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No users found.")

        # --- TAB 2: ADD NEW USER ---
        with tab2:
            st.subheader("Add New Staff Member")

            with st.form("add_user_form", clear_on_submit=True):
                col1, col2 = st.columns(2)

                with col1:
                    full_name = st.text_input("Full Name*")
                    email = st.text_input("Email Address*")

                with col2:
                    # Automatically pull the roles from our SQLAlchemy Enum
                    role = st.selectbox("Role*", options=[r.value for r in UserRole])
                    password = st.text_input("Temporary Password*", type="password")

                submit = st.form_submit_button("Create User", use_container_width=True)

                if submit:
                    if not full_name.strip() or not email.strip() or not password.strip():
                        st.error("Please fill in all required fields.")
                    else:
                        existing_user = session.query(User).filter_by(email=email.strip()).first()
                        if existing_user:
                            st.error("A user with this email address already exists.")
                        else:
                            new_user = User(
                                full_name=full_name.strip(),
                                email=email.strip(),
                                role=role,
                                hashed_password=hash_password(password)  # Securely hash!
                            )
                            session.add(new_user)
                            session.commit()
                            st.success(f"User {full_name} successfully created!")
                            st.rerun()

        # --- TAB 3: DELETE USER ---
        with tab3:
            st.subheader("Remove Staff Member")
            st.warning("⚠️ Deleting a user is permanent and cannot be undone.")

            # Get all users except the currently logged-in admin (prevent self-deletion)
            other_users = session.query(User).filter(User.id != st.session_state.current_user["id"]).all()

            if not other_users:
                st.info("No other users to delete.")
            else:
                with st.form("delete_user_form"):
                    user_to_delete = st.selectbox(
                        "Select User to Delete",
                        options=[u.id for u in other_users],
                        format_func=lambda x: next(f"{u.full_name} ({u.email})" for u in other_users if u.id == x)
                    )

                    # Checkbox for extra safety
                    confirm = st.checkbox("I confirm I want to delete this user.")

                    submit_delete = st.form_submit_button("Delete User", type="primary")

                    if submit_delete:
                        if confirm:
                            user = session.query(User).filter(User.id == user_to_delete).first()
                            session.delete(user)
                            session.commit()
                            st.success(f"User deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Please check the confirmation box to delete the user.")

    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass