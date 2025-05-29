from typing import Dict
from decimal import Decimal
from pp_payout import load_all_paypal_order_amounts
from cc_payout import load_all_ccavenue_order_amounts


def load_all_order_amounts_from_config(
    config_file: str = "config.yaml",
) -> Dict[str, Decimal]:
    paypal_order_amounts = load_all_paypal_order_amounts(config_file)
    ccavenue_order_amounts = load_all_ccavenue_order_amounts(config_file)
    all_order_amounts = {}
    all_order_amounts.update(paypal_order_amounts)
    duplicates = set(all_order_amounts.keys()) & set(ccavenue_order_amounts.keys())
    if duplicates:
        print(
            f"Warning: Found duplicate order IDs between PayPal and CCAvenue: {duplicates}"
        )
        for order_id in duplicates:
            print(
                f"  Order {order_id}: Keeping PayPal amount {all_order_amounts[order_id]} vs CCAvenue {ccavenue_order_amounts[order_id]}"
            )
    for order_id, amount in ccavenue_order_amounts.items():
        if order_id not in all_order_amounts:
            all_order_amounts[order_id] = amount
    print(f"\nTotal: Loaded amounts for {len(all_order_amounts)} unique orders")
    return all_order_amounts
