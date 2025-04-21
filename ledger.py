def get_gst_ledgers(gst_rate, is_domestic):
    if not is_domestic or gst_rate <= 0:
        return None
    rate_percent = gst_rate * 100
    cgst_rate_percent = rate_percent / 2
    sgst_rate_percent = cgst_rate_percent
    return {
        "cgst_ledger": f"CGST Collected @ {cgst_rate_percent:.0f}%",
        "sgst_ledger": f"SGST Collected @ {sgst_rate_percent:.0f}%"
    }


def get_sales_ledger(gst_rate, is_domestic):
    if not is_domestic:
        return "Export Sales"
    elif gst_rate > 0:
        rate_percent = gst_rate * 100
        return f"Local GST Sales @ {rate_percent:.0f}%"
    else:
        return "Local Exempt Sales"


def get_party_ledger(country):
    if country == "IN":
        return "Online Shop Domestic"
    else:
        return "ONLINE SHOP INTERNATIONAL"