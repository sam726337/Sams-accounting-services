from __future__ import annotations

import random
import re
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


def extract_gst_rate_from_stock_item_name(stock_item_name: str) -> Decimal:
    stock_name = (stock_item_name or "").strip()
    if not stock_name:
        return Decimal("0.00")

    match = re.search(r"(\d+(?:\.\d+)?)\s*%", stock_name)
    if not match:
        match = re.search(r"(\d+(?:\.\d+)?)", stock_name)
    if not match:
        return Decimal("0.00")

    return Decimal(match.group(1)).quantize(Decimal("0.01"))


def split_gst_rate(total_gst_rate: Decimal, *, has_cgst: bool, has_sgst: bool) -> tuple[Decimal, Decimal]:
    total_rate = Decimal(total_gst_rate or "0.00").quantize(Decimal("0.01"))

    if total_rate <= Decimal("0.00"):
        return Decimal("0.00"), Decimal("0.00")
    if has_cgst and has_sgst:
        half_rate = (total_rate / Decimal("2.00")).quantize(Decimal("0.01"))
        return half_rate, half_rate
    if has_cgst:
        return total_rate, Decimal("0.00")
    if has_sgst:
        return Decimal("0.00"), total_rate
    return Decimal("0.00"), Decimal("0.00")


def pick_spread_date(
    index: int,
    *,
    from_date: date,
    to_date: date,
    number_of_bills: int,
) -> date:
    date_range = (to_date - from_date).days
    if date_range == 0:
        return from_date
    step = date_range / max(number_of_bills - 1, 1)
    offset = round(step * index)
    return from_date + timedelta(days=min(offset, date_range))


def calculate_tax_components(
    base_amount: Decimal,
    *,
    cgst_rate: Decimal = Decimal("0.00"),
    sgst_rate: Decimal = Decimal("0.00"),
    has_round_off: bool,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    quant = Decimal("0.01")
    cgst_amount = (base_amount * (cgst_rate / Decimal("100.00"))).quantize(quant)
    sgst_amount = (base_amount * (sgst_rate / Decimal("100.00"))).quantize(quant)
    invoice_total = (base_amount + cgst_amount + sgst_amount).quantize(quant)
    round_off_amount = Decimal("0.00")
    if has_round_off:
        rounded_total = invoice_total.quantize(Decimal("1"), rounding=ROUND_HALF_UP).quantize(quant)
        round_off_amount = (rounded_total - invoice_total).quantize(quant)
    gross_amount = (invoice_total + round_off_amount).quantize(quant)
    return cgst_amount, sgst_amount, round_off_amount, gross_amount


def gross_amount_from_taxable(
    taxable_amount: Decimal,
    *,
    cgst_rate: Decimal = Decimal("0.00"),
    sgst_rate: Decimal = Decimal("0.00"),
    has_round_off: bool,
) -> Decimal:
    return calculate_tax_components(
        taxable_amount,
        cgst_rate=cgst_rate,
        sgst_rate=sgst_rate,
        has_round_off=has_round_off,
    )[3]


def split_random_sale_taxable_amounts(
    total_taxable_amount: Decimal,
    *,
    number_of_bills: int,
    min_amount: Decimal,
    max_amount: Decimal,
    cgst_rate: Decimal = Decimal("0.00"),
    sgst_rate: Decimal = Decimal("0.00"),
    has_round_off: bool,
    rng: random.Random | None = None,
    max_attempts: int = 25,
) -> list[Decimal]:
    quant = Decimal("0.01")
    rng = rng or random.Random()

    min_cents = int((min_amount * 100).to_integral_value())
    max_cents = int((max_amount * 100).to_integral_value())
    total_cents = int((total_taxable_amount * 100).to_integral_value())
    min_total_cents = min_cents * number_of_bills
    max_total_cents = max_cents * number_of_bills
    if not (min_total_cents <= total_cents <= max_total_cents):
        return [(total_taxable_amount / number_of_bills).quantize(quant) for _ in range(number_of_bills)]

    if number_of_bills <= 1:
        return [total_taxable_amount.quantize(quant)]

    extra_cents = total_cents - min_total_cents
    capacity_per_bill = max_cents - min_cents
    if capacity_per_bill <= 0:
        return [Decimal(min_cents) / Decimal("100") for _ in range(number_of_bills)]

    base_extra_cents = extra_cents // number_of_bills
    remainder_cents = extra_cents % number_of_bills
    amounts_cents = [min_cents + base_extra_cents for _ in range(number_of_bills)]
    if remainder_cents:
        bonus_indexes = rng.sample(range(number_of_bills), remainder_cents)
        for index in bonus_indexes:
            amounts_cents[index] += 1

    jitter_budget = max(number_of_bills * 12, extra_cents // 2)
    transfer_cap = max(1, capacity_per_bill // 6)
    for _ in range(min(max_attempts * number_of_bills, jitter_budget)):
        donor_candidates = [idx for idx, value in enumerate(amounts_cents) if value > min_cents]
        receiver_candidates = [idx for idx, value in enumerate(amounts_cents) if value < max_cents]
        if not donor_candidates or not receiver_candidates:
            break

        donor_index = rng.choice(donor_candidates)
        receiver_index = rng.choice(receiver_candidates)
        if donor_index == receiver_index:
            continue

        donor_available = amounts_cents[donor_index] - min_cents
        receiver_space = max_cents - amounts_cents[receiver_index]
        if donor_available <= 0 or receiver_space <= 0:
            continue

        max_transfer = min(donor_available, receiver_space, transfer_cap)
        if max_transfer <= 0:
            continue

        transfer = max(1, int(round(max_transfer * (rng.random() ** 0.35))))
        transfer = min(transfer, max_transfer)

        amounts_cents[donor_index] -= transfer
        amounts_cents[receiver_index] += transfer

    rng.shuffle(amounts_cents)
    return [(Decimal(c) / Decimal("100")).quantize(quant) for c in amounts_cents]


def spread_random_sale_dates(
    *,
    from_date: date,
    to_date: date,
    number_of_bills: int,
    rng: random.Random | None = None,
) -> list[date]:
    rng = rng or random.Random()
    date_range = (to_date - from_date).days
    if number_of_bills <= 1 or date_range <= 0:
        return [from_date for _ in range(number_of_bills)]

    offsets = [0, date_range]
    interior_slots = number_of_bills - 2
    if interior_slots > 0:
        possible_offsets = list(range(1, date_range))
        if len(possible_offsets) >= interior_slots:
            offsets.extend(rng.sample(possible_offsets, interior_slots))
        else:
            offsets.extend(rng.randint(1, date_range - 1) for _ in range(interior_slots))

    offsets.sort()
    return [from_date + timedelta(days=offset) for offset in offsets]


def build_random_sale_preview_entries(
    *,
    party_name: str,
    stock_item_name: str,
    sale_ledger: str,
    voucher_type: str,
    cash_bank_ledger: str,
    cgst_ledger: str,
    sgst_ledger: str,
    round_off_ledger: str,
    narration_prefix: str,
    from_date: date,
    to_date: date,
    number_of_bills: int,
    taxable_amount: Decimal,
    min_amount: Decimal,
    max_amount: Decimal,
    rng: random.Random | None = None,
) -> list[dict]:
    total_gst_rate = extract_gst_rate_from_stock_item_name(stock_item_name)
    cgst_rate, sgst_rate = split_gst_rate(
        total_gst_rate,
        has_cgst=bool(cgst_ledger.strip()),
        has_sgst=bool(sgst_ledger.strip()),
    )

    taxable_amounts = split_random_sale_taxable_amounts(
        taxable_amount,
        number_of_bills=number_of_bills,
        min_amount=min_amount,
        max_amount=max_amount,
        cgst_rate=cgst_rate,
        sgst_rate=sgst_rate,
        has_round_off=bool(round_off_ledger.strip()),
        rng=rng,
    )

    entry_dates = spread_random_sale_dates(
        from_date=from_date,
        to_date=to_date,
        number_of_bills=number_of_bills,
        rng=rng,
    )

    preview_entries: list[dict] = []
    for index, entry_taxable_amount in enumerate(taxable_amounts, start=1):
        cgst_amount, sgst_amount, round_off_amount, gross_amount = calculate_tax_components(
            entry_taxable_amount,
            cgst_rate=cgst_rate,
            sgst_rate=sgst_rate,
            has_round_off=bool(round_off_ledger.strip()),
        )
        preview_entries.append(
            {
                "bill_number": index,
                "voucher_date": entry_dates[index - 1],
                "party_name": party_name,
                "stock_item_name": stock_item_name,
                "sale_ledger": sale_ledger,
                "voucher_type": voucher_type,
                "cash_bank_ledger": cash_bank_ledger,
                "cgst_ledger": cgst_ledger,
                "sgst_ledger": sgst_ledger,
                "round_off_ledger": round_off_ledger,
                "taxable_amount": entry_taxable_amount,
                "cgst_amount": cgst_amount,
                "sgst_amount": sgst_amount,
                "round_off_amount": round_off_amount,
                "amount": gross_amount,
                "narration": f"{narration_prefix} {index} - {party_name} - {stock_item_name}",
            }
        )

    return preview_entries
