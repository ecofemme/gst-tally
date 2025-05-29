import csv
import glob
import io
import os
import yaml
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime


def extract_order_amounts_from_paypal_csv(csv_file_path: str) -> Tuple[Dict[str, Decimal], Set[str]]:
    """
    Extract WooCommerce order IDs and their INR totals from PayPal CSV.
    
    Process:
    1. Read all transactions sequentially
    2. Track payments by currency between withdrawals
    3. When withdrawal occurs, calculate exchange rate and apply to all pending payments
    4. Track refunds/reversals for affected orders
    
    Returns:
        Tuple of (order_amounts, refunded_orders)
        - order_amounts: Dictionary mapping order_id to INR amount
        - refunded_orders: Set of order IDs that have been refunded/reversed
    """
    order_amounts = {}
    pending_payments = {}  # currency -> list of payment info
    refunded_orders = set()
    
    # Track withdrawal sequences to match with currency conversions
    pending_withdrawal = None
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                transaction_type = row.get('Type', '').strip()
                currency = row.get('Currency', '').strip()
                status = row.get('Status', '').strip()
                
                # Skip pending transactions
                if status == 'Pending':
                    continue
                
                # Process Express Checkout Payments
                if transaction_type == 'Express Checkout Payment' and status == 'Completed':
                    invoice_number = row.get('Invoice Number', '').strip()
                    if invoice_number and invoice_number.startswith('WC-'):
                        order_id = invoice_number.replace('WC-', '')
                        try:
                            gross_amount = Decimal(row.get('Gross', '0').replace(',', ''))
                            if gross_amount > 0 and currency != 'INR':
                                # Initialize currency list if needed
                                if currency not in pending_payments:
                                    pending_payments[currency] = []
                                
                                pending_payments[currency].append({
                                    'order_id': order_id,
                                    'gross_amount': gross_amount,
                                    'transaction_id': row.get('Transaction ID', ''),
                                    'date': row.get('Date', '')
                                })
                        except (InvalidOperation, ValueError) as e:
                            print(f"Error parsing amount for order {invoice_number}: {e}")
                
                # Process User Initiated Withdrawals
                elif transaction_type == 'User Initiated Withdrawal' and currency == 'INR':
                    try:
                        inr_amount = abs(Decimal(row.get('Gross', '0').replace(',', '')))
                        if inr_amount > 0:
                            pending_withdrawal = {
                                'inr_amount': inr_amount,
                                'transaction_id': row.get('Transaction ID', '')
                            }
                    except (InvalidOperation, ValueError) as e:
                        print(f"Error parsing withdrawal amount: {e}")
                
                # Process Currency Conversions
                elif transaction_type == 'General Currency Conversion' and pending_withdrawal:
                    try:
                        amount = Decimal(row.get('Gross', '0').replace(',', ''))
                        reference_txn = row.get('Reference Txn ID', '')
                        
                        # Look for the foreign currency amount (negative)
                        if amount < 0 and currency != 'INR' and reference_txn == pending_withdrawal['transaction_id']:
                            foreign_amount = abs(amount)
                            exchange_rate = pending_withdrawal['inr_amount'] / foreign_amount
                            
                            # Apply exchange rate to all pending payments in this currency
                            if currency in pending_payments:
                                for payment in pending_payments[currency]:
                                    inr_total = payment['gross_amount'] * exchange_rate
                                    order_amounts[payment['order_id']] = inr_total.quantize(Decimal('0.01'))
                                
                                # Clear processed payments
                                pending_payments[currency] = []
                            
                            # Clear the pending withdrawal
                            pending_withdrawal = None
                            
                    except (InvalidOperation, ValueError) as e:
                        print(f"Error processing currency conversion: {e}")
                
                # Process Payment Reversals
                elif transaction_type == 'Payment Reversal':
                    invoice_number = row.get('Invoice Number', '').strip()
                    if invoice_number and invoice_number.startswith('WC-'):
                        order_id = invoice_number.replace('WC-', '')
                        refunded_orders.add(order_id)
                        # Remove from order_amounts if it exists
                        if order_id in order_amounts:
                            del order_amounts[order_id]
    
    except FileNotFoundError:
        print(f"Error: PayPal CSV file '{csv_file_path}' not found!")
    except Exception as e:
        print(f"Error reading PayPal CSV file: {e}")
    
    # Report any unprocessed payments
    unprocessed_count = sum(len(payments) for payments in pending_payments.values())
    if unprocessed_count > 0:
        print(f"  Found {unprocessed_count} payments not yet withdrawn")
    
    return order_amounts, refunded_orders


def load_all_paypal_order_amounts(config_file: str = "config.yaml") -> Dict[str, Decimal]:
    """
    Load order amounts from all PayPal CSV files in the configured folder.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Dictionary of order_id -> INR amount (merged from all files)
    """
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        data_folder = config.get('data_folder')
        paypal_prefix = config.get('paypal_prefix', 'Download')  # Default prefix if not specified
        
        if not data_folder:
            print("Warning: 'data_folder' must be specified in config")
            return {}
        
        if data_folder.startswith('~'):
            data_folder = os.path.expanduser(data_folder)
        
        if not os.path.exists(data_folder):
            print(f"Error: Data folder '{data_folder}' does not exist!")
            return {}
        
        # Find all PayPal CSV files
        csv_file_pattern = os.path.join(data_folder, f"{paypal_prefix}*.CSV")  # Note: uppercase .CSV
        csv_files = glob.glob(csv_file_pattern)
        
        # Also check for lowercase .csv
        csv_file_pattern_lower = os.path.join(data_folder, f"{paypal_prefix}*.csv")
        csv_files.extend(glob.glob(csv_file_pattern_lower))
        
        # Remove duplicates if any
        csv_files = list(set(csv_files))
        
        if not csv_files:
            print(f"No PayPal CSV files found with '{paypal_prefix}' prefix in {data_folder}")
            return {}
        
        print(f"Found {len(csv_files)} PayPal CSV files to process:")
        for csv_file in csv_files:
            print(f"  - {os.path.basename(csv_file)}")
        
        all_order_amounts = {}
        all_refunded_orders = set()
        total_orders = 0
        
        for csv_file in csv_files:
            print(f"\nProcessing {os.path.basename(csv_file)}...")
            file_amounts, file_refunds = extract_order_amounts_from_paypal_csv(csv_file)
            
            # Check for duplicate orders across files
            duplicates = set(all_order_amounts.keys()) & set(file_amounts.keys())
            if duplicates:
                print(f"Warning: Found duplicate order IDs: {duplicates}")
                for order_id in duplicates:
                    if all_order_amounts[order_id] != file_amounts[order_id]:
                        print(f"  Order {order_id}: {all_order_amounts[order_id]} vs {file_amounts[order_id]}")
            
            all_order_amounts.update(file_amounts)
            all_refunded_orders.update(file_refunds)
            total_orders += len(file_amounts)
            print(f"  Loaded {len(file_amounts)} orders from this file")
            if file_refunds:
                print(f"  Found {len(file_refunds)} refunded orders")
        
        print(f"\nTotal: Loaded amounts for {len(all_order_amounts)} unique orders from {len(csv_files)} files")
        if all_refunded_orders:
            print(f"Total refunded orders: {len(all_refunded_orders)}")
        
        return all_order_amounts
        
    except Exception as e:
        print(f"Error loading PayPal order amounts from config: {e}")
        return {}


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Single file mode
        csv_file = sys.argv[1]
        order_amounts, refunded = extract_order_amounts_from_paypal_csv(csv_file)
        
        print("\nOrder amounts summary:")
        total_inr = sum(order_amounts.values())
        print(f"Total orders: {len(order_amounts)}")
        print(f"Total INR value: {total_inr:,.2f}")
        if refunded:
            print(f"Refunded orders: {refunded}")
    else:
        # Load from config
        order_amounts = load_all_paypal_order_amounts()
        if order_amounts:
            total_inr = sum(order_amounts.values())
            print(f"\nTotal INR value across all files: {total_inr:,.2f}")