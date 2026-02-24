import streamlit as st
import pandas as pd
import plotly.express as px
from db.database import get_session
from db.models import Product, Category, Inventory


def show_inventory_page():
    st.header("📦 Inventory Management")

    # Organize the screen into tabs
    tab1, tab2, tab3 = st.tabs(["Product Overview", "Add New Product", "Manage Categories"])

    # Grab a database session
    session_gen = get_session()
    session = next(session_gen)

    try:
        # --- TAB 1: PRODUCT LIST & VISUALS ---
        with tab1:
            st.subheader("Current Inventory Dashboard")
            products = session.query(Product).all()

            if products:
                # Build a list of dictionaries to display nicely in a Streamlit dataframe
                data = []
                for p in products:
                    data.append({
                        "SKU": p.sku,
                        "Name": p.name,
                        "Category": p.category.name if p.category else "N/A",
                        "Price (KSH)": float(p.unit_price_ksh),
                        "Price (UGX)": float(p.unit_price_ugx),
                        "Stock": float(p.inventory.quantity_on_hand) if p.inventory else 0.0
                    })
                df = pd.DataFrame(data)

                # Top Level Metrics
                col1, col2, col3 = st.columns(3)
                total_products = len(df)
                total_stock = df["Stock"].sum()
                low_stock_items = len(df[df["Stock"] < 10])

                col1.metric("Total Unique Products", total_products)
                col2.metric("Total Items in Stock", f"{total_stock:,.0f}")
                col3.metric("Low Stock Alerts (<10)", low_stock_items, delta_color="inverse")

                st.divider()

                # Visualizations
                st.write("#### Inventory Insights")
                chart_col1, chart_col2 = st.columns(2)

                with chart_col1:
                    # Pie chart for Stock Distribution by Category
                    cat_stock = df.groupby("Category")["Stock"].sum().reset_index()
                    fig_pie = px.pie(
                        cat_stock,
                        values='Stock',
                        names='Category',
                        title='Stock Distribution by Category',
                        hole=0.4
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

                with chart_col2:
                    # Bar chart for Top Products by Stock
                    top_stock = df.nlargest(10, 'Stock').sort_values('Stock', ascending=True)
                    fig_bar = px.bar(
                        top_stock,
                        x='Stock',
                        y='Name',
                        orientation='h',
                        title='Top 10 Products by Stock Volume',
                        color='Category'
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

                st.divider()

                # Enhanced Dataframe view
                st.write("#### Detailed Product List")
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Stock": st.column_config.ProgressColumn(
                            "Stock Level",
                            help="Current quantity on hand",
                            format="%f",
                            min_value=0,
                            max_value=float(df['Stock'].max()) if not df.empty else 100,
                        ),
                        "Price (KSH)": st.column_config.NumberColumn(format="KSh %.2f"),
                        "Price (UGX)": st.column_config.NumberColumn(format="UGX %.2f"),
                    }
                )
            else:
                st.info("No products found. Head over to the 'Add New Product' tab to create some!")

        # --- TAB 3: CATEGORIES ---
        # We process Categories before Products because Products depend on them
        with tab3:
            st.subheader("Manage Categories")

            categories = session.query(Category).all()

            col_cat_list, col_cat_form = st.columns([1.5, 1])

            with col_cat_list:
                st.write("**Existing Categories**")
                if categories:
                    # Create a richer view of categories including product counts
                    cat_data = []
                    for c in categories:
                        prod_count = session.query(Product).filter(Product.category_id == c.id).count()
                        cat_data.append({
                            "Category Name": c.name,
                            "Description": c.description or "-",
                            "Products Linked": prod_count
                        })
                    st.dataframe(pd.DataFrame(cat_data), use_container_width=True, hide_index=True)
                else:
                    st.info("No categories exist yet.")

            with col_cat_form:
                st.write("**Add a New Category**")
                with st.form("add_category_form", clear_on_submit=True):
                    cat_name = st.text_input("Category Name*", placeholder="e.g., Whiskey, Soft Drinks")
                    cat_desc = st.text_area("Description (Optional)")
                    submit_cat = st.form_submit_button("Add Category", use_container_width=True)

                    if submit_cat:
                        if cat_name.strip():
                            # Case-insensitive duplicate check
                            existing = session.query(Category).filter(Category.name.ilike(cat_name.strip())).first()
                            if existing:
                                st.error(f"Category '{existing.name}' already exists.")
                            else:
                                new_cat = Category(name=cat_name.strip(), description=cat_desc.strip())
                                session.add(new_cat)
                                session.commit()
                                st.success(f"Category '{cat_name}' added!")
                                st.rerun()
                        else:
                            st.error("Category name is required.")

        # --- TAB 2: ADD PRODUCT ---
        with tab2:
            st.subheader("Add New Product")

            if not categories:
                st.warning(
                    "⚠️ You need to add at least one Category (in the Manage Categories tab) before adding a Product.")
            else:
                with st.form("add_product_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)

                    with col1:
                        sku = st.text_input("SKU (e.g., BEV-001)*")
                        name = st.text_input("Product Name*")
                        # Dropdown mapping category names to their IDs
                        cat_id = st.selectbox(
                            "Category*",
                            options=[c.id for c in categories],
                            format_func=lambda x: next(c.name for c in categories if c.id == x)
                        )
                        barcode = st.text_input("Barcode (Optional)")

                    with col2:
                        price_ksh = st.number_input("Selling Price (KSH)*", min_value=0.0, format="%.2f")
                        price_ugx = st.number_input("Selling Price (UGX)*", min_value=0.0, format="%.2f")
                        cost_ksh = st.number_input("Cost Price (KSH)*", min_value=0.0, format="%.2f")
                        initial_stock = st.number_input("Initial Stock Quantity", min_value=0.0, step=1.0)

                    submit_prod = st.form_submit_button("Save Product", use_container_width=True)

                    if submit_prod:
                        if not sku.strip() or not name.strip():
                            st.error("SKU and Name are required.")
                        else:
                            exists = session.query(Product).filter_by(sku=sku.strip()).first()
                            if exists:
                                st.error(f"A product with SKU '{sku}' already exists.")
                            else:
                                new_prod = Product(
                                    sku=sku.strip(),
                                    name=name.strip(),
                                    category_id=cat_id,
                                    unit_price_ksh=price_ksh,
                                    unit_price_ugx=price_ugx,
                                    cost_price_ksh=cost_ksh,
                                    barcode=barcode.strip() if barcode else None
                                )
                                session.add(new_prod)
                                session.flush()  # Flush to generate the new Product ID

                                # Immediately create the associated inventory record
                                new_inv = Inventory(
                                    product_id=new_prod.id,
                                    quantity_on_hand=initial_stock
                                )
                                session.add(new_inv)
                                session.commit()

                                st.success(f"Product '{name}' added successfully!")
                                st.rerun()
    finally:
        # Safely close the session
        try:
            next(session_gen)
        except StopIteration:
            pass