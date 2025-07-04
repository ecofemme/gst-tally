import argparse
import csv
import glob
import json
import os
import xml.etree.ElementTree as ET
import yaml
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from fx_payout import load_all_order_amounts_from_config

from ledger import get_gst_ledgers, get_party_ledger, get_sales_ledger

def safe_decimal_conversion(value, field_name="field", default="0"):
    if not value or not value.strip():
        return Decimal(default)
    try:
        return Decimal(value.replace(",", ""))
    except (InvalidOperation, ValueError) as e:
        print(f"Warning: Invalid {field_name} value '{value}', using {default}")
        return Decimal(default)


def load_config(config_file="config.yaml"):
    if not os.path.exists(config_file):
        print(f"Error: Configuration file '{config_file}' not found!")
        return None
    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        required_fields = [
            "woo_prefix",
            "tally_prefix",
            "data_folder",
            "tally_products_file",
            "sku_mapping_file",
            "product_prices_file",
        ]
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            print(
                f"Error: Missing required configuration fields: {', '.join(missing_fields)}"
            )
            return None
        if config["data_folder"].startswith("~"):
            config["data_folder"] = os.path.expanduser(config["data_folder"])
        if not os.path.isabs(config["data_folder"]):
            print(
                f"Error: data_folder '{config['data_folder']}' must be an absolute path!"
            )
            return None
        if not os.path.exists(config["data_folder"]):
            print(f"Error: Data folder '{config['data_folder']}' does not exist!")
            return None
        return config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None


def load_tally_products(tally_products_file):
    tally_products = {}
    try:
        with open(tally_products_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            print("Tally Products CSV Headers Found:", reader.fieldnames)
            for row in reader:
                tally_name = row["Tally Name"].strip()
                gst_percentage = row["GST Percentage"].strip()
                godown_name = row["Godown Name"].strip()
                gst_rate = Decimal(gst_percentage.replace("%", "")) / Decimal("100")
                tally_products[tally_name] = {
                    "gst_rate": gst_rate,
                    "godown_name": godown_name,
                }
        print(f"Loaded {len(tally_products)} tally products from {tally_products_file}")
        return tally_products
    except FileNotFoundError:
        print(f"Error: Tally products file '{tally_products_file}' not found!")
        return {}
    except Exception as e:
        print(f"Error loading tally products file: {e}")
        return {}


def load_product_prices(product_prices_file):
    product_prices = {}
    try:
        with open(product_prices_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            print("Product Prices CSV Headers Found:", reader.fieldnames)
            required_fields = ["Tally Name", "Normal Price"]
            missing_fields = [
                field for field in required_fields if field not in reader.fieldnames
            ]
            if missing_fields:
                print(
                    f"Error: Missing required fields in product prices CSV: {', '.join(missing_fields)}"
                )
                return {}
            for row in reader:
                tally_name = row["Tally Name"].strip()
                try:
                    normal_price = Decimal(row["Normal Price"])
                    if normal_price <= Decimal("0"):
                        print(
                            f"Error: Normal price for '{tally_name}' must be positive"
                        )
                        continue
                    product_prices[tally_name] = normal_price
                except InvalidOperation:
                    print(
                        f"Error: Invalid price for product '{tally_name}': {row['Normal Price']}"
                    )
        print(f"Loaded {len(product_prices)} product prices from {product_prices_file}")
        return product_prices
    except FileNotFoundError:
        print(f"Error: Product prices file '{product_prices_file}' not found!")
        return {}
    except Exception as e:
        print(f"Error loading product prices file: {e}")
        return {}


def load_sku_mapping(sku_mapping_file):
    sku_mapping = {}
    try:
        with open(sku_mapping_file, "r", encoding="utf-8") as f:
            sku_mapping = json.load(f)
        print(f"Loaded {len(sku_mapping)} SKU mappings from {sku_mapping_file}")
        return sku_mapping
    except FileNotFoundError:
        print(f"Error: SKU mapping file '{sku_mapping_file}' not found!")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from '{sku_mapping_file}': {e}")
        return {}
    except Exception as e:
        print(f"Error loading SKU mapping file: {e}")
        return {}


def get_tally_products_by_sku(sku, sku_mapping):
    if sku and sku.strip() in sku_mapping:
        return sku_mapping[sku.strip()]
    else:
        print(f"Warning: SKU '{sku}' not found in mapping")
        return []


def round_decimal(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def read_woo_csv(
    data_folder, csv_file, sku_mapping, tally_products, product_prices, payout_amounts
):
    file_path = os.path.join(data_folder, csv_file)
    sales_data = {}
    missing_payout_orders = []
    try:
        with open(file_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            print("CSV Headers Found:", reader.fieldnames)
            for row in reader:
                try:
                    if row["Order Status"].lower() != "wc-completed":
                        continue
                    order_id = row["Order ID"]
                    if order_id not in sales_data:
                        sale_date = datetime.strptime(
                            row["Order Date"], "%Y-%m-%d %H:%M:%S"
                        )
                        customer_name = (
                            f"{row['Billing First Name']} {row['Billing Last Name']}".strip()
                            or "Unknown Customer"
                        )
                        customer_phone = row["Billing Phone"] or "N/A"
                        customer_email = row["Billing Email Address"] or "N/A"
                        original_amount = safe_decimal_conversion(
                            row["Order Total"], "Order Total"
                        )
                        order_currency = row.get("Order Currency", "").strip()
                        original_shipping_cost = safe_decimal_conversion(
                            row.get("Shipping Cost", ""), "Shipping Cost"
                        )
                        total_fee_str = row.get("Total Fee Amount", "0").strip()
                        if not total_fee_str:
                            print(
                                f"Warning: Blank Total Fee Amount for order {order_id}, defaulting to 0"
                            )
                            original_donation_amount = Decimal("0")
                        else:
                            original_donation_amount = safe_decimal_conversion(
                                row.get("Total Fee Amount", ""), "Total Fee Amount"
                            )
                        country = row["Billing Country"]
                        party_ledger = get_party_ledger(country)
                        is_domestic = country == "IN"
                        conversion_ratio = Decimal("1.0")
                        final_amount = original_amount
                        final_shipping_cost = original_shipping_cost
                        final_donation_amount = original_donation_amount
                        if order_currency and order_currency != "INR":
                            payout_amount = payout_amounts.get(order_id)
                            if payout_amount:
                                conversion_ratio = payout_amount / original_amount
                                final_amount = payout_amount
                                final_shipping_cost = (
                                    original_shipping_cost * conversion_ratio
                                )
                                final_donation_amount = (
                                    original_donation_amount * conversion_ratio
                                )
                                print(
                                    f"Order {order_id}: Converting {order_currency} to INR"
                                    f" (ratio: {conversion_ratio:.6f})"
                                    f" - Original: {original_amount} {order_currency}"
                                    f" - INR: {final_amount} INR"
                                )
                            else:
                                print(
                                    f"Warning: No payout amount found for foreign currency order {order_id} ({order_currency})"
                                )
                                missing_payout_orders.append(
                                    {
                                        "order_id": order_id,
                                        "order_currency": order_currency,
                                        "woo_amount": original_amount,
                                        "customer_name": customer_name,
                                        "order_date": row["Order Date"],
                                        "country": country,
                                    }
                                )
                                continue
                        narration_parts = [
                            f"Customer: {customer_name}",
                            f"Phone: {customer_phone}",
                            f"Email: {customer_email}",
                        ]
                        if order_currency and order_currency != "INR":
                            narration_parts.append(
                                f"FX Rate: {conversion_ratio:.6f} ({order_currency} to INR)"
                            )
                        sales_data[order_id] = {
                            "date": sale_date,
                            "amount": final_amount,
                            "original_amount": original_amount,
                            "order_currency": order_currency,
                            "conversion_ratio": conversion_ratio,
                            "shipping_cost": final_shipping_cost,
                            "donation_amount": final_donation_amount,
                            "voucher_number": order_id,
                            "products": [],
                            "narration": ", ".join(narration_parts),
                            "party_ledger": party_ledger,
                            "is_domestic": is_domestic,
                        }
                    sku = row["SKU"].strip() if "SKU" in row else ""
                    tally_names = get_tally_products_by_sku(sku, sku_mapping)
                    quantity = int(
                        safe_decimal_conversion(
                            row.get("Quantity", ""), "Quantity", "1"
                        )
                    )
                    original_item_cost = safe_decimal_conversion(
                        row.get("Item Cost", ""), "Item Cost"
                    )
                    converted_item_cost = (
                        original_item_cost * sales_data[order_id]["conversion_ratio"]
                    )
                    for tally_name in tally_names:
                        if tally_name in tally_products:
                            product_details = tally_products[tally_name]
                            gst_rate = product_details["gst_rate"]
                            godown_name = product_details["godown_name"]
                            gst_rate = (
                                gst_rate
                                if sales_data[order_id]["is_domestic"]
                                else Decimal("0.0")
                            )
                            ledger_name = get_sales_ledger(
                                gst_rate, sales_data[order_id]["is_domestic"]
                            )
                            if len(tally_names) > 1:
                                missing_prices = [
                                    name
                                    for name in tally_names
                                    if name not in product_prices
                                ]
                                if missing_prices:
                                    print(
                                        f"Error: Missing prices for products: {', '.join(missing_prices)}. "
                                        f"SKU '{sku}' requires prices for all mapped Tally products."
                                    )
                                    continue
                                normal_prices = {
                                    name: product_prices[name] for name in tally_names
                                }
                                total_normal_price = sum(normal_prices.values())
                                discount_ratio = (
                                    converted_item_cost / total_normal_price
                                )
                                product_base_cost = (
                                    normal_prices[tally_name] * discount_ratio
                                )
                            else:
                                product_base_cost = converted_item_cost
                            base_rate = round_decimal(
                                product_base_cost / (Decimal("1") + gst_rate)
                                if gst_rate > Decimal("0")
                                else product_base_cost
                            )
                            total_base = round_decimal(
                                base_rate * Decimal(str(quantity))
                            )
                            total_gst = round_decimal(
                                (product_base_cost - base_rate) * Decimal(str(quantity))
                                if gst_rate > Decimal("0")
                                else Decimal("0.0")
                            )
                            cgst_amount = round_decimal(
                                total_gst / Decimal("2")
                                if gst_rate > Decimal("0")
                                else Decimal("0.0")
                            )
                            sgst_amount = round_decimal(
                                total_gst / Decimal("2")
                                if gst_rate > Decimal("0")
                                else Decimal("0.0")
                            )
                            sales_data[order_id]["products"].append(
                                {
                                    "name": tally_name,
                                    "quantity": quantity,
                                    "base_rate": base_rate,
                                    "base_amount": total_base,
                                    "gst_rate": gst_rate,
                                    "cgst_amount": cgst_amount,
                                    "sgst_amount": sgst_amount,
                                    "ledger_name": ledger_name,
                                    "godown_name": godown_name,
                                    "original_item_cost": original_item_cost,
                                    "converted_item_cost": converted_item_cost,
                                }
                            )
                        else:
                            print(
                                f"Warning: Tally product '{tally_name}' not found in tally_products"
                            )
                except (KeyError, ValueError, InvalidOperation) as e:
                    print(
                        f"Error processing order {row.get('Order ID', 'unknown')}: {e}"
                    )
                    print(f"  Row data: {dict(row)}")
        return list(sales_data.values()), missing_payout_orders
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found!")
        return [], []
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return [], []


def create_tally_xml(data_folder, sales_data, base_name="Sales"):
    if not sales_data:
        print(f"No sales data to process.")
        return None
    print(f"Generating XML for {len(sales_data)} total orders...")
    envelope = ET.Element("ENVELOPE")
    header = ET.SubElement(envelope, "HEADER")
    ET.SubElement(header, "TALLYREQUEST").text = "Import Data"
    body = ET.SubElement(envelope, "BODY")
    import_data = ET.SubElement(body, "IMPORTDATA")
    request_desc = ET.SubElement(import_data, "REQUESTDESC")
    ET.SubElement(request_desc, "REPORTNAME").text = "All Vouchers"
    ET.SubElement(request_desc, "STATICVARIABLES").text = ""
    request_data = ET.SubElement(import_data, "REQUESTDATA")
    for sale in sales_data:
        tally_msg = ET.SubElement(request_data, "TALLYMESSAGE", xmlns="TallyDeveloper")
        voucher = ET.SubElement(
            tally_msg,
            "VOUCHER",
            VCHTYPE="Sales",
            ACTION="Create",
            OBJVIEW="Invoice Voucher View",
        )
        ET.SubElement(voucher, "DATE").text = sale["date"].strftime("%Y%m%d")
        ET.SubElement(voucher, "EFFECTIVEDATE").text = sale["date"].strftime("%Y%m%d")
        ET.SubElement(voucher, "VOUCHERTYPENAME").text = "Sales"
        ET.SubElement(voucher, "VOUCHERNUMBER").text = sale["voucher_number"]
        ET.SubElement(voucher, "PARTYLEDGERNAME").text = sale["party_ledger"]
        ET.SubElement(voucher, "CSTFORMISSUETYPE").text = ""
        ET.SubElement(voucher, "CSTFORMRECVTYPE").text = ""
        ET.SubElement(voucher, "FBTPAYMENTTYPE").text = "Default"
        ET.SubElement(voucher, "PERSISTEDVIEW").text = "Invoice Voucher View"
        ET.SubElement(voucher, "NARRATION").text = sale["narration"]

        sale_amount = round_decimal(sale["amount"])
        party_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
        ET.SubElement(party_entry, "LEDGERNAME").text = sale["party_ledger"]
        ET.SubElement(party_entry, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(party_entry, "AMOUNT").text = f"-{sale_amount}"

        total_entries_value = Decimal("0.0")

        if sale["shipping_cost"] > Decimal("0"):
            shipping_amount = round_decimal(sale["shipping_cost"])
            shipping_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
            ET.SubElement(
                shipping_entry, "LEDGERNAME"
            ).text = "Packing and Transport Charges Collected"
            ET.SubElement(shipping_entry, "ISDEEMEDPOSITIVE").text = "No"
            ET.SubElement(shipping_entry, "AMOUNT").text = str(shipping_amount)
            total_entries_value += shipping_amount
        if sale["donation_amount"] > Decimal("0"):
            donation_amount = round_decimal(sale["donation_amount"])
            donation_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
            ET.SubElement(donation_entry, "LEDGERNAME").text = "Pad for Pad scheme"
            ET.SubElement(donation_entry, "ISDEEMEDPOSITIVE").text = "No"
            ET.SubElement(donation_entry, "AMOUNT").text = str(donation_amount)
            total_entries_value += donation_amount

        for product in sale["products"]:
            if not product["godown_name"]:
                ledger_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
                ET.SubElement(ledger_entry, "LEDGERNAME").text = product["name"]
                ET.SubElement(ledger_entry, "ISDEEMEDPOSITIVE").text = "No"
                base_amount = round_decimal(product["base_amount"])
                ET.SubElement(ledger_entry, "AMOUNT").text = str(base_amount)
                total_entries_value += base_amount
            else:
                inventory_entry = ET.SubElement(voucher, "ALLINVENTORYENTRIES.LIST")
                ET.SubElement(inventory_entry, "STOCKITEMNAME").text = product["name"]
                ET.SubElement(inventory_entry, "ISDEEMEDPOSITIVE").text = "No"
                base_rate = round_decimal(product["base_rate"])
                base_amount = round_decimal(product["base_amount"])
                ET.SubElement(inventory_entry, "RATE").text = f"{base_rate}/Nos"
                ET.SubElement(inventory_entry, "AMOUNT").text = str(base_amount)
                ET.SubElement(
                    inventory_entry, "ACTUALQTY"
                ).text = f"{product['quantity']} Nos"
                ET.SubElement(
                    inventory_entry, "BILLEDQTY"
                ).text = f"{product['quantity']} Nos"
                ET.SubElement(inventory_entry, "GODOWNNAME").text = product[
                    "godown_name"
                ]
                accounting = ET.SubElement(
                    inventory_entry, "ACCOUNTINGALLOCATIONS.LIST"
                )
                ET.SubElement(accounting, "LEDGERNAME").text = product["ledger_name"]
                ET.SubElement(accounting, "ISDEEMEDPOSITIVE").text = "No"
                ET.SubElement(accounting, "AMOUNT").text = str(base_amount)
                total_entries_value += base_amount
        if sale["is_domestic"]:
            gst_rates_used = {}
            for product in sale["products"]:
                if product["gst_rate"] > Decimal("0"):
                    gst_rate = product["gst_rate"]
                    if gst_rate not in gst_rates_used:
                        gst_rates_used[gst_rate] = {
                            "cgst": Decimal("0"),
                            "sgst": Decimal("0"),
                        }
                    gst_rates_used[gst_rate]["cgst"] += product["cgst_amount"]
                    gst_rates_used[gst_rate]["sgst"] += product["sgst_amount"]
            for gst_rate, amounts in gst_rates_used.items():
                gst_ledgers = get_gst_ledgers(gst_rate, sale["is_domestic"])
                if amounts["cgst"] > Decimal("0"):
                    cgst_amount = round_decimal(amounts["cgst"])
                    cgst_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
                    ET.SubElement(cgst_entry, "LEDGERNAME").text = gst_ledgers[
                        "cgst_ledger"
                    ]
                    ET.SubElement(cgst_entry, "ISDEEMEDPOSITIVE").text = "No"
                    ET.SubElement(cgst_entry, "AMOUNT").text = str(cgst_amount)
                    total_entries_value += cgst_amount
                if amounts["sgst"] > Decimal("0"):
                    sgst_amount = round_decimal(amounts["sgst"])
                    sgst_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
                    ET.SubElement(sgst_entry, "LEDGERNAME").text = gst_ledgers[
                        "sgst_ledger"
                    ]
                    ET.SubElement(sgst_entry, "ISDEEMEDPOSITIVE").text = "No"
                    ET.SubElement(sgst_entry, "AMOUNT").text = str(sgst_amount)
                    total_entries_value += sgst_amount
        rounding_diff = sale_amount - total_entries_value
        if abs(rounding_diff) >= Decimal("0.01"):
            rounding_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
            ET.SubElement(rounding_entry, "LEDGERNAME").text = "Rounding Off"
            is_deemed_positive = "Yes" if rounding_diff > Decimal("0") else "No"
            ET.SubElement(rounding_entry, "ISDEEMEDPOSITIVE").text = is_deemed_positive
            ET.SubElement(rounding_entry, "AMOUNT").text = str(rounding_diff)
            total_entries_value += rounding_diff
    output_filename = os.path.join(data_folder, f"{base_name}.xml")
    print(f"Writing to {output_filename}...")
    try:
        tree = ET.ElementTree(envelope)
        tree.write(output_filename, encoding="utf-8", xml_declaration=True)
        print(f"Successfully wrote {output_filename}.")
        return output_filename
    except Exception as e:
        print(f"Error writing {output_filename}: {e}")
        return None


def save_missing_payout_orders(data_folder, csv_file, missing_orders, config):
    if not missing_orders:
        return
    base_name = os.path.basename(csv_file).replace(".csv", "")
    woo_prefix = config.get("woo_prefix", "Orders-Export")
    missing_prefix = config.get("missing_payout_prefix", "missing-payout")
    if base_name.startswith(woo_prefix):
        suffix = base_name.replace(woo_prefix, "")
        missing_file = f"{missing_prefix}{suffix}.csv"
    else:
        missing_file = f"{missing_prefix}-{base_name}.csv"
    missing_file_path = os.path.join(data_folder, missing_file)
    try:
        with open(missing_file_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "order_id",
                "order_currency",
                "woo_amount",
                "customer_name",
                "order_date",
                "country",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(missing_orders)
        print(
            f"Saved {len(missing_orders)} orders with missing payout amounts to: {missing_file}"
        )
    except Exception as e:
        print(f"Error saving missing payout orders file: {e}")


def main():
    print("WooCommerce CSV to Tally XML Converter with SKU-based Mapping")
    parser = argparse.ArgumentParser(
        description="Convert WooCommerce CSV to Tally XML with GST calculations using SKU mapping"
    )
    parser.add_argument(
        "-c", "--config", default="config.yaml", help="Path to configuration file"
    )
    args = parser.parse_args()
    config = load_config(args.config)
    if not config:
        return
    data_folder = config["data_folder"]
    tally_products_file = config["tally_products_file"]
    sku_mapping_file = config["sku_mapping_file"]
    woo_prefix = config["woo_prefix"]
    tally_prefix = config["tally_prefix"]
    product_prices_file = config["product_prices_file"]
    if not os.path.exists(tally_products_file):
        print(f"Error: Tally products file '{tally_products_file}' not found!")
        return
    if not os.path.exists(sku_mapping_file):
        print(f"Error: SKU mapping file '{sku_mapping_file}' not found!")
        return
    tally_products = load_tally_products(tally_products_file)
    sku_mapping = load_sku_mapping(sku_mapping_file)
    product_prices = load_product_prices(product_prices_file)
    print("\nLoading payout data...")
    payout_amounts = load_all_order_amounts_from_config(args.config)
    if not tally_products:
        print("Failed to load Tally products. Exiting.")
        return
    if not sku_mapping:
        print("Failed to load SKU mapping. Exiting.")
        return
    if not product_prices:
        print("Failed to load product price file. Exiting.")
        return
    csv_file_pattern = os.path.join(data_folder, f"{woo_prefix}*.csv")
    csv_files = glob.glob(csv_file_pattern)
    if not csv_files:
        print(f"No CSV files found with '{woo_prefix}' prefix.")
        return
    print(f"Found {len(csv_files)} CSV files to process.")
    processed_count = 0
    skipped_count = 0
    for csv_file in csv_files:
        filename = os.path.basename(csv_file)
        suffix = filename.replace(woo_prefix, "").replace(".csv", "")
        base_name = f"{tally_prefix}{suffix}"
        output_filename = os.path.join(data_folder, f"{base_name}.xml")
        if os.path.exists(output_filename):
            print(
                f"\nSkipping {filename}... Output file {os.path.basename(output_filename)} already exists."
            )
            skipped_count += 1
            continue
        print(f"\nProcessing {csv_file}...")
        sales_data, missing_payouts = read_woo_csv(
            data_folder,
            csv_file,
            sku_mapping,
            tally_products,
            product_prices,
            payout_amounts,
        )
        if missing_payouts:
            save_missing_payout_orders(data_folder, csv_file, missing_payouts, config)
        if sales_data:
            domestic_count = len([sale for sale in sales_data if sale["is_domestic"]])
            international_count = len(
                [sale for sale in sales_data if not sale["is_domestic"]]
            )
            print(f"Domestic orders detected: {domestic_count}")
            print(f"International orders detected: {international_count}")
            sales_file = create_tally_xml(data_folder, sales_data, base_name=base_name)
            total_processed = len(sales_data)
            print(f"Processed {total_processed} completed orders.")
            processed_count += 1
            if sales_file:
                print(
                    f"All orders (domestic and international) saved to '{sales_file}' ({total_processed} orders)."
                )
            else:
                print("No sales file generated for this CSV.")
        else:
            print("No valid sales data processed for this CSV. Check your file.")
    print(
        f"\nProcessed {processed_count} CSV files, skipped {skipped_count} CSV files (already processed)."
    )
    print("\nYou can now import the generated XML files into Tally.")


if __name__ == "__main__":
    main()
