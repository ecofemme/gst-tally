import csv
import glob
import os
import yaml
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Set, Tuple


def extract_order_amounts_from_paypal_csv(
    csv_file_path: str,
) -> Tuple[Dict[str, Decimal], Set[str], List[Dict]]:
    """
    Extract WooCommerce order IDs and their INR totals from PayPal CSV, with details for verification.

    Process:
    1. Read all transactions sequentially
    2. Track payments by currency between withdrawals
    3. When withdrawal occurs, calculate exchange rate and apply to all pending payments
    4. Track refunds/reversals for affected orders
    5. Collect detailed order information for manual cross-checking

    Returns:
        Tuple of (order_amounts, refunded_orders, order_details)
        - order_amounts: Dictionary mapping order_id to INR amount
        - refunded_orders: Set of order IDs that have been refunded/reversed
        - order_details: List of dictionaries with order details for verification
    """
    order_amounts = {}
    pending_payments = {}
    refunded_orders = set()
    order_details = []  # List to store detailed order info for verification
    pending_withdrawal = None
    try:
        with open(csv_file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            print(f"Headers in {csv_file_path}: {reader.fieldnames}")
            for row in reader:
                transaction_type = row.get("Type", "").strip()
                currency = row.get("Currency", "").strip()
                status = row.get("Status", "").strip()
                if status == "Pending":
                    continue
                if (
                    transaction_type == "Express Checkout Payment"
                    and status == "Completed"
                ):
                    custom_number = row.get("Custom Number", "").strip()
                    transaction_id = row.get("Transaction ID", "").strip()
                    if custom_number:
                        order_id = custom_number
                        try:
                            gross_amount = Decimal(
                                row.get("Gross", "0").replace(",", "")
                            )
                            if gross_amount > 0 and currency != "INR":
                                if currency not in pending_payments:
                                    pending_payments[currency] = []
                                payment_info = {
                                    "order_id": order_id,
                                    "gross_amount": gross_amount,
                                    "transaction_id": transaction_id,
                                    "date": row.get("Date", ""),
                                    "currency": currency,
                                }
                                pending_payments[currency].append(payment_info)
                                order_details.append(
                                    {
                                        "order_id": order_id,
                                        "currency": currency,
                                        "gross_amount": str(gross_amount),
                                        "inr_amount": "Pending",
                                        "transaction_id": transaction_id,
                                        "date": row.get("Date", ""),
                                        "status": "Pending Conversion",
                                    }
                                )
                        except (InvalidOperation, ValueError) as e:
                            print(f"Error parsing amount for order {order_id}: {e}")
                elif (
                    transaction_type == "User Initiated Withdrawal"
                    and currency == "INR"
                ):
                    try:
                        inr_amount = abs(
                            Decimal(row.get("Gross", "0").replace(",", ""))
                        )
                        if inr_amount > 0:
                            pending_withdrawal = {
                                "inr_amount": inr_amount,
                                "transaction_id": row.get("Transaction ID", ""),
                            }
                    except (InvalidOperation, ValueError) as e:
                        print(f"Error parsing withdrawal amount: {e}")
                elif (
                    transaction_type == "General Currency Conversion"
                    and pending_withdrawal
                ):
                    try:
                        amount = Decimal(row.get("Gross", "0").replace(",", ""))
                        reference_txn = row.get("Reference Txn ID", "")
                        if (
                            amount < 0
                            and currency != "INR"
                            and reference_txn == pending_withdrawal["transaction_id"]
                        ):
                            foreign_amount = abs(amount)
                            exchange_rate = (
                                pending_withdrawal["inr_amount"] / foreign_amount
                            )
                            if currency in pending_payments:
                                for payment in pending_payments[currency]:
                                    inr_total = payment["gross_amount"] * exchange_rate
                                    order_amounts[payment["order_id"]] = (
                                        inr_total.quantize(Decimal("0.01"))
                                    )
                                    for detail in order_details:
                                        if (
                                            detail["order_id"] == payment["order_id"]
                                            and detail["status"] == "Pending Conversion"
                                        ):
                                            detail["inr_amount"] = str(
                                                inr_total.quantize(Decimal("0.01"))
                                            )
                                            detail["status"] = "Converted"
                                            detail["exchange_rate"] = str(exchange_rate)
                                pending_payments[currency] = []
                            pending_withdrawal = None
                    except (InvalidOperation, ValueError) as e:
                        print(f"Error processing currency conversion: {e}")
                elif transaction_type == "Payment Reversal":
                    custom_number = row.get("Custom Number", "").strip()
                    if custom_number:
                        order_id = custom_number
                        refunded_orders.add(order_id)
                        if order_id in order_amounts:
                            del order_amounts[order_id]
                        for detail in order_details:
                            if detail["order_id"] == order_id:
                                detail["status"] = "Refunded"
    except FileNotFoundError:
        print(f"Error: PayPal CSV file '{csv_file_path}' not found!")
    except Exception as e:
        print(f"Error reading PayPal CSV file: {e}")
    unprocessed_count = sum(len(payments) for payments in pending_payments.values())
    if unprocessed_count > 0:
        print(f"  Found {unprocessed_count} payments not yet withdrawn")
    return order_amounts, refunded_orders, order_details


def load_all_paypal_order_amounts(
    config_file: str = "config.yaml",
) -> Tuple[Dict[str, Decimal], List[Dict]]:
    """
    Load order amounts from all PayPal CSV files in the configured folder.

    Args:
        config_file: Path to configuration file

    Returns:
        Tuple of (order_amounts, order_details)
        - order_amounts: Dictionary of order_id -> INR amount (merged from all files)
        - order_details: List of dictionaries with detailed order info for verification
    """
    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        data_folder = config.get("data_folder")
        paypal_prefix = config.get("paypal_prefix", "Download")
        if not data_folder:
            print("Warning: 'data_folder' must be specified in config")
            return {}, []
        if data_folder.startswith("~"):
            data_folder = os.path.expanduser(data_folder)
        if not os.path.exists(data_folder):
            print(f"Error: Data folder '{data_folder}' does not exist!")
            return {}, []
        csv_file_pattern = os.path.join(
            data_folder, f"{paypal_prefix}*.CSV"
        )  # Note: uppercase .CSV
        csv_files = glob.glob(csv_file_pattern)
        csv_file_pattern_lower = os.path.join(data_folder, f"{paypal_prefix}*.csv")
        csv_files.extend(glob.glob(csv_file_pattern_lower))
        csv_files = list(set(csv_files))
        if not csv_files:
            print(
                f"No PayPal CSV files found with '{paypal_prefix}' prefix in {data_folder}"
            )
            return {}, []
        print(f"Found {len(csv_files)} PayPal CSV files to process:")
        for csv_file in csv_files:
            print(f"  - {os.path.basename(csv_file)}")
        all_order_amounts = {}
        all_refunded_orders = set()
        all_order_details = []
        total_orders = 0
        for csv_file in csv_files:
            print(f"\nProcessing {os.path.basename(csv_file)}...")
            file_amounts, file_refunds, file_details = (
                extract_order_amounts_from_paypal_csv(csv_file)
            )
            duplicates = set(all_order_amounts.keys()) & set(file_amounts.keys())
            if duplicates:
                print(f"Warning: Found duplicate order IDs: {duplicates}")
                for order_id in duplicates:
                    if all_order_amounts[order_id] != file_amounts[order_id]:
                        print(
                            f"  Order {order_id}: {all_order_amounts[order_id]} vs {file_amounts[order_id]}"
                        )
            all_order_amounts.update(file_amounts)
            all_refunded_orders.update(file_refunds)
            all_order_details.extend(file_details)
            total_orders += len(file_amounts)
            print(f"  Loaded {len(file_amounts)} orders from this file")
            if file_refunds:
                print(f"  Found {len(file_refunds)} refunded orders")
        print(
            f"\nTotal: Loaded amounts for {len(all_order_amounts)} unique orders from {len(csv_files)} files"
        )
        if all_refunded_orders:
            print(f"Total refunded orders: {len(all_refunded_orders)}")
        return all_order_amounts, all_order_details
    except Exception as e:
        print(f"Error loading PayPal order amounts from config: {e}")
        return {}, []


def save_order_details(data_folder: str, order_details: List[Dict]):
    """
    Save order details to a CSV file for manual cross-checking.

    Args:
        data_folder: Path to the data folder
        order_details: List of dictionaries containing order details
    """
    if not order_details:
        print("No order details to save.")
        return
    output_file = os.path.join(data_folder, "paypal_orders_summary.csv")
    fieldnames = [
        "order_id",
        "currency",
        "gross_amount",
        "inr_amount",
        "exchange_rate",
        "transaction_id",
        "date",
        "status",
    ]
    try:
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for detail in order_details:
                row = {field: detail.get(field, "") for field in fieldnames}
                writer.writerow(row)
        print(f"Saved {len(order_details)} order details to {output_file}")
    except Exception as e:
        print(f"Error saving order details to {output_file}: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        order_amounts, refunded, order_details = extract_order_amounts_from_paypal_csv(
            csv_file
        )
        print("\nOrder amounts summary:")
        total_inr = sum(order_amounts.values())
        print(f"Total orders: {len(order_amounts)}")
        print(f"Total INR value: {total_inr:,.2f}")
        if refunded:
            print(f"Refunded orders: {refunded}")
        if order_details:
            print(f"Order details collected: {len(order_details)}")
    else:
        order_amounts, order_details = load_all_paypal_order_amounts()
        if order_amounts:
            total_inr = sum(order_amounts.values())
            print(f"\nTotal INR value across all files: {total_inr:,.2f}")
        if order_details:
            with open("config.yaml", "r") as f:
                config = yaml.safe_load(f)
            data_folder = config.get("data_folder")
            if data_folder and data_folder.startswith("~"):
                data_folder = os.path.expanduser(data_folder)
            save_order_details(data_folder, order_details)
