import argparse
import csv
import glob
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime

import yaml

from ledger import get_gst_ledgers, get_party_ledger, get_sales_ledger


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
                gst_rate = float(gst_percentage.replace("%", "")) / 100
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
                    normal_price = float(row["Normal Price"])
                    if normal_price <= 0:
                        print(
                            f"Error: Normal price for '{tally_name}' must be positive"
                        )
                        continue
                    product_prices[tally_name] = normal_price
                except ValueError:
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


def read_woo_csv(data_folder, csv_file, sku_mapping, tally_products, product_prices):
    file_path = os.path.join(data_folder, csv_file)
    sales_data = {}
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
                        amount = float(row["Order Total"].replace(",", ""))
                        country = row["Billing Country"]
                        party_ledger = get_party_ledger(country)
                        is_domestic = country == "IN"
                        sales_data[order_id] = {
                            "date": sale_date,
                            "amount": amount,
                            "voucher_number": order_id,
                            "products": [],
                            "narration": f"Customer: {customer_name}, Phone: {customer_phone}, Email: {customer_email}",
                            "party_ledger": party_ledger,
                            "is_domestic": is_domestic,
                        }
                    sku = row["SKU"].strip() if "SKU" in row else ""
                    tally_names = get_tally_products_by_sku(sku, sku_mapping)
                    quantity = int(float(row.get("Quantity", "1").replace(",", "")))
                    item_cost = float(row.get("Item Cost", "0").replace(",", ""))
                    for tally_name in tally_names:
                        if tally_name in tally_products:
                            product_details = tally_products[tally_name]
                            gst_rate = product_details["gst_rate"]
                            godown_name = product_details["godown_name"]
                            gst_rate = (
                                gst_rate if sales_data[order_id]["is_domestic"] else 0.0
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
                                discount_ratio = item_cost / total_normal_price
                                product_base_cost = (
                                    normal_prices[tally_name] * discount_ratio
                                )
                            else:
                                product_base_cost = item_cost
                            base_rate = (
                                product_base_cost / (1 + gst_rate)
                                if gst_rate > 0
                                else product_base_cost
                            )
                            total_base = base_rate * quantity
                            total_gst = (
                                (product_base_cost - base_rate) * quantity
                                if gst_rate > 0
                                else 0.0
                            )
                            cgst_amount = total_gst / 2 if gst_rate > 0 else 0.0
                            sgst_amount = total_gst / 2 if gst_rate > 0 else 0.0
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
                                }
                            )
                        else:
                            print(
                                f"Warning: Tally product '{tally_name}' not found in tally_products"
                            )
                except (KeyError, ValueError) as e:
                    print(
                        f"Error processing order {row.get('Order ID', 'unknown')}: {e}"
                    )
        return list(sales_data.values())
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found!")
        return []
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return []


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
        for product in sale["products"]:
            if not product["godown_name"]:
                ledger_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
                ET.SubElement(ledger_entry, "LEDGERNAME").text = product["name"]
                ET.SubElement(ledger_entry, "ISDEEMEDPOSITIVE").text = "No"
                ET.SubElement(
                    ledger_entry, "AMOUNT"
                ).text = f"{product['base_amount']:.2f}"
            else:
                inventory_entry = ET.SubElement(voucher, "ALLINVENTORYENTRIES.LIST")
                ET.SubElement(inventory_entry, "STOCKITEMNAME").text = product["name"]
                ET.SubElement(inventory_entry, "ISDEEMEDPOSITIVE").text = "No"
                ET.SubElement(
                    inventory_entry, "RATE"
                ).text = f"{product['base_rate']:.2f}/Nos"
                ET.SubElement(
                    inventory_entry, "AMOUNT"
                ).text = f"{product['base_amount']:.2f}"
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
                ET.SubElement(
                    accounting, "AMOUNT"
                ).text = f"{product['base_amount']:.2f}"
        if sale["is_domestic"]:
            gst_rates_used = {}
            for product in sale["products"]:
                if product["gst_rate"] > 0:
                    gst_rate = product["gst_rate"]
                    if gst_rate not in gst_rates_used:
                        gst_rates_used[gst_rate] = {"cgst": 0, "sgst": 0}
                    gst_rates_used[gst_rate]["cgst"] += product["cgst_amount"]
                    gst_rates_used[gst_rate]["sgst"] += product["sgst_amount"]
            for gst_rate, amounts in gst_rates_used.items():
                cgst_rate_percent = (gst_rate / 2) * 100
                sgst_rate_percent = cgst_rate_percent
                gst_ledgers = get_gst_ledgers(gst_rate, sale["is_domestic"])
                if amounts["cgst"] > 0:
                    cgst_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
                    ET.SubElement(cgst_entry, "LEDGERNAME").text = gst_ledgers[
                        "cgst_ledger"
                    ]
                    ET.SubElement(cgst_entry, "ISDEEMEDPOSITIVE").text = "No"
                    ET.SubElement(cgst_entry, "AMOUNT").text = f"{amounts['cgst']:.2f}"
                if amounts["sgst"] > 0:
                    sgst_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
                    ET.SubElement(sgst_entry, "LEDGERNAME").text = gst_ledgers[
                        "sgst_ledger"
                    ]
                    ET.SubElement(sgst_entry, "ISDEEMEDPOSITIVE").text = "No"
                    ET.SubElement(sgst_entry, "AMOUNT").text = f"{amounts['sgst']:.2f}"
        party_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
        ET.SubElement(party_entry, "LEDGERNAME").text = sale["party_ledger"]
        ET.SubElement(party_entry, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(party_entry, "AMOUNT").text = f"-{sale['amount']:.2f}"
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
            print(f"\nSkipping {filename}... Output file {os.path.basename(output_filename)} already exists.")
            skipped_count += 1
            continue
        print(f"\nProcessing {csv_file}...")
        sales_data = read_woo_csv(data_folder, csv_file, sku_mapping, tally_products, product_prices)
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
    print(f"\nProcessed {processed_count} CSV files, skipped {skipped_count} CSV files (already processed).")
    print("\nYou can now import the generated XML files into Tally.")


if __name__ == "__main__":
    main()
