"""
models.py
---------
SQLAlchemy ORM models for the hybrid POS + Inventory Management System.

Entity overview:
  User              — staff accounts (admin, cashier, manager, waiter)
  Category          — product categories / departments
  Supplier          — vendors who supply stock
  Product           — items sold or stocked (dual KSH + UGX prices)
  Inventory         — current stock levels per product
  Customer          — registered customers (loyalty / receipts)
  Order             — a table/counter order with a full lifecycle
  OrderItem         — line items on an order (currency locked at placement)
  Transaction       — payment record settling an Order
  TransactionItem   — line items mirrored from OrderItems at checkout
  Payment           — one or more payment legs for a transaction
  PurchaseOrder     — a restock order sent to a supplier
  PurchaseOrderItem — line items within a purchase order
  StockMovement     — immutable audit log of every stock change
"""

import enum
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Numeric, Boolean,
    DateTime, ForeignKey, Enum, text
)
from sqlalchemy.orm import relationship

# Import your DeclarativeBase from database.py
from database import Base


# ---------------------------------------------------------------------------
# Python Enums (Mapped to PostgreSQL custom types)
# ---------------------------------------------------------------------------
class Currency(str, enum.Enum):
    KSH = "KSH"
    UGX = "UGX"

class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    cashier = "cashier"
    waiter = "waiter"

class OrderStatus(str, enum.Enum):
    placed = "placed"
    served = "served"
    cleared = "cleared"

class TransactionStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    voided = "voided"
    refunded = "refunded"

class PaymentMethod(str, enum.Enum):
    cash = "cash"
    card = "card"
    mobile_money = "mobile_money"
    credit = "credit"

class PurchaseOrderStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    partially_received = "partially_received"
    received = "received"
    cancelled = "cancelled"

class MovementType(str, enum.Enum):
    purchase = "purchase"
    sale = "sale"
    adjustment = "adjustment"
    return_in = "return_in"
    return_out = "return_out"
    damage = "damage"


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(200), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, name="userrole", create_type=False), nullable=False, server_default="cashier")
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

    # Relationships
    orders_placed = relationship("Order", foreign_keys="[Order.placed_by_id]", back_populates="placed_by")
    orders_served = relationship("Order", foreign_keys="[Order.served_by_id]", back_populates="served_by")
    orders_cleared = relationship("Order", foreign_keys="[Order.cleared_by_id]", back_populates="cleared_by")
    transactions = relationship("Transaction", back_populates="cashier")
    stock_movements = relationship("StockMovement", back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    products = relationship("Product", back_populates="category")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    contact_name = Column(String(120))
    phone = Column(String(30))
    email = Column(String(200))
    address = Column(Text)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

    products = relationship("Product", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(60), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category_id = Column(Integer, ForeignKey("categories.id"))
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))

    unit_price_ksh = Column(Numeric(12, 2), nullable=False)
    unit_price_ugx = Column(Numeric(12, 2), nullable=False)
    cost_price_ksh = Column(Numeric(12, 2), nullable=False)
    tax_rate = Column(Numeric(5, 2), nullable=False, server_default="0.00")
    unit_of_measure = Column(String(30), server_default="piece")
    barcode = Column(String(100), unique=True, index=True)
    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

    category = relationship("Category", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    inventory = relationship("Inventory", back_populates="product", uselist=False)
    order_items = relationship("OrderItem", back_populates="product")
    transaction_items = relationship("TransactionItem", back_populates="product")
    purchase_order_items = relationship("PurchaseOrderItem", back_populates="product")
    stock_movements = relationship("StockMovement", back_populates="product")


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, unique=True)
    quantity_on_hand = Column(Numeric(12, 3), nullable=False, server_default="0")
    reorder_point = Column(Numeric(12, 3), nullable=False, server_default="10")
    reorder_quantity = Column(Numeric(12, 3), nullable=False, server_default="50")
    location = Column(String(100))
    last_updated = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

    product = relationship("Product", back_populates="inventory")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(120), nullable=False)
    phone = Column(String(30), unique=True)
    email = Column(String(200), unique=True)
    loyalty_pts = Column(Integer, nullable=False, server_default="0")
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    orders = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(30), nullable=False, unique=True)
    currency = Column(Enum(Currency, name="currency", create_type=False), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    table_ref = Column(String(50))
    status = Column(Enum(OrderStatus, name="orderstatus", create_type=False), nullable=False, server_default="placed", index=True)
    placed_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"), index=True)
    placed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    served_at = Column(DateTime(timezone=True))
    served_by_id = Column(Integer, ForeignKey("users.id"))
    cleared_at = Column(DateTime(timezone=True))
    cleared_by_id = Column(Integer, ForeignKey("users.id"))

    subtotal = Column(Numeric(14, 2), nullable=False, server_default="0")
    tax_total = Column(Numeric(14, 2), nullable=False, server_default="0")
    discount_total = Column(Numeric(14, 2), nullable=False, server_default="0")
    grand_total = Column(Numeric(14, 2), nullable=False, server_default="0")
    notes = Column(Text)

    customer = relationship("Customer", back_populates="orders")
    placed_by = relationship("User", foreign_keys=[placed_by_id], back_populates="orders_placed")
    served_by = relationship("User", foreign_keys=[served_by_id], back_populates="orders_served")
    cleared_by = relationship("User", foreign_keys=[cleared_by_id], back_populates="orders_cleared")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    transaction = relationship("Transaction", back_populates="order", uselist=False)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(12, 3), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    discount = Column(Numeric(12, 2), nullable=False, server_default="0")
    tax_amount = Column(Numeric(12, 2), nullable=False, server_default="0")
    line_total = Column(Numeric(14, 2), nullable=False)
    notes = Column(Text)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    receipt_number = Column(String(30), nullable=False, unique=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    cashier_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    currency = Column(Enum(Currency, name="currency", create_type=False), nullable=False, index=True)
    status = Column(Enum(TransactionStatus, name="transactionstatus", create_type=False), nullable=False, server_default="completed")

    subtotal = Column(Numeric(14, 2), nullable=False, server_default="0")
    tax_total = Column(Numeric(14, 2), nullable=False, server_default="0")
    discount_total = Column(Numeric(14, 2), nullable=False, server_default="0")
    grand_total = Column(Numeric(14, 2), nullable=False, server_default="0")
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), index=True)

    order = relationship("Order", back_populates="transaction")
    cashier = relationship("User", back_populates="transactions")
    items = relationship("TransactionItem", back_populates="transaction", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="transaction", cascade="all, delete-orphan")


class TransactionItem(Base):
    __tablename__ = "transaction_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(BigInteger, ForeignKey("transactions.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(12, 3), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    discount = Column(Numeric(12, 2), nullable=False, server_default="0")
    tax_amount = Column(Numeric(12, 2), nullable=False, server_default="0")
    line_total = Column(Numeric(14, 2), nullable=False)

    transaction = relationship("Transaction", back_populates="items")
    product = relationship("Product", back_populates="transaction_items")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(BigInteger, ForeignKey("transactions.id"), nullable=False)
    method = Column(Enum(PaymentMethod, name="paymentmethod", create_type=False), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(Enum(Currency, name="currency", create_type=False), nullable=False)
    reference = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    transaction = relationship("Transaction", back_populates="payments")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    po_number = Column(String(30), nullable=False, unique=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    status = Column(Enum(PurchaseOrderStatus, name="purchaseorderstatus", create_type=False), nullable=False, server_default="draft")
    expected_date = Column(DateTime(timezone=True))
    received_date = Column(DateTime(timezone=True))
    total_cost = Column(Numeric(14, 2), nullable=False, server_default="0")
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity_ordered = Column(Numeric(12, 3), nullable=False)
    quantity_received = Column(Numeric(12, 3), nullable=False, server_default="0")
    unit_cost = Column(Numeric(12, 2), nullable=False)
    line_total = Column(Numeric(14, 2), nullable=False)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product", back_populates="purchase_order_items")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    movement_type = Column(Enum(MovementType, name="movementtype", create_type=False), nullable=False)
    quantity_change = Column(Numeric(12, 3), nullable=False)
    quantity_before = Column(Numeric(12, 3), nullable=False)
    quantity_after = Column(Numeric(12, 3), nullable=False)
    reference_id = Column(String(60))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), index=True)

    product = relationship("Product", back_populates="stock_movements")
    user = relationship("User", back_populates="stock_movements")