import os
from dotenv import load_dotenv

# Ensure environment variables are loaded so database.py can connect
load_dotenv()

from database import get_session
from models import Category, Supplier, Product, Inventory

products_data = [
    # --- WHISKEY ---
    ("Jack Daniel's 1 Ltr", "WHK001", 20, 6000, 180000, "Whiskey", "Import", 1),
    ("Black Label 750ml", "WHK002", 20, 5500, 160000, "Whiskey", "Import", 1),
    ("Red Label 1 Ltr", "WHK003", 25, 3800, 100000, "Whiskey", "Import", 1),
    ("Red Label 750ml", "WHK004", 30, 3500, 90000, "Whiskey", "Import", 1),
    ("John Barr Red 1 Ltr", "WHK005", 20, 3800, 100000, "Whiskey", "Import", 0),
    ("John Barr Red 750ml", "WHK006", 20, 3500, 90000, "Whiskey", "Import", 0),
    ("John Barr Black 1 Ltr", "WHK007", 15, 4000, 110000, "Whiskey", "Import", 0),
    ("John Barr Black 750ml", "WHK008", 15, 3800, 100000, "Whiskey", "Import", 0),
    ("Jameson 1 Ltr", "WHK009", 25, 5000, 130000, "Whiskey", "Import", 1),
    ("J&B 1 Ltr", "WHK010", 15, 4500, 120000, "Whiskey", "Import", 0),
    ("J&B 750ml", "WHK011", 15, 4000, 110000, "Whiskey", "Import", 0),
    ("Ballantine's 1 Ltr", "WHK012", 15, 4500, 120000, "Whiskey", "Import", 0),
    ("Southern Comfort 1 Ltr", "WHK013", 15, 4000, 110000, "Whiskey", "Import", 0),
    ("Southern Comfort 750ml", "WHK014", 15, 3800, 100000, "Whiskey", "Import", 0),
    ("Grants 1 Ltr", "WHK015", 15, 4000, 110000, "Whiskey", "Import", 0),
    ("Grants 750ml", "WHK016", 15, 3800, 100000, "Whiskey", "Import", 0),
    ("Black & White 750ml", "WHK017", 20, 2500, 60000, "Whiskey", "Import", 0),
    ("Black & White 350ml", "WHK018", 30, 1000, 25000, "Whiskey", "Import", 0),
    ("Famous Grouse 350ml", "WHK019", 20, 1300, 35000, "Whiskey", "Import", 0),
    ("Famous Grouse 200ml", "WHK020", 30, 750, 20000, "Whiskey", "Import", 0),
    ("Bond 7 750ml", "WHK021", 30, 1300, 35000, "Whiskey", "UDL", 1),
    ("Bond 7 350ml", "WHK022", 40, 800, 20000, "Whiskey", "UDL", 1),
    ("Bond 7 200ml", "WHK023", 50, 250, 6000, "Whiskey", "UDL", 1),

    # --- RUM ---
    ("Captain Morgan Gold 750ml", "RUM001", 20, 1300, 35000, "Rum", "Import", 1),
    ("Captain Morgan Gold 200ml", "RUM002", 30, 450, 12000, "Rum", "Import", 0),
    ("Bacardi Negra Shots", "RUM003", 10, 200, 5000, "Rum", "Import", 0),
    ("Bacardi Blanca Shots", "RUM004", 10, 200, 5000, "Rum", "Import", 0),

    # --- BRANDY ---
    ("Old Admiral 750 ml", "BRD001", 20, 2000, 50000, "Brandy", "Import", 0),

    # --- GIN ---
    ("Gilbey's 750ml", "GIN001", 30, 1500, 40000, "Gin", "EABL", 1),
    ("Gilbey's 350ml", "GIN002", 40, 800, 20000, "Gin", "EABL", 1),
    ("Gilbey's 200ml", "GIN003", 50, 450, 12000, "Gin", "EABL", 1),
    ("Gordon's 1 Ltr", "GIN004", 20, 3800, 100000, "Gin", "EABL", 0),
    ("Gordon's 750ml", "GIN005", 25, 3500, 90000, "Gin", "EABL", 0),
    ("UG Waragi 750ml", "GIN006", 30, 1300, 35000, "Gin", "UDL", 1),
    ("UG Waragi Lemon & Ginger 750ml", "GIN007", 30, 1500, 40000, "Gin", "UDL", 0),
    ("UG Waragi 350ml", "GIN008", 40, 800, 20000, "Gin", "UDL", 1),
    ("UG Waragi Plastic 200ml", "GIN009", 50, 250, 6000, "Gin", "UDL", 1),
    ("UG Waragi Lemon & Ginger 200ml", "GIN010", 40, 550, 15000, "Gin", "UDL", 0),

    # --- VODKA ---
    ("Smirnoff Vodka 750 ml", "VOD001", 20, 1500, 40000, "Vodka", "EABL", 1),

    # --- LIQUEUR / SPIRITS / TEQUILA ---
    ("Chinese Spirit", "LIQ001", 20, 1300, 35000, "Liqueur", "Import", 0),
    ("Amarula 1 Ltr", "LIQ002", 15, 4000, 110000, "Liqueur", "Import", 1),
    ("Amarula 750ml", "LIQ003", 20, 3800, 100000, "Liqueur", "Import", 1),
    ("Amarula 350ml", "LIQ004", 25, 3000, 80000, "Liqueur", "Import", 0),
    ("Sheridan's 1 Ltr", "LIQ005", 10, 300, 10000, "Liqueur", "Import", 0),
    ("Zappa Blue Shots", "LIQ006", 15, 200, 5000, "Liqueur", "Import", 0),
    ("Zappa Red Shots", "LIQ007", 15, 200, 5000, "Liqueur", "Import", 0),
    ("V&A 750ml", "LIQ008", 20, 1500, 40000, "Liqueur", "Import", 0),
    ("V&A 200ml", "LIQ009", 30, 550, 15000, "Liqueur", "Import", 0),
    ("Camino Shots", "LIQ010", 10, 200, 5000, "Liqueur", "Import", 0),
    ("Jagermeister Shots", "LIQ011", 10, 200, 5000, "Liqueur", "Import", 0),
    ("Cuervo Shots", "LIQ012", 10, 200, 5000, "Liqueur", "Import", 0),

    # --- WINE ---
    ("Four Cousins 750ml", "WIN001", 20, 1500, 40000, "Wine", "Import", 1),
    ("Four Cousins Shots", "WIN002", 10, 300, 8000, "Wine", "Import", 0),
    ("Robertson 750 ml", "WIN003", 20, 1500, 50000, "Wine", "Import", 0),
    ("Mohan's 750 ml", "WIN004", 20, 1500, 40000, "Wine", "Import", 0),
    ("Theresa 750ml", "WIN005", 20, 1300, 35000, "Wine", "Import", 0),
    ("Bella 750ml", "WIN006", 20, 1300, 35000, "Wine", "Import", 0),
    ("Martini Rosso Shots", "WIN007", 10, 200, 5000, "Wine", "Import", 0),
    ("Martini Bianco Shots", "WIN008", 10, 200, 5000, "Wine", "Import", 0),
    ("4th Street 5Ltr", "WIN009", 5, 300, 8000, "Wine", "Import", 0),
    ("Bella 330ml", "WIN010", 25, 550, 15000, "Wine", "Import", 0),

    # --- BEER ---
    ("Tusker Lager Can", "BER001", 48, 350, 10000, "Beer", "EABL", 1),
    ("Tusker Lite Can", "BER002", 48, 350, 10000, "Beer", "EABL", 1),
    ("Tusker Lager (Bottle)", "BER003", 100, 150, 4000, "Beer", "EABL", 1),
    ("Tusker Lite (Bottle)", "BER004", 100, 150, 4000, "Beer", "EABL", 1),
    ("Tusker Malt", "BER005", 100, 150, 4000, "Beer", "EABL", 1),
    ("Tusker Cider", "BER006", 60, 200, 5000, "Beer", "EABL", 1),
    ("Bell", "BER007", 100, 150, 4000, "Beer", "EABL", 1),
    ("Bell Honey", "BER008", 50, 150, 4000, "Beer", "EABL", 0),
    ("Club", "BER009", 100, 150, 4000, "Beer", "EABL", 1),
    ("Nile", "BER010", 100, 150, 4000, "Beer", "EABL", 1),
    ("Pilsner", "BER011", 50, 150, 4000, "Beer", "EABL", 1),
    ("Heineken", "BER012", 48, 300, 8000, "Beer", "Import", 1),
    ("Heineken Can", "BER013", 24, 450, 12000, "Beer", "Import", 1),
    ("Black Ice", "BER014", 50, 200, 5000, "Beer", "Import", 0),
    ("Guaranna", "BER015", 50, 300, 8000, "Beer", "Import", 0),
    ("Savanna", "BER016", 50, 350, 10000, "Beer", "Import", 1),
    ("Amstel", "BER017", 50, 250, 6000, "Beer", "Import", 0),
    ("GK 500ml", "BER018", 50, 200, 5000, "Beer", "EABL", 1),
    ("GK 300ml", "BER019", 50, 150, 4000, "Beer", "EABL", 1),
    ("GK Smooth 300ml", "BER020", 50, 150, 4000, "Beer", "EABL", 1),
    ("Castle Lite", "BER021", 50, 150, 4000, "Beer", "Import", 1),

    # --- SOFT DRINKS ---
    ("Delmonte", "SFT001", 30, 350, 10000, "Soft Drinks", "Coca Cola", 0),
    ("Minute Maid", "SFT002", 40, 250, 6000, "Soft Drinks", "Coca Cola", 1),
    ("Soda 300ml", "SFT003", 100, 100, 2000, "Soft Drinks", "Coca Cola", 1),
    ("Power Play", "SFT004", 50, 120, 3000, "Soft Drinks", "Coca Cola", 1),
    ("Oner", "SFT005", 50, 150, 4000, "Soft Drinks", "General Supplier", 0),
    ("Rockboom", "SFT006", 50, 120, 3000, "Soft Drinks", "General Supplier", 1),
    ("Redbull", "SFT007", 50, 300, 8000, "Soft Drinks", "Import", 1),
    ("Predator", "SFT008", 50, 120, 3000, "Soft Drinks", "Coca Cola", 1),
    ("Water 500ml", "SFT009", 100, 50, 1000, "Soft Drinks", "General Supplier", 1),
    ("Water 1.5 Ltrs", "SFT010", 50, 100, 2000, "Soft Drinks", "General Supplier", 1),
]


def seed_database():
    session_gen = get_session()
    session = next(session_gen)

    try:
        print("Starting database seed...")

        # 1. Collect all unique categories and suppliers from the data
        unique_categories = set(row[5] for row in products_data)
        unique_suppliers = set(row[6] for row in products_data)

        # 2. Insert Categories (if they don't exist)
        category_map = {}
        for cat_name in unique_categories:
            cat = session.query(Category).filter_by(name=cat_name).first()
            if not cat:
                cat = Category(name=cat_name)
                session.add(cat)
                session.flush()  # Get the new ID immediately
                print(f"Created Category: {cat_name}")
            category_map[cat_name] = cat.id

        # 3. Insert Suppliers (if they don't exist)
        supplier_map = {}
        for sup_name in unique_suppliers:
            sup = session.query(Supplier).filter_by(name=sup_name).first()
            if not sup:
                sup = Supplier(name=sup_name, contact_name="Default Contact")
                session.add(sup)
                session.flush()
                print(f"Created Supplier: {sup_name}")
            supplier_map[sup_name] = sup.id

        # 4. Insert Products and Inventory
        products_added = 0
        for row in products_data:
            name, sku, stock, price_ksh, price_ugx, cat_name, sup_name, is_active = row

            # Check if product already exists by SKU
            existing_prod = session.query(Product).filter_by(sku=sku).first()

            if not existing_prod:
                # Create Product
                new_prod = Product(
                    name=name,
                    sku=sku,
                    category_id=category_map[cat_name],
                    supplier_id=supplier_map[sup_name],
                    unit_price_ksh=price_ksh,
                    unit_price_ugx=price_ugx,
                    cost_price_ksh=0.0,  # Defaulting to 0 since it's not in the tuple
                    is_active=bool(is_active)
                )
                session.add(new_prod)
                session.flush()  # Get Product ID

                # Create Initial Inventory record
                new_inv = Inventory(
                    product_id=new_prod.id,
                    quantity_on_hand=stock
                )
                session.add(new_inv)
                products_added += 1

        # Finalize transaction
        session.commit()
        print(f"✅ Success! Added {products_added} new products with inventory.")

    except Exception as e:
        session.rollback()
        print(f"❌ Error seeding database: {e}")
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    seed_database()