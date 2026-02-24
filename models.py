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
  Order             — a table/counter order with a full lifecycle:
                       placed → served → cleared
  OrderItem         — line items on an order (currency locked at placement)
  Transaction       — payment record settling an Order
  TransactionItem   — line items mirrored from OrderItems at checkout
  Payment           — one or more payment legs for a transaction
  PurchaseOrder     — a restock order sent to a supplier
  PurchaseOrderItem — line items within a purchase order
  StockMovement     — immutable audit log of every stock change

Currency design:
  - Products carry two independent prices: unit_price_ksh and unit_price_ugx.
  - When an Order is placed, the currency is chosen (KSH or UGX) and locked
    on the Order.  All OrderItems store the unit price in that currency.
  - Sales reporting is done per-currency so the two revenue streams are never
    blended or converted.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Enum, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Currency(str, enum.Enum):
    KSH = "KSH"   # Kenyan Shilling
    UGX = "UGX"   # Ugandan Shilling


class UserRole(str, enum.Enum):
    admin   = "admin"
    manager = "manager"
    cashier = "cashier"
    waiter  = "waiter"


class OrderStatus(str, enum.Enum):
    placed  = "placed"    # order received, awaiting fulfilment
    served  = "served"    # all items delivered to customer
    cleared = "cleared"   # table/counter cleared, ready for next customer


class TransactionStatus(str, enum.Enum):
    pending   = "pending"
    completed = "completed"
    voided    = "voided"
    refunded  = "refunded"


class PaymentMethod(str, enum.Enum):
    cash         = "cash"
    card         = "card"
    mobile_money = "mobile_money"
    credit       = "credit"


class PurchaseOrderStatus(str, enum.Enum):
    draft              = "draft"
    sent               = "sent"
    partially_received = "partially_received"
    received           = "received"
    cancelled          = "cancelled"


class MovementType(str, enum.Enum):
    purchase   = "purchase"    # stock added via purchase order
    sale       = "sale"        # stock removed via POS sale
    adjustment = "adjustment"  # manual correction
    return_in  = "return_in"   # customer return — stock comes back
    return_out = "return_out"  # return to supplier
    damage     = "damage"      # damaged / written off


# ---------------------------------------------------------------------------
# User (Staff)
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    full_name       = Column(String(120), nullable=False)
    email           = Column(String(200), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(Enum(UserRole), nullable=False, default=UserRole.cashier)
    is_active       = Column(Boolean, nullable=False, default=True)
    created_at      = Column(DateTime(timezone=True), default=utcnow)
    updated_at      = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    orders_placed   = relationship("Order", foreign_keys="Order.placed_by_id",  back_populates="placed_by")
    orders_served   = relationship("Order", foreign_keys="Order.served_by_id",  back_populates="served_by")
    orders_cleared  = relationship("Order", foreign_keys="Order.cleared_by_id", back_populates="cleared_by")
    transactions    = relationship("Transaction", back_populates="cashier")
    stock_movements = relationship("StockMovement", back_populates="user")

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------
class Category(Base):
    __tablename__ = "categories"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at  = Column(DateTime(timezone=True), default=utcnow)

    products = relationship("Product", back_populates="category")

    def __repr__(self):
        return f"<Category {self.name}>"


# ---------------------------------------------------------------------------
# Supplier
# ---------------------------------------------------------------------------
class Supplier(Base):
    __tablename__ = "suppliers"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    name         = Column(String(200), nullable=False)
    contact_name = Column(String(120))
    phone        = Column(String(30))
    email        = Column(String(200))
    address      = Column(Text)
    is_active    = Column(Boolean, nullable=False, default=True)
    created_at   = Column(DateTime(timezone=True), default=utcnow)
    updated_at   = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")

    def __repr__(self):
        return f"<Supplier {self.name}>"


# ---------------------------------------------------------------------------
# Product  — dual-currency pricing
# ---------------------------------------------------------------------------
class Product(Base):
    """
    unit_price_ksh and unit_price_ugx are set independently by management.
    They are NOT derived from each other via a conversion rate — each market
    may have different pricing strategies, promotions, or margins.
    """
    __tablename__ = "products"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    sku             = Column(String(60), unique=True, nullable=False)
    name            = Column(String(200), nullable=False)
    description     = Column(Text)
    category_id     = Column(Integer, ForeignKey("categories.id"), nullable=True)
    supplier_id     = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    # ── Selling prices (one per currency, independently managed) ──────────
    unit_price_ksh  = Column(Numeric(12, 2), nullable=False)
    unit_price_ugx  = Column(Numeric(12, 2), nullable=False)

    # ── Cost price (base/home currency: KSH) ─────────────────────────────
    cost_price_ksh  = Column(Numeric(12, 2), nullable=False)

    tax_rate        = Column(Numeric(5, 2), nullable=False, default=0.00)  # %
    unit_of_measure = Column(String(30), default="piece")
    barcode         = Column(String(100), unique=True, nullable=True)
    is_active       = Column(Boolean, nullable=False, default=True)
    created_at      = Column(DateTime(timezone=True), default=utcnow)
    updated_at      = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    category          = relationship("Category", back_populates="products")
    supplier          = relationship("Supplier")
    inventory         = relationship("Inventory", back_populates="product", uselist=False)
    order_items       = relationship("OrderItem", back_populates="product")
    transaction_items = relationship("TransactionItem", back_populates="product")
    po_items          = relationship("PurchaseOrderItem", back_populates="product")
    stock_movements   = relationship("StockMovement", back_populates="product")

    def price_for(self, currency: "Currency"):
        """Return the correct selling price for the given currency."""
        return self.unit_price_ksh if currency == Currency.KSH else self.unit_price_ugx

    def __repr__(self):
        return (
            f"<Product [{self.sku}] {self.name} "
            f"KSH={self.unit_price_ksh} UGX={self.unit_price_ugx}>"
        )


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
class Inventory(Base):
    """Current stock level for each product. Currency-agnostic — stock is stock."""
    __tablename__ = "inventory"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    product_id       = Column(Integer, ForeignKey("products.id"), unique=True, nullable=False)
    quantity_on_hand = Column(Numeric(12, 3), nullable=False, default=0)
    reorder_point    = Column(Numeric(12, 3), nullable=False, default=10)
    reorder_quantity = Column(Numeric(12, 3), nullable=False, default=50)
    location         = Column(String(100))
    last_updated     = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    product = relationship("Product", back_populates="inventory")

    @property
    def needs_reorder(self) -> bool:
        return self.quantity_on_hand <= self.reorder_point

    def __repr__(self):
        return f"<Inventory product_id={self.product_id} qty={self.quantity_on_hand}>"


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------
class Customer(Base):
    __tablename__ = "customers"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    full_name   = Column(String(120), nullable=False)
    phone       = Column(String(30), unique=True, nullable=True)
    email       = Column(String(200), unique=True, nullable=True)
    loyalty_pts = Column(Integer, nullable=False, default=0)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), default=utcnow)

    orders = relationship("Order", back_populates="customer")

    def __repr__(self):
        return f"<Customer {self.full_name}>"


# ---------------------------------------------------------------------------
# Order  — the core lifecycle entity
# ---------------------------------------------------------------------------
class Order(Base):
    """
    An Order represents a table or counter request, from placement through
    fulfilment to clearance.

    Lifecycle
    ─────────
       placed  ──►  served  ──►  cleared
         │             │             │
     placed_at      served_at    cleared_at
     placed_by_id   served_by_id cleared_by_id

    Currency is chosen at placement and locked for the lifetime of the order.
    All monetary values (subtotal, grand_total, item prices) are in that currency.

    An Order becomes a Transaction when payment is collected (one-to-one link).
    """
    __tablename__ = "orders"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(30), unique=True, nullable=False)
    currency     = Column(Enum(Currency), nullable=False)          # KSH or UGX — locked at placement
    customer_id  = Column(Integer, ForeignKey("customers.id"), nullable=True)
    table_ref    = Column(String(50), nullable=True)               # e.g. "Table 4", "Counter 1"

    # ── Status ──────────────────────────────────────────────────────────
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.placed)

    # ── Placed ──────────────────────────────────────────────────────────
    placed_at    = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    placed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # ── Served (all items delivered to the customer) ─────────────────────
    served_at    = Column(DateTime(timezone=True), nullable=True)
    served_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # ── Cleared (table/counter cleared, session closed) ──────────────────
    cleared_at    = Column(DateTime(timezone=True), nullable=True)
    cleared_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # ── Totals (all in the order's locked currency) ──────────────────────
    subtotal       = Column(Numeric(14, 2), nullable=False, default=0)
    tax_total      = Column(Numeric(14, 2), nullable=False, default=0)
    discount_total = Column(Numeric(14, 2), nullable=False, default=0)
    grand_total    = Column(Numeric(14, 2), nullable=False, default=0)

    notes = Column(Text)

    # Relationships
    customer   = relationship("Customer", back_populates="orders")
    placed_by  = relationship("User", foreign_keys=[placed_by_id],  back_populates="orders_placed")
    served_by  = relationship("User", foreign_keys=[served_by_id],  back_populates="orders_served")
    cleared_by = relationship("User", foreign_keys=[cleared_by_id], back_populates="orders_cleared")
    items       = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    transaction = relationship("Transaction", back_populates="order", uselist=False)

    # ── Convenience helpers ──────────────────────────────────────────────
    @property
    def time_to_serve(self):
        """Minutes between placement and served. None if not yet served."""
        if self.served_at and self.placed_at:
            return int((self.served_at - self.placed_at).total_seconds() // 60)
        return None

    @property
    def time_to_clear(self):
        """Minutes between placement and cleared. None if not yet cleared."""
        if self.cleared_at and self.placed_at:
            return int((self.cleared_at - self.placed_at).total_seconds() // 60)
        return None

    def __repr__(self):
        return f"<Order #{self.order_number} [{self.currency}] {self.status}>"


# ---------------------------------------------------------------------------
# OrderItem  — line items on an Order
# ---------------------------------------------------------------------------
class OrderItem(Base):
    """
    Records the unit price in the order's currency at the moment the item
    was added. Price changes on the Product after order placement do not
    affect existing orders.
    """
    __tablename__ = "order_items"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    order_id   = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity   = Column(Numeric(12, 3), nullable=False)

    # Price snapshotted from Product.price_for(order.currency) at placement
    unit_price = Column(Numeric(12, 2), nullable=False)   # in order's currency
    discount   = Column(Numeric(12, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(12, 2), nullable=False, default=0)
    line_total = Column(Numeric(14, 2), nullable=False)

    notes = Column(Text)   # special instructions e.g. "no onions", "extra shot"

    # Relationships
    order   = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem order={self.order_id} product={self.product_id} qty={self.quantity}>"


# ---------------------------------------------------------------------------
# Transaction  — payment record that settles an Order
# ---------------------------------------------------------------------------
class Transaction(Base):
    """
    Created when an Order is paid. Inherits currency from its Order.
    All amounts are in that currency.
    """
    __tablename__ = "transactions"

    id             = Column(BigInteger, primary_key=True, autoincrement=True)
    receipt_number = Column(String(30), unique=True, nullable=False)
    order_id       = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False)
    cashier_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    currency       = Column(Enum(Currency), nullable=False)   # inherited from Order
    status         = Column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.completed)
    subtotal       = Column(Numeric(14, 2), nullable=False, default=0)
    tax_total      = Column(Numeric(14, 2), nullable=False, default=0)
    discount_total = Column(Numeric(14, 2), nullable=False, default=0)
    grand_total    = Column(Numeric(14, 2), nullable=False, default=0)
    notes          = Column(Text)
    created_at     = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    order    = relationship("Order", back_populates="transaction")
    cashier  = relationship("User", back_populates="transactions")
    items    = relationship("TransactionItem", back_populates="transaction", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="transaction", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Transaction #{self.receipt_number} [{self.currency}] {self.grand_total}>"


# ---------------------------------------------------------------------------
# TransactionItem  — snapshot of OrderItems at checkout
# ---------------------------------------------------------------------------
class TransactionItem(Base):
    """
    Mirrors OrderItems at the moment of payment. Kept separately so voids
    and refunds can be tracked without mutating the original Order.
    """
    __tablename__ = "transaction_items"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(BigInteger, ForeignKey("transactions.id"), nullable=False)
    product_id     = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity       = Column(Numeric(12, 3), nullable=False)
    unit_price     = Column(Numeric(12, 2), nullable=False)   # in transaction's currency
    discount       = Column(Numeric(12, 2), nullable=False, default=0)
    tax_amount     = Column(Numeric(12, 2), nullable=False, default=0)
    line_total     = Column(Numeric(14, 2), nullable=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="items")
    product     = relationship("Product", back_populates="transaction_items")

    def __repr__(self):
        return f"<TxItem tx={self.transaction_id} product={self.product_id} qty={self.quantity}>"


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------
class Payment(Base):
    __tablename__ = "payments"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(BigInteger, ForeignKey("transactions.id"), nullable=False)
    method         = Column(Enum(PaymentMethod), nullable=False)
    amount         = Column(Numeric(14, 2), nullable=False)
    currency       = Column(Enum(Currency), nullable=False)   # currency of this payment leg
    reference      = Column(String(100))   # M-Pesa ref, card auth code, etc.
    created_at     = Column(DateTime(timezone=True), default=utcnow)

    transaction = relationship("Transaction", back_populates="payments")

    def __repr__(self):
        return f"<Payment [{self.currency}] {self.method} {self.amount}>"


# ---------------------------------------------------------------------------
# Purchase Order
# ---------------------------------------------------------------------------
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    po_number     = Column(String(30), unique=True, nullable=False)
    supplier_id   = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    status        = Column(Enum(PurchaseOrderStatus), nullable=False, default=PurchaseOrderStatus.draft)
    expected_date = Column(DateTime(timezone=True), nullable=True)
    received_date = Column(DateTime(timezone=True), nullable=True)
    total_cost    = Column(Numeric(14, 2), nullable=False, default=0)
    notes         = Column(Text)
    created_at    = Column(DateTime(timezone=True), default=utcnow)
    updated_at    = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    supplier = relationship("Supplier", back_populates="purchase_orders")
    items    = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PurchaseOrder #{self.po_number} {self.status}>"


# ---------------------------------------------------------------------------
# PurchaseOrderItem
# ---------------------------------------------------------------------------
class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id        = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity_ordered  = Column(Numeric(12, 3), nullable=False)
    quantity_received = Column(Numeric(12, 3), nullable=False, default=0)
    unit_cost         = Column(Numeric(12, 2), nullable=False)
    line_total        = Column(Numeric(14, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint("purchase_order_id", "product_id", name="uq_po_product"),
    )

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product        = relationship("Product", back_populates="po_items")

    def __repr__(self):
        return f"<POItem po={self.purchase_order_id} product={self.product_id}>"


# ---------------------------------------------------------------------------
# StockMovement  — immutable audit log
# ---------------------------------------------------------------------------
class StockMovement(Base):
    """
    Every change to Inventory.quantity_on_hand must produce a StockMovement.
    Stock is currency-agnostic (a unit is a unit). reference_id links back
    to the order number, receipt number, or PO number that caused the movement.
    """
    __tablename__ = "stock_movements"

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id      = Column(Integer, ForeignKey("products.id"), nullable=False)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=True)
    movement_type   = Column(Enum(MovementType), nullable=False)
    quantity_change = Column(Numeric(12, 3), nullable=False)   # + = in,  - = out
    quantity_before = Column(Numeric(12, 3), nullable=False)
    quantity_after  = Column(Numeric(12, 3), nullable=False)
    reference_id    = Column(String(60))
    notes           = Column(Text)
    created_at      = Column(DateTime(timezone=True), default=utcnow)

    product = relationship("Product", back_populates="stock_movements")
    user    = relationship("User", back_populates="stock_movements")

    def __repr__(self):
        return (
            f"<StockMovement product={self.product_id} "
            f"{self.movement_type} {self.quantity_change:+}>"
        )
