from dotenv import load_dotenv

# Load environment variables from the .env file BEFORE importing database modules
load_dotenv()

import streamlit as st

# Import database session tools and models
from db.database import get_session, check_connection
from db.models import User
from modules.inventory import show_inventory_page
from modules.settings import show_settings_page
from modules.auth import verify_passwordy

# --- Page Configuration ---
st.set_page_config(
    page_title="TheChase POS & Inventory",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Initialize Session State ---
if "db_connected" not in st.session_state:
    st.session_state.db_connected = check_connection()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "current_user" not in st.session_state:
    st.session_state.current_user = None


# --- Helper Functions ---
def login(email, password):
    """
    Query the database to check if the user exists and the password matches.
    (Note: In production, use hashed passwords. We'll set that up soon!)
    """
    try:
        # We need to manually handle the generator from get_session()
        session_gen = get_session()
        session = next(session_gen)

        user = session.query(User).filter(User.email == email).first()

        # Use secure password verification!
        if user and user.is_active and verify_password(password, user.hashed_password):
            st.session_state.logged_in = True
            st.session_state.current_user = {
                "id": user.id,
                "name": user.full_name,
                "role": user.role.value
            }
            st.success(f"Welcome back, {user.full_name}!")
        else:
            st.error("Invalid email or password, or account is inactive.")

    except Exception as e:
        st.error(f"Database error during login: {e}")
    finally:
        # Clean up the session generator
        try:
            next(session_gen)
        except StopIteration:
            pass


def logout():
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.rerun()


# --- UI: Database Warning ---
if not st.session_state.db_connected:
    st.error("⚠️ Could not connect to the database. Please check your credentials.")
    st.stop()

# --- UI: Login Screen ---
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>TheChase POS</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: gray;'>Staff Login</h4>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Log In", use_container_width=True)

            if submit:
                if email and password:
                    login(email, password)
                    st.rerun()
                else:
                    st.warning("Please enter both email and password.")

# --- UI: Main Application (Logged In) ---
else:
    # Sidebar
    with st.sidebar:
        user_info = st.session_state.current_user
        st.markdown(f"**👤 {user_info['name']}**")
        st.caption(f"Role: {user_info['role'].capitalize()}")
        st.button("Logout", on_click=logout, use_container_width=True)

        st.divider()

        # Navigation
        st.subheader("Navigation")
        # You can expand this menu based on the user's role
        menu_options = ["Dashboard", "POS Till", "Active Orders", "Inventory", "Settings"]

        if user_info["role"] in ["waiter", "cashier"]:
            # Restrict menu for lower roles
            menu_options = ["POS Till", "Active Orders"]

        selection = st.radio("Go to", menu_options, label_visibility="collapsed")

    # Main Content Area
    st.title(selection)

    if selection == "Dashboard":
        st.write("Welcome to the main dashboard. High-level metrics will go here.")

    elif selection == "POS Till":
        st.write("This will be the Point of Sale interface where cashiers/waiters ring up items.")

    elif selection == "Active Orders":
        st.write("This will show the Kanban board of orders (Placed -> Served -> Cleared).")

    elif selection == "Inventory":
        show_inventory_page()

    elif selection == "Settings":
        show_settings_page()