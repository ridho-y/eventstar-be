from datetime import date, timedelta
from sqlalchemy import asc, func
from typing import Union, List
from decimal import Decimal

from ..database import db
from ..events import event_db
from .. import models, schemas, exceptions, constants

# ---------------------------------------------------------------------------------------------------- #
# ---------------------------------------  Daily Sales  ---------------------------------------------- #


def get_or_create_todays_sales(host: models.Host) -> models.HostDailySales:

    todays_sales = (
        db.get()
        .query(models.HostDailySales)
        .filter(models.HostDailySales.host_id == host.host_id)
        .filter(models.HostDailySales.date == date.today())
        .first()
    )

    if todays_sales:
        return todays_sales

    todays_sales = models.HostDailySales(
        host_id=host.host_id,
        date=date.today(),
        sales=0
    )

    db.get().add(todays_sales)
    return todays_sales


def log_daily_sales(amount: float, host: models.Host) -> None:
    todays_sales = get_or_create_todays_sales(host)
    todays_sales.sales += Decimal.from_float(amount)


def get_host_daily_sales_graph_data(user: models.User) -> schemas.GraphData:
    if not user.user_type == constants.HOST:
        raise exceptions.ForbiddenActionException("User cannot request for sales data.")

    limit = date.today() - timedelta(days=constants.SALES_DATA_LIMIT)
    daily_sales = (
        user.host.daily_sales_data.filter(models.HostDailySales.date >= limit)
        .order_by(asc(models.HostDailySales.date))
        .all()
    )

    return autofill_missing_date_points(daily_sales)


# ---------------------------------------------------------------------------------------------------------- #
# -------------------------------------------  Event Sales ------------------------------------------------- #


def get_or_create_todays_event_reserve_sales(host_id: int, reserve_id: int, event_id: int) -> models.EventSales:

    todays_sales = (
        db.get()
        .query(models.EventSales)
        .filter(models.EventSales.host_id == host_id)
        .filter(models.EventSales.reserve_id == reserve_id)
        .filter(models.EventSales.date == date.today())
        .first()
    )

    if todays_sales:
        return todays_sales

    todays_sales = models.EventSales(
        host_id=host_id,
        event_id=event_id,
        reserve_id=reserve_id,
        date=date.today(),
        sales=0
    )

    db.get().add(todays_sales)
    return todays_sales


def log_event_reserve_sales(event_id: int, reserve_id: int, num_tickets: int, host_id: int):
    todays_reserve_sales = get_or_create_todays_event_reserve_sales(host_id, reserve_id, event_id)
    todays_reserve_sales.sales += num_tickets


# ---------------------------------------  Event Sales Graph  ----------------------------------------- #


def get_event_daily_sales_graph_data(event_id: int, user: models.User) -> schemas.EventSalesAnalytics:
    if not user.user_type == constants.HOST:
        raise exceptions.ForbiddenActionException("User cannot request for sales data.")

    event = event_db.get_event(event_id)
    limit = date.today() - timedelta(days=constants.SALES_DATA_LIMIT)

    return schemas.EventSalesAnalytics(
        data=[
            get_event_reserve_sales_data(reserve, limit, user.host)
            for reserve in event.reserves
        ]
    )


def get_event_reserve_sales_data(
    reserve: models.EventReserve, limit: date, host: models.Host
) -> schemas.EventReserveSalesAnalytics:
    raw_sales_data = (
        host.event_sales_data.filter(models.EventSales.reserve_id == reserve.event_reserve_id)
        .filter(models.EventSales.date >= limit)
        .all()
    )

    sales_data = autofill_missing_date_points(raw_sales_data).data
    return schemas.EventReserveSalesAnalytics(id=reserve.reserve_name, data=sales_data)


# --------------------------------  Event Sales Percentage Chart  ------------------------------------ #


def get_event_sales_ratio(event_id: int, user: models.User) -> schemas.EventTotalSalesPerReserve:
    if not user.user_type == constants.HOST:
        raise exceptions.ForbiddenActionException("User cannot request for sales data.")

    event = event_db.get_event(event_id)

    return schemas.EventTotalSalesPerReserve(
        data=[
            get_event_reserve_total_sales(reserve, user.host)
            for reserve in event.reserves
        ]
    )


def get_event_reserve_total_sales(reserve: models.EventReserve, host: models.Host) -> schemas.EventReserveSalesTotal:
    total_tickets = (
        db.get()
        .query(func.coalesce(func.sum(models.EventSales.sales), 0))
        .filter(models.EventSales.reserve_id == reserve.event_reserve_id)
        .scalar()
    )

    return schemas.EventReserveSalesTotal(id=reserve.reserve_name, tickets=total_tickets)


# ---------------------------------------------------------------------------------------------------- #
# ------------------------------------------  Helpers ------------------------------------------------ #


def autofill_missing_date_points(
    sales_data: Union[List[models.HostDailySales], List[models.EventSales]], days: int = constants.SALES_DATA_LIMIT
) -> schemas.GraphData:

    start_date = date.today() - timedelta(days=days)
    all_dates = {start_date + timedelta(days=i): 0 for i in range(days)}
    for sales in sales_data:
        all_dates[sales.date] = sales.sales

    return schemas.GraphData(
        data=[
            schemas.DataPoint(xValue=date, yValue=sales)
            for date, sales in all_dates.items()
        ]
    )
