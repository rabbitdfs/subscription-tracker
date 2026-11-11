"""Создание всех таблиц

Revision ID: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "payment_methods",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("markup_percent", sa.Numeric(5, 2), nullable=False),
    )
    op.create_index("ix_payment_methods_user_id", "payment_methods", ["user_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "payment_method_id",
            sa.BigInteger(),
            sa.ForeignKey("payment_methods.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(4), nullable=False),
        sa.Column("period", sa.String(10), nullable=False),
        sa.Column("next_charge_date", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index(
        "ix_subscriptions_next_charge_date",
        "subscriptions",
        ["next_charge_date"],
        postgresql_where=sa.text("is_active AND deleted_at IS NULL"),
    )

    op.create_table(
        "rates",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("currency", sa.String(4), nullable=False),
        sa.Column("rate_to_rub", sa.Numeric(14, 6), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rates_source_currency_fetched_at", "rates", ["source", "currency", "fetched_at"])

    op.create_table(
        "charges",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("subscription_id", sa.BigInteger(), sa.ForeignKey("subscriptions.id"), nullable=False),
        sa.Column("charge_date", sa.Date(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(4), nullable=False),
        sa.Column("rate_to_rub", sa.Numeric(14, 6), nullable=False),
        sa.Column("rub_amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("is_approx", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_charges_subscription_id_charge_date", "charges", ["subscription_id", "charge_date"])


def downgrade():
    op.drop_table("charges")
    op.drop_table("rates")
    op.drop_table("subscriptions")
    op.drop_table("payment_methods")
    op.drop_table("users")
