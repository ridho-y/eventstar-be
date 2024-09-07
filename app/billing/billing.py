from .. import models, schemas
from .. import exceptions
from ..database import db

# ------------------------------------------------------------------------------------------------- #
# ---------------------------------------- Billing ------------------------------------------------ #


def insert_billing(user: models.User, billing: schemas.BillingInfo):
    # Check if there is an existing billing info for the same user with the same card number
    if check_existing_billing(billing.cardNumber, user.user_id):
        raise exceptions.NotUniqueException(
            f"Your account already has a payment method with cardnumber {billing.cardNumber}."
        )

    # Create a new billing info object
    new_billing_info = models.BillingInfo(
        user_id=user.user_id,
        cardholder_name=billing.billingAddress.firstName + " " + billing.billingAddress.lastName,
        card_number=billing.cardNumber,
        expiry_month=billing.expiryMonth,
        expiry_year=billing.expiryYear,
        first_name=billing.billingAddress.firstName,
        last_name=billing.billingAddress.lastName,
        country=billing.billingAddress.country,
        street_line1=billing.billingAddress.streetLine1,
        street_line2=billing.billingAddress.streetLine2,
        suburb=billing.billingAddress.suburb,
        state=billing.billingAddress.state,
        postcode=billing.billingAddress.postcode,
        email=billing.billingAddress.email,
        phone=billing.billingAddress.phone,
    )

    # Add the new billing info to the session
    db.get().add(new_billing_info)


def update_billing(user: models.User, billing_id: int, billing: schemas.BillingInfo):
    billing_info = get_billing_model(billing_id, user)

    if billing.cardNumber and not check_existing_billing(billing.cardNumber, user.user_id, billing_id):
        billing_info.card_number = billing.cardNumber
    if billing.expiryMonth:
        billing_info.expiry_month = billing.expiryMonth
    if billing.expiryYear:
        billing_info.expiry_year = billing.expiryYear
    if billing.billingAddress:
        if billing.billingAddress.firstName:
            billing_info.first_name = billing.billingAddress.firstName
        if billing.billingAddress.lastName:
            billing_info.last_name = billing.billingAddress.lastName
        if billing.billingAddress.country:
            billing_info.country = billing.billingAddress.country
        if billing.billingAddress.streetLine1:
            billing_info.street_line1 = billing.billingAddress.streetLine1
        if billing.billingAddress.streetLine2:
            billing_info.street_line2 = billing.billingAddress.streetLine2
        if billing.billingAddress.suburb:
            billing_info.suburb = billing.billingAddress.suburb
        if billing.billingAddress.state:
            billing_info.state = billing.billingAddress.state
        if billing.billingAddress.postcode:
            billing_info.postcode = billing.billingAddress.postcode
        if billing.billingAddress.email:
            billing_info.email = billing.billingAddress.email
        if billing.billingAddress.phone:
            billing_info.phone = billing.billingAddress.phone


def get_all_billings(user: models.User):
    user_billings = db.get().query(models.BillingInfo).filter_by(user_id=user.user_id).all()

    all_billings = [
        schemas.BillingInfo(
            billingId=billing.billing_id,
            cardNumber=billing.card_number,
            expiryMonth=billing.expiry_month,
            expiryYear=billing.expiry_year,
            billingAddress=schemas.BillingAddress(
                firstName=billing.first_name,
                lastName=billing.last_name,
                country=billing.country,
                streetLine1=billing.street_line1,
                streetLine2=billing.street_line2,
                suburb=billing.suburb,
                state=billing.state,
                postcode=billing.postcode,
                email=billing.email,
                phone=billing.phone,
            ),
        )
        for billing in user_billings
    ]

    return schemas.AllBillingInfo(billingInfo=all_billings, balance=user.balance)


def get_billing_model(billing_id: int, user: models.User) -> models.BillingInfo:
    try:
        billing_info = (
            db.get()
            .query(models.BillingInfo)
            .filter_by(user_id=user.user_id, billing_id=billing_id)
            .one()
        )

    except Exception:
        raise exceptions.InvalidInputException(f"Could not find billing id '{billing_id}' for user '{user.username}'.")

    return billing_info


def get_billing_schema(user: models.User, billing_id: int) -> schemas.BillingInfo:
    item = get_billing_model(billing_id, user)

    address = schemas.BillingAddress(
        firstName=item.first_name,
        lastName=item.last_name,
        country=item.country,
        streetLine1=item.street_line1,
        streetLine2=item.street_line2,
        suburb=item.suburb,
        state=item.state,
        postcode=item.postcode,
        email=item.email,
        phone=item.phone,
    )
    return schemas.BillingInfo(
        billingId=item.billing_id,
        cardNumber=item.card_number,
        expiryMonth=item.expiry_month,
        expiryYear=item.expiry_year,
        billingAddress=address,
    )


def delete_billing(user: models.User, billing_id: int):
    item = get_billing_model(billing_id, user)
    db.get().delete(item)


# ------------------------------------------------------------------------------------------------- #
# -------------------------------------- Validations ---------------------------------------------- #


def check_existing_billing(card_number: str, user_id: int, billing_id: int = None) -> bool:
    existing_billing_info = (
        db.get()
        .query(models.BillingInfo)
        .filter_by(user_id=user_id, card_number=card_number)
        .first()
    )
    if existing_billing_info:
        if billing_id and existing_billing_info.billing_id != billing_id:
            raise exceptions.NotUniqueException(
                f"Your account already has a payment method with cardnumber {card_number}."
            )
        return True
    return False
