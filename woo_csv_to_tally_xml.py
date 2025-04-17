import csv
from datetime import datetime
import xml.etree.ElementTree as ET
import os
import glob
import re

# Function to load product mapping from CSV with attributes
def load_product_mapping(mapping_file):
    woo_to_tally = {}
    tally_to_gst = {}
    attributes_map = {}
    try:
        with open(mapping_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            print("Mapping CSV Headers Found:", reader.fieldnames)
            for row in reader:
                woo_name = row["WooCommerce Name"].strip()
                tally_name = row["Tally Name"].strip()
                gst_percentage = row["GST Percentage"].strip()
                attributes = row["Attributes (Key Variations)"].strip()

                # Add to WooCommerce to Tally mapping
                woo_to_tally[woo_name] = tally_name

                # Parse GST Percentage
                gst_rate = float(gst_percentage.replace("%", "")) / 100
                tally_to_gst[tally_name] = gst_rate

                # Store attributes
                attributes_map[woo_name] = attributes

        print(f"Loaded {len(woo_to_tally)} product mappings from {mapping_file}")
        return woo_to_tally, tally_to_gst, attributes_map
    except FileNotFoundError:
        print(f"Error: Mapping file '{mapping_file}' not found!")
        return {}, {}, {}
    except Exception as e:
        print(f"Error loading mapping file: {e}")
        return {}, {}, {}

# Function to extract add-on details from attributes
def extract_addon_details(attributes):
    addons = []
    bag_pattern = r"Add Storage Bag: Yes, Add Bag \(\+Rs\.(\d+\.?\d*)\)"
    book_pattern = r"Add Book: Yes, Add Book \(\+Rs\.(\d+\.?\d*)\)"
    
    bag_match = re.search(bag_pattern, attributes)
    if bag_match:
        addons.append({"type": "Storage Pouch", "price": float(bag_match.group(1))})
    
    book_match = re.search(book_pattern, attributes)
    if book_match:
        addons.append({"type": "Book – When Girls Grow Up", "price": float(book_match.group(1))})
    
    return addons

# Function to get Tally product name from WooCommerce name
def get_tally_product_name(woo_name, woo_to_tally):
    return woo_to_tally.get(woo_name.strip(), woo_name.strip())

# Function to parse WooCommerce CSV and extract sales data
def read_woo_csv(csv_file, woo_to_tally, tally_to_gst, attributes_map):
    sales_data = {}
    try:
        with open(csv_file, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            print("CSV Headers Found:", reader.fieldnames)
            for row in reader:
                try:
                    if row["Order Status"].lower() != "wc-completed":
                        continue
                    
                    order_id = row["Order ID"]
                    if order_id not in sales_data:
                        sale_date = datetime.strptime(row["Order Date"], "%Y-%m-%d %H:%M:%S")
                        customer_name = f"{row['Billing First Name']} {row['Billing Last Name']}".strip() or "Unknown Customer"
                        customer_phone = row["Billing Phone"] or "N/A"
                        customer_email = row["Billing Email Address"] or "N/A"
                        amount = float(row["Order Total"].replace(",", ""))
                        country = row["Billing Country"]
                        party_ledger = "Online Shop Domestic" if country == "IN" else "ONLINE SHOP INTERNATIONAL"
                        is_domestic = (country == "IN")
                        
                        sales_data[order_id] = {
                            "date": sale_date,
                            "amount": amount,
                            "voucher_number": order_id,
                            "products": [],
                            "narration": f"Customer: {customer_name}, Phone: {customer_phone}, Email: {customer_email}",
                            "party_ledger": party_ledger,
                            "is_domestic": is_domestic
                        }
                    
                    product_name = row["Product Name"]
                    tally_name = get_tally_product_name(product_name, woo_to_tally)
                    quantity = int(float(row.get("Quantity", "1").replace(",", "")))
                    item_cost = float(row.get("Item Cost", "0").replace(",", ""))
                    attributes = attributes_map.get(product_name, "None")

                    # Extract add-ons from attributes
                    addons = extract_addon_details(attributes)
                    base_cost = item_cost - sum(addon["price"] for addon in addons)

                    # Base product
                    gst_rate = tally_to_gst.get(tally_name, 0.0)
                    gst_rate = gst_rate if sales_data[order_id]["is_domestic"] else 0.0
                    base_rate = base_cost / (1 + gst_rate) if gst_rate > 0 else base_cost
                    total_base = base_rate * quantity
                    total_gst = (base_cost - base_rate) * quantity if gst_rate > 0 else 0.0
                    cgst_amount = total_gst / 2 if gst_rate > 0 else 0.0
                    sgst_amount = total_gst / 2 if gst_rate > 0 else 0.0
                    
                    sales_data[order_id]["products"].append({
                        "name": tally_name,
                        "quantity": quantity,
                        "base_rate": base_rate,
                        "base_amount": total_base,
                        "gst_rate": gst_rate,
                        "cgst_amount": cgst_amount,
                        "sgst_amount": sgst_amount
                    })

                    # Add-ons
                    for addon in addons:
                        addon_tally_name = addon["type"]
                        addon_price = addon["price"]
                        addon_gst_rate = tally_to_gst.get(addon_tally_name, 0.0)
                        addon_gst_rate = addon_gst_rate if sales_data[order_id]["is_domestic"] else 0.0
                        addon_base_rate = addon_price / (1 + addon_gst_rate) if addon_gst_rate > 0 else addon_price
                        addon_gst = (addon_price - addon_base_rate) * quantity if addon_gst_rate > 0 else 0.0
                        addon_cgst = addon_gst / 2
                        addon_sgst = addon_gst / 2
                        sales_data[order_id]["products"].append({
                            "name": addon_tally_name,
                            "quantity": quantity,
                            "base_rate": addon_base_rate,
                            "base_amount": addon_base_rate * quantity,
                            "gst_rate": addon_gst_rate,
                            "cgst_amount": addon_cgst * quantity,
                            "sgst_amount": addon_sgst * quantity
                        })
                
                except (KeyError, ValueError) as e:
                    print(f"Error processing order {row.get('Order ID', 'unknown')}: {e}")
        
        return list(sales_data.values())
    
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found!")
        return []
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return []

# Function to find the next available filename
def get_next_filename(base_name="Sales", extension=".xml"):
    counter = 1
    while True:
        filename = f"{base_name}{counter}{extension}"
        if not os.path.exists(filename):
            return filename
        counter += 1

# Generate Tally XML from sales data with GST
def create_tally_xml(sales_data, base_name="Sales"):
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
        voucher = ET.SubElement(tally_msg, "VOUCHER", VCHTYPE="Sales", ACTION="Create", OBJVIEW="Invoice Voucher View")
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
        
        # Inventory entries
        for product in sale["products"]:
            inventory_entry = ET.SubElement(voucher, "ALLINVENTORYENTRIES.LIST")
            ET.SubElement(inventory_entry, "STOCKITEMNAME").text = product["name"]
            ET.SubElement(inventory_entry, "ISDEEMEDPOSITIVE").text = "No"
            ET.SubElement(inventory_entry, "RATE").text = f"{product['base_rate']:.2f}/Nos"
            ET.SubElement(inventory_entry, "AMOUNT").text = f"{product['base_amount']:.2f}"
            ET.SubElement(inventory_entry, "ACTUALQTY").text = f"{product['quantity']} Nos"
            ET.SubElement(inventory_entry, "BILLEDQTY").text = f"{product['quantity']} Nos"
            ET.SubElement(inventory_entry, "GODOWNNAME").text = "Eco Femme"
            # Accounting allocation
            accounting = ET.SubElement(inventory_entry, "ACCOUNTINGALLOCATIONS.LIST")
            if sale["is_domestic"] and product["gst_rate"] > 0:
                ledger_name = f"Local GST Sales @ {product['gst_rate'] * 100:.0f}%"
            elif sale["is_domestic"]:
                ledger_name = "Local Exempt Sales"
            else:
                ledger_name = "Export Sales"
            ET.SubElement(accounting, "LEDGERNAME").text = ledger_name
            ET.SubElement(accounting, "ISDEEMEDPOSITIVE").text = "No"
            ET.SubElement(accounting, "AMOUNT").text = f"{product['base_amount']:.2f}"
        
        # GST Ledger Entries (domestic only)
        if sale["is_domestic"]:
            total_cgst = sum(p["cgst_amount"] for p in sale["products"])
            total_sgst = sum(p["sgst_amount"] for p in sale["products"])
            gst_rates_used = set(p["gst_rate"] for p in sale["products"] if p["gst_rate"] > 0)
            
            for gst_rate in gst_rates_used:
                cgst_rate_percent = (gst_rate / 2) * 100
                sgst_rate_percent = cgst_rate_percent
                cgst_ledger = f"CGST Collected @ {cgst_rate_percent:.0f}%"
                sgst_ledger = f"SGST Collected @ {sgst_rate_percent:.0f}%"
                
                cgst_amount = sum(p["cgst_amount"] for p in sale["products"] if p["gst_rate"] == gst_rate)
                sgst_amount = sum(p["sgst_amount"] for p in sale["products"] if p["gst_rate"] == gst_rate)
                
                if cgst_amount > 0:
                    cgst_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
                    ET.SubElement(cgst_entry, "LEDGERNAME").text = cgst_ledger
                    ET.SubElement(cgst_entry, "ISDEEMEDPOSITIVE").text = "No"
                    ET.SubElement(cgst_entry, "AMOUNT").text = f"{cgst_amount:.2f}"
                
                if sgst_amount > 0:
                    sgst_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
                    ET.SubElement(sgst_entry, "LEDGERNAME").text = sgst_ledger
                    ET.SubElement(sgst_entry, "ISDEEMEDPOSITIVE").text = "No"
                    ET.SubElement(sgst_entry, "AMOUNT").text = f"{sgst_amount:.2f}"
        
        # Party Ledger Entry
        party_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
        ET.SubElement(party_entry, "LEDGERNAME").text = sale["party_ledger"]
        ET.SubElement(party_entry, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(party_entry, "AMOUNT").text = f"-{sale['amount']:.2f}"

    output_filename = get_next_filename(base_name=base_name, extension=".xml")
    print(f"Attempting to write {output_filename}...")
    try:
        tree = ET.ElementTree(envelope)
        tree.write(output_filename, encoding="utf-8", xml_declaration=True)
        print(f"Successfully wrote {output_filename}.")
        return output_filename
    except Exception as e:
        print(f"Error writing {output_filename}: {e}")
        return None

# Main function
def main():
    print("WooCommerce CSV to Tally XML Converter with Attribute-Based Add-Ons")
    mapping_file = input("Enter the name of your product mapping CSV file (e.g., new_product_mapping.csv): ").strip()
    csv_file = input("Enter the name of your WooCommerce CSV file (e.g., woo_orders.csv): ").strip()
    
    # Load product mapping with attributes
    woo_to_tally, tally_to_gst, attributes_map = load_product_mapping(mapping_file)
    if not woo_to_tally or not tally_to_gst or not attributes_map:
        print("Failed to load product mapping. Exiting.")
        return
    
    existing_files = glob.glob("*.xml")
    print("Existing XML files in directory:", existing_files if existing_files else "None")
    
    sales_data = read_woo_csv(csv_file, woo_to_tally, tally_to_gst, attributes_map)
    
    if sales_data:
        domestic_count = len([sale for sale in sales_data if sale["is_domestic"]])
        international_count = len([sale for sale in sales_data if not sale["is_domestic"]])
        
        print(f"Domestic orders detected: {domestic_count}")
        print(f"International orders detected: {international_count}")
        
        sales_file = create_tally_xml(sales_data, base_name="Sales")
        
        total_processed = len(sales_data)
        print(f"Processed {total_processed} completed orders.")
        if sales_file:
            print(f"All orders (domestic and international) saved to '{sales_file}' ({total_processed} orders).")
        else:
            print("No sales file generated.")
        print("You can now import this XML file into Tally.")
    else:
        print("No valid sales data processed. Check your CSV file.")

if __name__ == "__main__":
    main()
    input("Press Enter to exit...")
