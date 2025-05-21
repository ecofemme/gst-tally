from decimal import Decimal


def get_gst_ledgers(gst_rate, is_domestic):
    if not is_domestic or gst_rate <= Decimal("0"):
        return None
    rate_percent = gst_rate * Decimal("100")
    cgst_rate_percent = rate_percent / Decimal("2")
    sgst_rate_percent = cgst_rate_percent
    cgst_str = (
        str(cgst_rate_percent).rstrip("0").rstrip(".")
        if "." in str(cgst_rate_percent)
        else str(cgst_rate_percent)
    )
    sgst_str = (
        str(sgst_rate_percent).rstrip("0").rstrip(".")
        if "." in str(sgst_rate_percent)
        else str(sgst_rate_percent)
    )
    return {
        "cgst_ledger": f"CGST Collected @ {cgst_str}%",
        "sgst_ledger": f"SGST Collected @ {sgst_str}%",
    }


def get_sales_ledger(gst_rate, is_domestic):
    if not is_domestic:
        return "Export Sales"
    elif gst_rate > Decimal("0"):
        rate_percent = gst_rate * Decimal("100")
        return f"Local GST Sales @ {rate_percent:.0f}%"
    else:
        return "Local Exempt Sales"


def get_party_ledger(country):
    if country == "IN":
        return "Online Shop Domestic"
    else:
        return "ONLINE SHOP INTERNATIONAL"
