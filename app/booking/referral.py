from .. import constants, exceptions, models, schemas
from ..database import db


# --------------------------------------------------------------------------------------------- #
# -----------------------------  Referral Creation/Deletion ----------------------------------- #


def create_new_referral(referral_info: schemas.ReferralInfo, user: models.User) -> None:
    if not user.user_type == constants.HOST:
        raise exceptions.ForbiddenActionException("User cannot create a new referral code.")

    if referral_code_exists(referral_info.referralCode):
        raise exceptions.InvalidInputException(
            f"Cannot add referral code '{referral_info.referralCode}'. Referral code already exists."
        )

    if not referral_info.referralCode:
        raise exceptions.InvalidInputException("Cannot create an empty referral code.")

    if not (0 <= referral_info.percentageOff <= 100):
        raise exceptions.InvalidInputException("Discount percentage must be between 0 and 100 (%).")

    if not (0 <= referral_info.referrerCut <= 100):
        raise exceptions.InvalidInputException("Referer percentage cut must be between 0 and 100 (%).")

    new_referral_code = models.Referral(
        referral_code=referral_info.referralCode,
        host_id=user.user_id,
        percentage_off=referral_info.percentageOff,
        referrer_cut=referral_info.referrerCut,
        referrer_name=referral_info.name,
        pay_id_phone=referral_info.payIdPhone,
        is_active=True,
        amount_paid=0,
        amount_used=0,
    )

    db.get().add(new_referral_code)


def deactivate_referral(referral_code: str, user: models.User) -> None:
    if not user.user_type == constants.HOST:
        raise exceptions.ForbiddenActionException(f"User '{user.username}' is not a Host.")

    referral = get_referral(referral_code)
    if not referral.host_id == user.user_id:
        raise exceptions.ForbiddenAccessException(
            f"Host '{user.username}' does not have access to this referral code '{referral_code}'."
        )

    if not referral.is_active:
        raise exceptions.InvalidInputException(
            f"Cannot deactivate referral code '{referral_code}'. Referral code is already inactive."
        )

    referral.is_active = False


def reactivate_referral(referral_code: str, user: models.User) -> None:
    referral = get_referral(referral_code)

    if referral.host_id != user.user_id:
        raise exceptions.ForbiddenAccessException(f"User '{user.username}' cannot access this referral.")

    if referral.is_active:
        raise exceptions.InvalidInputException(
            f"Cannot add referral code '{referral_code}'. Referral code is already active."
        )

    referral.is_active = True


# --------------------------------------------------------------------------------------------- #
# -----------------------------------  Referral Getters --------------------------------------- #


def get_referral_discount(referral_code: str) -> schemas.Discount:
    referral = get_referral(referral_code)

    if not referral.is_active:
        raise exceptions.InvalidInputException(f"Referral code '{referral_code}' has expired.")

    return referral.percentage_off


def get_referral_info(referral: models.Referral) -> schemas.ReferralInfo:
    return schemas.ReferralInfo(
        referralCode=referral.referral_code,
        percentageOff=referral.percentage_off,
        referrerCut=referral.referrer_cut,
        name=referral.referrer_name,
        payIdPhone=referral.pay_id_phone,
        isActive=referral.is_active,
        amountPaid=referral.amount_paid,
        noUsed=referral.amount_used,
    )


def get_host_referrals(user: models.User) -> schemas.HostReferrals:
    if not user.user_type == constants.HOST:
        raise exceptions.ForbiddenActionException(f"User '{user.username}' is not a Host.")

    active_referrals = user.host.referrals.filter(models.Referral.is_active.is_(True)).all()
    inactive_referrals = user.host.referrals.filter(models.Referral.is_active.is_(False)).all()

    return schemas.HostReferrals(
        activeReferrals=[get_referral_info(referral) for referral in active_referrals],
        inactiveReferrals=[get_referral_info(referral) for referral in inactive_referrals],
    )


def get_referral(referral_code: str) -> models.Referral:
    try:
        return (
            db.get()
            .query(models.Referral)
            .filter(models.Referral.referral_code == referral_code)
            .one()
        )
    except Exception:
        raise exceptions.NotFoundException(f"Referral code '{referral_code}' is invalid.")


# --------------------------------------------------------------------------------------------- #
# ------------------------------------  Helper Functions -------------------------------------- #


def apply_discount_and_referral_fee(referral_code: str, total_cost: float) -> (float, float):
    try:
        referral = get_referral(referral_code)
        total_cost -= total_cost * referral.percentage_off
        referrer_fee = total_cost * referral.referrer_cut
        referral.amount_paid += referrer_fee
        referral.amount_used += 1

    except Exception:
        referrer_fee = 0

    host_cut = total_cost - referrer_fee

    return (total_cost, host_cut)


def refund_referral_fee(referral: models.Referral, total_cost: float) -> float:
    if not referral:
        return total_cost

    referrer_fee = total_cost * referral.referrer_cut
    referral.amount_paid -= referrer_fee
    referral.amount_used -= 1

    return total_cost - referrer_fee


def referral_code_exists(referral_code: str) -> bool:
    try:
        return (
            db.get()
            .query(models.Referral)
            .filter(models.Referral.referral_code == referral_code)
            .first()
            is not None
        )
    except Exception:
        raise exceptions.BadGatewayException()
