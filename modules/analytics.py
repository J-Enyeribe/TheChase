import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from db.database import get_session
from db.models import Transaction, TransactionItem, Product, Category, Inventory, User, Payment

# Professional Executive Gold Palette
GOLD_PALETTE = ["#D4AF37", "#C5A028", "#A6801E", "#876514", "#FFD700", "#DAA520"]
GREEN_PALETTE = ["#00CC96", "#00A87B", "#008560"]
DANGER_COLOR = "#FF4C4C"
WARNING_COLOR = "#FFA500"


def show_analytics_page():
    """
    High-Impact Executive Analytics Hub.
    Designed as a unified Command Center: KPIs -> Trends -> Product Intel -> Operations.
    """
    session_gen = get_session()
    session = next(session_gen)

    try:
        # =========================================================
        # 1. PAGE CONFIG & CSS STYLING (Merged & Upgraded)
        # =========================================================
        st.markdown("""
        <style>
            /* Main Glow Cards for KPIs */
            .glow-card {
                background: linear-gradient(145deg, #1e2124 0%, #111214 100%);
                border: 1px solid rgba(212, 175, 55, 0.3);
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 0 15px rgba(212, 175, 55, 0.1);
                text-align: center;
                transition: transform 0.2s ease-in-out;
            }
            .glow-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 0 20px rgba(212, 175, 55, 0.2);
            }
            .metric-label { color: #a3a3a3; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
            .metric-val { color: #D4AF37; font-size: 2rem; font-weight: 700; margin-top: 8px; text-shadow: 0 0 10px rgba(212, 175, 55, 0.3); }

            /* Stock Watchlist Tiles */
            .stock-tile {
                padding: 12px 16px; 
                border-radius: 8px; 
                background: rgba(255,255,255,0.03); 
                margin-bottom: 10px; 
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.95rem;
            }
            .stock-danger { border-left: 4px solid #FF4C4C; background: linear-gradient(90deg, rgba(255,76,76,0.15) 0%, transparent 100%); }
            .stock-warning { border-left: 4px solid #FFA500; background: linear-gradient(90deg, rgba(255,165,0,0.15) 0%, transparent 100%); }

            /* Section Headers */
            .section-header {
                color: #ffffff;
                font-size: 1.2rem;
                font-weight: 600;
                margin-bottom: 15px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
                padding-bottom: 8px;
                margin-top: 25px;
            }

            /* Custom Radio Buttons (Global Currency Selector) */
            div[role="radiogroup"] { flex-direction: row; gap: 8px; justify-content: flex-end; }
            div[role="radiogroup"] label > div:first-child { display: none; }
            div[role="radiogroup"] label { 
                background-color: #1E1E1E !important; 
                padding: 8px 24px !important; 
                border-radius: 6px !important; 
                border: 1px solid #333 !important; 
                cursor: pointer;
                transition: all 0.2s ease-in-out;
                font-size: 0.95rem;
                color: #E0E0E0 !important;
                display: flex;
                align-items: center;
                justify-content: center;
                min-width: 80px; 
            }
            div[role="radiogroup"] label:hover { border-color: #666 !important; background-color: #2D2D2D !important; }
            div[role="radiogroup"] label:has(input:checked) {
                background-color: #D4AF37 !important; 
                color: black !important; 
                border-color: #D4AF37 !important;
                font-weight: 700;
                box-shadow: 0 0 10px rgba(212, 175, 55, 0.4);
            }
            div[role="radiogroup"] input:checked + div { color: #000; font-weight: bold; }
        </style>
        """, unsafe_allow_html=True)

        # =========================================================
        # 2. HEADER & GLOBAL CONTROLS
        # =========================================================
        col_title, col_curr = st.columns([2, 1], vertical_alignment="center")
        with col_title:
            st.markdown("<h2>📊 Command Center</h2>", unsafe_allow_html=True)
            st.markdown(
                "<p style='color: #8b949e; margin-top: -10px;'>Insights to optimize stock, staffing, and sales.</p>",
                unsafe_allow_html=True)
        with col_curr:
            selected_currency = st.radio("Global Currency", ["KSH", "UGX"], horizontal=True,
                                         label_visibility="collapsed")

        # --- TIMELINE CONTROLS ---
        time_frame = st.segmented_control(
            "Timeline Scope",
            ["Daily", "Weekly", "Monthly", "Custom"],
            default="Daily",
            label_visibility="collapsed"
        )

        now = datetime.now()
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now

        if time_frame == "Weekly":
            start_date = now - timedelta(days=7)
        elif time_frame == "Monthly":
            start_date = now - timedelta(days=30)
        elif time_frame == "Custom":
            with st.expander("📅 Custom Date Range", expanded=True):
                c1, c2 = st.columns(2)
                d_start = c1.date_input("Start Date", now - timedelta(days=7))
                d_end = c2.date_input("End Date", now)
                start_date = datetime.combine(d_start, datetime.min.time())
                end_date = datetime.combine(d_end, datetime.max.time())

        # =========================================================
        # 3. DATA ENGINE (SQLAlchemy -> Pandas)
        # =========================================================
        # 3a. Transaction Header Level Data
        tx_results = session.query(
            Transaction, User.full_name, func.max(Payment.method).label("primary_method")
        ).join(User, Transaction.cashier_id == User.id) \
            .outerjoin(Payment, Transaction.id == Payment.transaction_id) \
            .filter(Transaction.created_at.between(start_date, end_date)) \
            .group_by(Transaction.id, User.full_name).all()

        txdata = []
        for t, cashier_name, method in tx_results:
            tx_currency = t.currency.value if hasattr(t.currency, 'value') else str(t.currency)
            if tx_currency == selected_currency:  # Filter by globally selected currency
                display_method = method.value if hasattr(method, 'value') else str(method) if method else "N/A"
                txdata.append({
                    "Timestamp": t.created_at,
                    "Receipt": t.receipt_number,
                    "Total": float(t.grand_total),
                    "Method": display_method,
                    "Cashier": cashier_name,
                    "Hour": t.created_at.hour
                })
        df_tx = pd.DataFrame(txdata)

        # 3b. Transaction Item Level Data (For Product Intel & Sunburst)
        item_results = session.query(
            Transaction.currency, Category.name.label('category'), Product.name.label('product_name'),
            TransactionItem.quantity, TransactionItem.line_total
        ).join(TransactionItem, Transaction.id == TransactionItem.transaction_id) \
            .join(Product, TransactionItem.product_id == Product.id) \
            .join(Category, Product.category_id == Category.id) \
            .filter(Transaction.created_at.between(start_date, end_date)).all()

        item_data = []
        for curr, cat, prod, qty, total in item_results:
            tx_currency = curr.value if hasattr(curr, 'value') else str(curr)
            if tx_currency == selected_currency:
                item_data.append({
                    "Category": cat,
                    "Product": prod,
                    "Quantity": float(qty),
                    "Revenue": float(total)
                })
        df_items = pd.DataFrame(item_data)

        # =========================================================
        # LEVEL 1: HIGH-IMPACT KPIs
        # =========================================================
        st.write("")

        total_rev = total_orders = units_sold = avg_ticket = 0
        if not df_tx.empty:
            total_rev = df_tx['Total'].sum()
            total_orders = len(df_tx)
            avg_ticket = total_rev / total_orders
        if not df_items.empty:
            units_sold = df_items['Quantity'].sum()

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(
                f'<div class="glow-card"><div class="metric-label">Total Revenue ({selected_currency})</div><div class="metric-val">{total_rev:,.0f}</div></div>',
                unsafe_allow_html=True)
        with k2:
            st.markdown(
                f'<div class="glow-card"><div class="metric-label">Total Orders</div><div class="metric-val">{total_orders}</div></div>',
                unsafe_allow_html=True)
        with k3:
            st.markdown(
                f'<div class="glow-card"><div class="metric-label">Units Sold</div><div class="metric-val">{int(units_sold)}</div></div>',
                unsafe_allow_html=True)
        with k4:
            st.markdown(
                f'<div class="glow-card"><div class="metric-label">Avg Order Value</div><div class="metric-val">{avg_ticket:,.0f}</div></div>',
                unsafe_allow_html=True)

        # =========================================================
        # LEVEL 2: VISUAL TRENDS
        # =========================================================
        col_trends1, col_trends2 = st.columns(2)

        with col_trends1:
            st.markdown('<div class="section-header">☀️ Revenue Flow (Sunburst)</div>', unsafe_allow_html=True)
            if not df_items.empty:
                df_sb = df_items.groupby(['Category', 'Product'])['Revenue'].sum().reset_index()
                fig_sb = px.sunburst(
                    df_sb, path=['Category', 'Product'], values='Revenue',
                    color_discrete_sequence=GOLD_PALETTE
                )
                fig_sb.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=10, l=10, r=10, b=10), font_color="#D4AF37"
                )
                st.plotly_chart(fig_sb, use_container_width=True)
            else:
                st.info(f"No revenue data available for {selected_currency} in this period.")

        with col_trends2:
            st.markdown('<div class="section-header">⚡ Hourly Traffic Heatmap</div>', unsafe_allow_html=True)
            if not df_tx.empty:
                df_velocity = df_tx.groupby('Hour').size().reset_index(name='Volume')
                all_hours = pd.DataFrame({'Hour': range(24)})
                df_velocity = pd.merge(all_hours, df_velocity, on='Hour', how='left').fillna(0)

                fig_area = px.area(
                    df_velocity, x='Hour', y='Volume',
                    color_discrete_sequence=[GOLD_PALETTE[0]],
                    labels={'Hour': 'Time of Day (24H)', 'Volume': 'Orders'}
                )
                fig_area.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=10, l=10, r=10, b=10), font_color="#D4AF37",
                    xaxis=dict(tickmode='linear', tick0=0, dtick=2)
                )
                fig_area.update_traces(fillcolor='rgba(212, 175, 55, 0.2)', line=dict(color='#D4AF37', width=3))
                st.plotly_chart(fig_area, use_container_width=True)
            else:
                st.info("No traffic data available.")

        # =========================================================
        # LEVEL 3: PRODUCT INTELLIGENCE (Lifted from analytics.py)
        # =========================================================
        st.markdown('<div class="section-header">📦 Product Intelligence</div>', unsafe_allow_html=True)
        tab_top, tab_dead = st.tabs(["🏆 Top Products", "🐢 Dead Stock Analysis"])

        with tab_top:
            col_vol, col_rev = st.columns(2)
            if not df_items.empty:
                with col_vol:
                    st.markdown("##### By Volume (Units)")
                    top_vol = df_items.groupby('Product')['Quantity'].sum().sort_values(ascending=False).head(
                        10).reset_index()
                    fig_vol = px.bar(
                        top_vol, x='Quantity', y='Product', orientation='h',
                        template="plotly_dark", text='Quantity',
                        color_discrete_sequence=[GOLD_PALETTE[0]]
                    )
                    fig_vol.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False,
                                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_vol, use_container_width=True)

                with col_rev:
                    st.markdown(f"##### By Revenue ({selected_currency})")
                    top_rev = df_items.groupby('Product')['Revenue'].sum().sort_values(ascending=False).head(
                        10).reset_index()
                    fig_rev = px.bar(
                        top_rev, x='Revenue', y='Product', orientation='h',
                        template="plotly_dark", text_auto='.2s',
                        color_discrete_sequence=[GREEN_PALETTE[0]]
                    )
                    fig_rev.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False,
                                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_rev, use_container_width=True)
            else:
                st.info("No product data available.")

        with tab_dead:
            st.markdown("##### ⚠️ Dead Stock (Zero Sales in Period)")
            st.caption(
                f"Active inventory that has NOT sold during the selected timeline in the **{selected_currency}** market.")

            # Fetch all active inventory
            all_prods_query = session.query(
                Product.name, Inventory.quantity_on_hand, Product.unit_price_ksh
            ).join(Inventory, Product.id == Inventory.product_id).all()

            if all_prods_query:
                df_all = pd.DataFrame(all_prods_query, columns=['name', 'qty', 'price'])
                sold_products = df_items['Product'].unique() if not df_items.empty else []

                # Filter to only products that didn't sell
                df_dead = df_all[~df_all['name'].isin(sold_products)].copy()

                # Calculate tied up cash
                df_dead['cash_tied_up'] = df_dead['qty'] * df_dead['price']
                df_dead = df_dead[df_dead['cash_tied_up'] > 0].sort_values(by='cash_tied_up', ascending=False)

                if not df_dead.empty:
                    total_tied = df_dead['cash_tied_up'].sum()
                    st.error(f"💸 You have **{selected_currency} {total_tied:,.0f}** tied up in dead stock.")

                    st.dataframe(
                        df_dead[['name', 'qty', 'price', 'cash_tied_up']],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "name": "Product Name",
                            "qty": "Units on Hand",
                            "price": st.column_config.NumberColumn("Unit Price", format=f"{selected_currency} %d"),
                            "cash_tied_up": st.column_config.NumberColumn("Loss Potential",
                                                                          format=f"{selected_currency} %d")
                        }
                    )
                else:
                    st.success("✅ Incredible! Every single item in inventory has moved during this period.")
            else:
                st.info("Inventory data unavailable.")

        # =========================================================
        # LEVEL 4: OPERATIONAL DETAILS
        # =========================================================
        col_ops1, col_ops2 = st.columns([2, 1])

        with col_ops1:
            st.markdown('<div class="section-header">📡 Live Transaction Feed</div>', unsafe_allow_html=True)
            if not df_tx.empty:
                df_feed = df_tx[['Receipt', 'Total', 'Cashier', 'Timestamp']].copy()
                df_feed['Timestamp'] = pd.to_datetime(df_feed['Timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

                st.dataframe(
                    df_feed.head(50),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Total": st.column_config.NumberColumn("Amount", format=f"{selected_currency} %.2f")
                    }
                )
            else:
                st.info("No recent transactions.")

        with col_ops2:
            st.markdown('<div class="section-header">🚨 Visual Inventory Radar</div>', unsafe_allow_html=True)
            low_stock = session.query(Product.name, Inventory.quantity_on_hand) \
                .join(Inventory, Product.id == Inventory.product_id) \
                .filter(Inventory.quantity_on_hand <= 15) \
                .order_by(Inventory.quantity_on_hand.asc()).limit(10).all()

            if low_stock:
                for name, qty in low_stock:
                    qty = int(qty)
                    css_class = "stock-danger" if qty <= 5 else "stock-warning"
                    label = "CRITICAL" if qty <= 5 else "LOW"
                    color = DANGER_COLOR if qty <= 5 else WARNING_COLOR

                    st.markdown(f"""
                        <div class="stock-tile {css_class}">
                            <span style="font-weight: 600;">{name}</span>
                            <span>
                                <span style="color: {color}; font-weight: bold; font-size: 0.8rem; margin-right: 8px;">{label}</span>
                                <span>{qty} left</span>
                            </span>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("All stock levels are optimal. No immediate radar alerts.")

    finally:
        session.close()


if __name__ == "__main__":
    show_analytics_page()