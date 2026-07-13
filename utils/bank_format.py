from __future__ import annotations

from html import escape


def money(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ")


def rub(value: float) -> str:
    return f"{money(value)} ₽"


def account_tail(user: dict) -> str:
    z_id = str(user.get("passport", "0000")).replace("-", "")
    return z_id[-4:].rjust(4, "0")


def public_sender_name(user: dict) -> str:
    username = str(user.get("username") or "").strip()
    if username:
        return f"@{username}"
    return escape(str(user.get("name") or "клиент Z-Bank"))


def masked_client(user: dict) -> str:
    return f"клиент Z-Bank · Z-ID ****{account_tail(user)}"


def transfer_income_notice(sender: dict, receiver: dict, amount: float) -> str:
    balance = float(receiver.get("balances", {}).get("RUB", 0.0))
    return (
        "900-\n"
        f"Вы получили перевод от {public_sender_name(sender)}\n"
        f"Сумма: +{rub(amount)}\n"
        f"Счет: {account_tail(receiver)} · {rub(balance)}"
    )


def transfer_debit_notice(sender: dict, receiver: dict, amount: float) -> str:
    balance = float(sender.get("balances", {}).get("RUB", 0.0))
    return (
        "900-\n"
        f"Перевод: {masked_client(receiver)}\n"
        f"Сумма: -{rub(amount)}\n"
        f"Счет: {account_tail(sender)} · {rub(balance)}"
    )


def merchant_debit_notice(user: dict, merchant: str, amount: float) -> str:
    balance = float(user.get("balances", {}).get("RUB", 0.0))
    return (
        "900-\n"
        f"Списание: {merchant}\n"
        f"Сумма: -{rub(amount)}\n"
        f"Счет: {account_tail(user)} · {rub(balance)}"
    )


def merchant_credit_notice(user: dict, merchant: str, amount: float) -> str:
    balance = float(user.get("balances", {}).get("RUB", 0.0))
    return (
        "900-\n"
        f"Пополнение: {merchant}\n"
        f"Сумма: +{rub(amount)}\n"
        f"Счет: {account_tail(user)} · {rub(balance)}"
    )
