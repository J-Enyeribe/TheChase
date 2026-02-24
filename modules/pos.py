import streamlit as st
import uuid
from decimal import Decimal
from contextlib import contextmanager

# Assuming these exist in your project structure
from db.database import get_session
from db.models import Product, Category, Order, OrderItem, Transaction, TransactionItem, Inventory, User


# =========================================================
# 1. UI CONFIGURATION & CSS INJECTION
# =========================================================
def inject_custom_css():
    """Injects custom CSS to style the POS interface with a luxury dark/gold theme."""
    st.markdown("""
    <style>
        /* General UI Cleanup & Full Width */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {background-color: transparent !important;}

        .main .block-container {
            max-width: 99% !important;
            padding: 0.5rem 1rem 0rem 1rem !important;
        }

        /* Gold & Black Typography */
        h1, h2, h3 {
            color: #D4AF37 !important;
            font-weight: 300 !important;
            letter-spacing: 1px;
            margin-top: 0px !important;
            margin-bottom: 10px !important;
        }

        p, div, span, label {
            color: #E0E0E0;
        }

        /* Global Button Tweaks */
        .stButton>button { 
            height: auto; 
            padding: 10px 5px;
            border-radius: 8px;
            border: 1px solid #D4AF37;
            background-color: #1A1A1A;
            color: #D4AF37;
            font-weight: bold;
            transition: all 0.3s ease;
        }

        .stButton>button:hover {
            background-color: #D4AF37;
            color: #000000;
            border-color: #D4AF37;
        }

        .stButton>button:disabled {
            border: 1px solid #555555;
            color: #888888;
            background-color: #222222;
            cursor: not-allowed;
        }

        /* Layout Tweaks */
        .stSelectbox { margin-bottom: -15px !important; }

        .cart-container {
            background-color: #111111;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #333333;
            height: 100%;
        }

        [data-testid="stMetricValue"] {
            color: #D4AF37 !important;
            font-size: 2rem !important;
        }
    </style>
    """, unsafe_allow_html=True)


# =========================================================
# 2. STATE MANAGEMENT & CART LOGIC
# =========================================================
def init_pos_state():
    """Initialize necessary Streamlit session variables."""
    if 'cart' not in st.session_state:
        st.session_state.cart = []
    if 'currency_code' not in st.session_state:
        st.session_state.currency_code = 'KES'


def add_to_cart(product: Product):
    """Adds a product to the cart or increments its quantity if it exists."""
    default_pref = "Warm"

    # Check for exact match (Product ID + Preference)
    for item in st.session_state.cart:
        if item['product_id'] == product.id and item['pref'] == default_pref:
            item['qty'] += 1
            st.toast(f"Added another {product.name} ({default_pref})")
            return

    # Add new item
    st.session_state.cart.append({
        "cart_id": str(uuid.uuid4()),
        "product_id": product.id,
        "name": product.name,
        "price_kes": float(product.unit_price_ksh),
        "price_ugx": float(product.unit_price_ugx),
        "qty": 1,
        "pref": default_pref
    })
    st.toast(f"Added {product.name} ({default_pref})")


def consolidate_cart():
    """Merges cart items that share the same product_id and preference."""
    new_cart = []
    for item in st.session_state.cart:
        found = False
        for existing in new_cart:
            if existing['product_id'] == item['product_id'] and existing['pref'] == item['pref']:
                existing['qty'] += item['qty']
                found = True
                break
        if not found:
            new_cart.append(item)
    st.session_state.cart = new_cart


def update_item_pref(cart_id: str):
    """Callback triggered when the preference selectbox changes."""
    new_pref = st.session_state[f"pref_widget_{cart_id}"]
    for item in st.session_state.cart:
        if item['cart_id'] == cart_id:
            item['pref'] = new_pref
            break
    consolidate_cart()


def remove_from_cart(cart_id: str):
    """Removes a specific item from the cart by its unique cart UI ID."""
    st.session_state.cart = [item for item in st.session_state.cart if item['cart_id'] != cart_id]


def clear_cart():
    """Empties the entire cart."""
    st.session_state.cart = []


# =========================================================
# 3. DATABASE CHECKOUT TRANSACTION
# =========================================================
def process_checkout(session) -> bool:
    """Processes the cart items, creates orders/transactions, and updates inventory."""
    if not st.session_state.cart:
        st.error("Cart is empty!")
        return False

    try:
        # 1. Identify Cashier
        cashier_id = st.session_state.get('user_id')
        if not cashier_id:
            cashier = session.query(User).filter_by(role="cashier").first()
            if not cashier:
                st.error("No cashier found in database. Cannot process order.")
                return False
            cashier_id = cashier.id

        # 2. Setup Order Totals and References
        curr = st.session_state.currency_code
        curr_key = f"price_{curr.lower()}"
        subtotal = sum(item['qty'] * item[curr_key] for item in st.session_state.cart)

        order_ref = f"ORD-{str(uuid.uuid4())[:8].upper()}"
        txn_ref = f"TXN-{str(uuid.uuid4())[:8].upper()}"

        # 3. Create Order Record
        new_order = Order(
            order_number=order_ref,
            currency=curr,
            status="cleared",
            placed_by_id=cashier_id,
            served_by_id=cashier_id,
            cleared_by_id=cashier_id,
            subtotal=Decimal(subtotal),
            grand_total=Decimal(subtotal)
        )
        session.add(new_order)
        session.flush()

        # 4. Create Transaction Record
        new_tx = Transaction(
            receipt_number=txn_ref,
            order_id=new_order.id,
            cashier_id=cashier_id,
            currency=curr,
            status="completed",
            subtotal=Decimal(subtotal),
            grand_total=Decimal(subtotal),
            amount_paid=Decimal(subtotal),
            change_returned=Decimal(0.0)
        )
        session.add(new_tx)
        session.flush()

        # 5. Process Individual Items
        for item in st.session_state.cart:
            unit_price = Decimal(item[curr_key])
            quantity = item['qty']
            line_total = quantity * unit_price

            session.add(OrderItem(
                order_id=new_order.id,
                product_id=item['product_id'],
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total
            ))

            session.add(TransactionItem(
                transaction_id=new_tx.id,
                product_id=item['product_id'],
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total
            ))

            # Deduct Inventory
            inv = session.query(Inventory).filter_by(product_id=item['product_id']).first()
            if inv:
                inv.quantity_on_hand -= Decimal(quantity)

        # 6. Commit everything atomically
        session.commit()
        st.success(f"✅ Payment successful! Receipt: {txn_ref}")
        clear_cart()
        return True

    except Exception as e:
        session.rollback()
        st.error(f"Checkout failed: {e}")
        return False


# =========================================================
# 4. UI COMPONENTS
# =========================================================
def render_header():
    """Renders the top title and currency selector."""
    c1, c2 = st.columns([3, 1])
    with c1:
        st.title("💠 Command Center")
    with c2:
        current_index = 0 if st.session_state.currency_code == "KES" else 1
        st.session_state.currency_code = st.radio(
            "Currency", ["KES", "UGX"], horizontal=True, index=current_index
        )
    st.divider()


def render_product_grid(db_session):
    """Renders the categories and product buttons."""
    categories = db_session.query(Category).all()
    cat_names = ["All Items"] + [c.name for c in categories]
    tabs = st.tabs(cat_names)

    curr_lower = st.session_state.currency_code.lower()

    for i, tab in enumerate(tabs):
        with tab:
            # Build Base Query
            query = db_session.query(Product).filter(
                (Product.is_active == True) | (Product.is_active.is_(None))
            )

            # Filter by Category if not "All Items"
            if i > 0:
                query = query.filter(Product.category_id == categories[i - 1].id)

            products = query.all()

            if not products:
                st.info("No products found in this category.")
                continue

            # Render 4-Column Grid
            pcols = st.columns(4)
            for idx, p in enumerate(products):
                col = pcols[idx % 4]
                with col:
                    price = float(p.unit_price_ksh) if curr_lower == 'kes' else float(p.unit_price_ugx)
                    stock = p.inventory.quantity_on_hand if p.inventory else 0
                    is_oos = stock <= 0

                    if is_oos:
                        label = f"❌ {p.name}\nSOLD OUT"
                    else:
                        label = f"{p.name}\n{st.session_state.currency_code} {price:,.0f}"

                    # Unique keys per tab to prevent Streamlit component ID clashes
                    btn_key = f"prod_{p.id}_tab_{i}"

                    if st.button(label, key=btn_key, disabled=is_oos, use_container_width=True):
                        add_to_cart(p)
                        st.rerun()


def render_cart_section(db_session):
    """Renders the right-side cart panel and handles checkout."""
    st.markdown('<div class="cart-container">', unsafe_allow_html=True)
    st.subheader("🛒 Current Order")

    if not st.session_state.cart:
        st.info("Cart is empty.")
    else:
        curr = st.session_state.currency_code
        curr_key = f"price_{curr.lower()}"
        grand_total = 0

        # Render Cart Items
        for item in st.session_state.cart:
            line_total = item['qty'] * item[curr_key]
            grand_total += line_total

            ci1, ci2, ci3 = st.columns([5, 3, 1])
            with ci1:
                st.write(f"**{item['qty']}x** {item['name']}")
                st.selectbox(
                    "Preference",
                    ["Warm", "Cold", "Mixer", "Standard"],
                    index=["Warm", "Cold", "Mixer", "Standard"].index(item['pref']),
                    key=f"pref_widget_{item['cart_id']}",
                    on_change=update_item_pref,
                    args=(item['cart_id'],),
                    label_visibility="collapsed"
                )
            with ci2:
                st.write(f"{line_total:,.0f}")
            with ci3:
                if st.button("✖", key=f"rm_{item['cart_id']}", help="Remove item"):
                    remove_from_cart(item['cart_id'])
                    st.rerun()

            st.write("")  # Spacer

        # Totals & Action Buttons
        st.divider()
        st.metric("Total Due", f"{curr} {grand_total:,.0f}")

        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("🗑️ Clear", use_container_width=True):
                clear_cart()
                st.rerun()
        with btn_c2:
            if st.button("💳 Pay", type="primary", use_container_width=True):
                if process_checkout(db_session):
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# 5. MAIN EXECUTION (ENTRY POINT)
# =========================================================
@contextmanager
def manage_db_session():
    """Safe wrapper for FastAPI dependency-style generators to use in a with block."""
    session_gen = get_session()
    db_session = next(session_gen)
    try:
        yield db_session
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass


def show_pos_page():
    """Main view compilation."""
    st.set_page_config(page_title="Command Center", layout="wide")  # Added missing config
    inject_custom_css()
    init_pos_state()

    render_header()

    # Database boundary
    with manage_db_session() as db_session:
        pos_col, cart_col = st.columns([7, 3])

        with pos_col:
            render_product_grid(db_session)

        with cart_col:
            render_cart_section(db_session)


if __name__ == "__main__":
    show_pos_page()