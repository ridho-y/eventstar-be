from datetime import datetime
from sqlalchemy import desc

from .. import models, schemas, exceptions, constants
from ..database import db
from ..profile import host_analytics
from ..search.sort_filter import get_subset_results
from .billing import get_billing_model

from decimal import Decimal
import locale

try:
    locale.setlocale(locale.LC_ALL, "en_AU.UTF-8")
except locale.Error:
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")


# ---------------------------------------------------------------------------------------------------------------- #
# ---------------------------------------- Manage Account Balance ------------------------------------------------ #


def deposit_balance(balance_info: schemas.UpdateBalance, user: models.User) -> None:
    card = get_billing_model(balance_info.billingId, user)
    if not card:
        raise exceptions.ForbiddenAccessException("Invalid billing information. Please choose another payment method.")

    if user.balance + Decimal.from_float(balance_info.amount) >= constants.MAX_BALANCE:
        error_msg = f"User cannot store more than {locale.currency(constants.MAX_BALANCE, symbol=True, grouping=True)} in their account."
        raise exceptions.ForbiddenActionException(error_msg)

    user.balance += Decimal.from_float(balance_info.amount)

    log_description = f"Deposit {locale.currency(balance_info.amount, symbol=True, grouping=True)} from card number ending in '{card.card_number[-4:]}'."
    log_transaction(balance_info.amount, log_description, user)


def withdraw_balance(balance_info: schemas.UpdateBalance, user: models.User) -> None:
    card = get_billing_model(balance_info.billingId, user)
    if not card:
        error_msg = "Invalid billing information. Please choose another card to withdraw the funds to."
        raise exceptions.ForbiddenAccessException(error_msg)

    if user.balance < balance_info.amount:
        error_msg =  f"Cannot withdraw more than the user's balance: {locale.currency(user.balance, symbol=True, grouping=True)}."
        raise exceptions.InvalidInputException(error_msg)

    user.balance -= Decimal.from_float(balance_info.amount)

    log_description = f"Withdraw {locale.currency(balance_info.amount, symbol=True, grouping=True)} to card number ending in '{card.card_number[-4:]}'."
    log_transaction(balance_info.amount, log_description, user)


# -------------------------------------------------------------------------------------------------------------- #
# ------------------------------------------- Make Transactions ------------------------------------------------ #


def add_balance(amount: float, action: str, item: str, user: models.User) -> None:
    log_description = f"Credit {locale.currency(amount, symbol=True, grouping=True)}: {action} for {item}."

    user.balance += Decimal.from_float(amount)
    log_transaction(amount, log_description, user)

    if user.user_type == constants.HOST:
        host_analytics.log_daily_sales(amount, user.host)


def deduct_balance(amount: float, action: str, item: str, user: models.User) -> None:
    log_description = f"Debit {locale.currency(amount, symbol=True, grouping=True)}: {action} for {item}."

    user.balance -= Decimal.from_float(amount)
    log_transaction(-amount, log_description, user)

    if user.user_type == constants.HOST:
        host_analytics.log_daily_sales(-amount, user.host)


# ------------------------------------------------------------------------------------------------------------- #
# ---------------------------------------- Transaction Logging ------------------------------------------------ #


def log_transaction(amount: float, description: str, user: models.User) -> None:

    debit, credit = (0, amount) if amount >= 0 else (abs(amount), 0)

    transaction = models.Transaction(
        user_id=user.user_id,
        date=datetime.now(),
        description=description,
        credit=credit,
        debit=debit,
        balance=user.balance,
    )

    db.get().add(transaction)


def get_transaction_schema(transaction: models.Transaction) -> schemas.Transaction:
    return schemas.Transaction(
        dateTime=transaction.date,
        description=transaction.description,
        credit=transaction.credit,
        debit=transaction.debit,
        balance=transaction.balance,
    )


def get_my_transactions(start: int, user: models.User) -> schemas.Transactions:
    transactions = user.transactions.order_by(desc(models.Transaction.date)).all()

    # Get the required subset
    transactions = get_subset_results(transactions, start, len(transactions), constants.TRANSACTION_RESULTS)

    return schemas.Transactions(
        transactions=[
            get_transaction_schema(transaction) 
            for transaction in transactions
        ]
    )
