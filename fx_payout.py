import csv
import glob
import os
import yaml
from decimal import Decimal, InvalidOperation
from typing import Dict


def extract_order_amounts_from_payout_csv(csv_file_path: str) -> Dict[str, Decimal]:
    """
    Extract order amounts from a single payment processor payout CSV file.

    Args:
        csv_file_path: Path to the payout CSV file

    Returns:
        Dictionary mapping WooCommerce Order ID to amount (always in INR)
    """
    order_amounts = {}
    try:
        with open(csv_file_path, "r", encoding="utf-8") as f:
            content = f.read()
        sections = content.strip().split("\n\n")
        if len(sections) < 2:
            print(f"Warning: Expected two sections in {csv_file_path}, found only one")
            return order_amounts
        transaction_lines = sections[1].strip().split("\n")
        if not transaction_lines:
            print(f"Warning: No transaction data found in {csv_file_path}")
            return order_amounts
        transaction_reader = csv.DictReader(transaction_lines)
        for row in transaction_reader:
            try:
                order_id_field = row.get("Order ID", "").strip()
                amount_str = row.get("Amount", "").strip()
                if not order_id_field or not amount_str:
                    continue
                if "_" in order_id_field:
                    woo_order_id = order_id_field.split("_")[0]
                else:
                    woo_order_id = order_id_field
                amount = Decimal(amount_str.replace(",", ""))
                order_amounts[woo_order_id] = amount
            except (InvalidOperation, ValueError) as e:
                print(
                    f"Error processing transaction row for order {order_id_field} in {csv_file_path}: {e}"
                )
                continue
    except FileNotFoundError:
        print(f"Error: Payout CSV file '{csv_file_path}' not found!")
    except Exception as e:
        print(f"Error reading payout CSV file {csv_file_path}: {e}")
    return order_amounts


def load_all_order_amounts_from_config(
    config_file: str = "config.yaml",
) -> Dict[str, Decimal]:
    """
    Load order amounts from all payout CSV files in the configured folder.

    Args:
        config_file: Path to configuration file

    Returns:
        Dictionary of amounts by WooCommerce Order ID (merged from all files)
    """
    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        data_folder = config.get("data_folder")
        payout_prefix = config.get("payout_prefix")
        if not data_folder or not payout_prefix:
            print(
                "Warning: 'data_folder' and 'payout_prefix' must be specified in config"
            )
            return {}
        if data_folder.startswith("~"):
            data_folder = os.path.expanduser(data_folder)
        if not os.path.exists(data_folder):
            print(f"Error: Data folder '{data_folder}' does not exist!")
            return {}
        csv_file_pattern = os.path.join(data_folder, f"{payout_prefix}*.csv")
        csv_files = glob.glob(csv_file_pattern)
        if not csv_files:
            print(
                f"No payout CSV files found with '{payout_prefix}' prefix in {data_folder}"
            )
            return {}
        print(f"Found {len(csv_files)} payout CSV files to process:")
        for csv_file in csv_files:
            print(f"  - {os.path.basename(csv_file)}")
        all_order_amounts = {}
        total_orders = 0
        for csv_file in csv_files:
            print(f"\nProcessing {os.path.basename(csv_file)}...")
            file_amounts = extract_order_amounts_from_payout_csv(csv_file)
            duplicates = set(all_order_amounts.keys()) & set(file_amounts.keys())
            if duplicates:
                print(f"Warning: Found duplicate order IDs: {duplicates}")
                for order_id in duplicates:
                    if all_order_amounts[order_id] != file_amounts[order_id]:
                        print(
                            f"  Order {order_id}: {all_order_amounts[order_id]} vs {file_amounts[order_id]}"
                        )
            all_order_amounts.update(file_amounts)
            total_orders += len(file_amounts)
            print(f"  Loaded {len(file_amounts)} orders from this file")
        print(
            f"\nTotal: Loaded amounts for {len(all_order_amounts)} unique orders from {len(csv_files)} files"
        )
        return all_order_amounts
    except Exception as e:
        print(f"Error loading order amounts from config: {e}")
        return {}
