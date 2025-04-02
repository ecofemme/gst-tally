import csv
from datetime import datetime
import xml.etree.ElementTree as ET
import os
import glob

# Reverse mapping: WooCommerce Name -> Tally Name
WOO_TO_TALLY_MAPPING = {
    "Breast Pads": "Breast Pad",
    "The Clit Kit – Teaching Aid": "Clit Kit",
    "Cuterus – Teaching Aid": "Cuterus",
    "Gift A Cloth Pad": "Gift A Cloth Pad Kit",
    "Heavy Flow Kit - Pack of 4": "Heavy Flow Kit",
    "Light Flow Kit - Pack of 4": "Light Flow Kit",
    "Eco Bébé Nappy Cover": "Nappy Covers",
    "Pantyliners Without Leakproof Layer - Natural Organic": "Natural Organic Pantyliner without PUL (pack of 3)",
    "Pantyliners with Leakproof Layer- Natural Organic": "Natural Organic Pantyliner with PUL (Pack of 3)",
    "Light Flow Kit - Pack of 4 - Natural Range": "Natural Light Flow Kit",
    "Day Pad - Natural Organic": "Natural Organic Day Pad",
    "Day Pad Plus - Natural Organic": "Natural Organic Day Pad Plus",
    "Day Pad Plus- Twin Pack - Natural Organic": "Natural Organic Day Pad Plus Twin Pack",
    "Day Pad - Twin Pack - Natural Organic": "Natural Organic Day Pad Twin Pack",
    "First Period Kit": "Natural Organic First Period Kit With Book",
    "Full Cycle Kit - Natural Organic - No, Thanks! / Full Cycle Kit - Natural Organic - Yes, Add Bag(+Rs.75)": "Natural Organic Fully Cycle Kit",
    "Night Pad - Natural Organic": "Natural Organic Night Pad",
    "Night Pad - Twin Pack - Natural Organic": "Natural Organic Night Pad Twin Pack",
    "Starter Kit - Natural Organic - No, Thanks! / Starter Kit - Natural Organic - Yes, Add Bag(+Rs.75)": "Natural Organic starter kit",
    "Medium Flow Kit - Pack of 4 - Natural Range": "Natural Medium Flow Kit",
    "Make Your Own Stitching Kit": "Natural Make Your Own Kit",
    "New Mum’s Kit": "New Mum's Kit",
    "Period Panty - Hipster - [X-Small/Small/Medium/Large/X-Large/2X-Large/3X-Large] / Period Panty - Brief - [X-Small/Small/Medium/Large/X-Large]": "Period Panty",
    "Starter Kit - Vibrant Organic - No, Thanks! / Starter Kit - Vibrant Organic - Yes, Add Bag(+Rs.75)": "Starter Kit",
    "Cloth Storage Bag": "Storage Pouch",
    "Travel Pouch": "Travel pouch",
    "Medium Flow Kit - Pack of 4 - Vibrant Range": "Vibrant Medium Flow Kit",
    "Day Pad - Vibrant Organic": "Vibrant Organic Day Pad",
    "Day Pad Plus - Vibrant Organic": "Vibrant organic Day pad plus",
    "Day Pad Plus- Twin pack - Vibrant organic": "Vibrant Organic Day Pad Plus Twin Pack",
    "Day Pad - Twin Pack- Vibrant Organic": "Vibrant Organic Day Pad Twin Pack",
    "Foldable Pad - Vibrant Organic": "Vibrant Organic Foldable Pad",
    "Foldable Pad - Twin Pack - Vibrant Organic": "Vibrant Organic Foldable Pad Twin Pack",
    "Full Cycle Kit - Vibrant - No, Thanks! / Full Cycle Kit - Vibrant - Yes, Add Bag(+Rs.75)": "Vibrant Organic Fully Cycle Kit",
    "Night Pad - Vibrant Organic": "Vibrant Organic Night pad",
    "Night Pad - Twin Pack - Vibrant organic": "Vibrant Organic Night Pad Twin Pack",
    "Pantyliners Without Leakproof Layer - Vibrant Organic": "Vibrant Organic Pantyliner without PUL (pack of 3)",
    "Pantyliners with Leakproof Layer- Vibrant Organic": "Vibrant Organic Pantyliner with PUL",
    "Super Comfy Pad - Vibrant organic / Super Comfy Twin Pack - Vibrant organic": "Vibrant Organic Super Comfy",
    "Book – When Girls Grow Up": "Book",
    "Up-cycled Cloth Pad Keychain": "Key Chain",
    "Probiotic Cloth Pad Soap": "soap",
    "SheCup – Menstrual Cup": "SHE cups",
    "Cloth Pad Stickers – Set of 4": "Stickers",
    "Sumo Style belt": "Sumo Style belt",
    "Good Ol’ Faithful Nappy Square – Pack of 3 - large": "Good Ol' Faithful Large - Square",
    "Good Ol’ Faithful Nappy Square – Pack of 3 - small": "Good Ol' Faithful Small - Square",
    "Fit and Fold Inserts – Day (Pack of 3) - large": "FoldnFit Day Large - Insert",
    "Fit and Fold Inserts – Day (Pack of 3) - small": "FoldnFit Day Small - Insert",
    "Fit n Fold Nappy Insert – Night (Pack of 3) - large": "FoldnFit Night Large - Insert",
    "Fit n Fold Nappy Insert – Night (Pack of 3) - small": "FoldnFit Night Small - Insert",
    "Gift 1 Pad": "Pad for Pad scheme",
    "Gift 2 Pads": "Pad for Pad scheme",
    "Gift 3 Pads": "Pad for Pad scheme",
    "Gift 4 Pads": "Pad for Pad scheme",
    "Gift 5 Pads": "Pad for Pad scheme",
    "Gift 6 Pads": "Pad for Pad scheme",
    "Gift 7 Pads": "Pad for Pad scheme",
    "Gift 8 Pads": "Pad for Pad scheme",
    "Gift 9 Pads": "Pad for Pad scheme",
    "Gift 10 Pads": "Pad for Pad scheme",
    "Gift 15 Pads": "Pad for Pad scheme",
    "Gift 20 Pads": "Pad for Pad scheme",
    "Gift 25 Pads": "Pad for Pad scheme",
    "Gift 30 Pads": "Pad for Pad scheme"
}

# GST mapping: Tally Name -> GST Percentage (as decimal)
TALLY_TO_GST_MAPPING = {
    "Breast Pad": 0.18,
    "Clit Kit": 0.0,
    "Cuterus": 0.0,
    "Gift A Cloth Pad Kit": 0.18,
    "Heavy Flow Kit": 0.18,
    "Light Flow Kit": 0.18,
    "Nappy Covers": 0.18,
    "Natural Organic Pantyliner without PUL (pack of 3)": 0.18,
    "Natural Organic Pantyliner with PUL (Pack of 3)": 0.18,
    "Natural Light Flow Kit": 0.18,
    "Natural Organic Day Pad": 0.18,
    "Natural Organic Day Pad Plus": 0.18,
    "Natural Organic Day Pad Plus Twin Pack": 0.18,
    "Natural Organic Day Pad Twin Pack": 0.18,
    "Natural Organic First Period Kit With Book": 0.18,
    "Natural Organic Fully Cycle Kit": 0.18,
    "Natural Organic Night Pad": 0.18,
    "Natural Organic Night Pad Twin Pack": 0.18,
    "Natural Organic starter kit": 0.18,
    "Natural Medium Flow Kit": 0.18,
    "Natural Make Your Own Kit": 0.18,
    "New Mum's Kit": 0.18,
    "Period Panty": 0.18,
    "Starter Kit": 0.18,
    "Storage Pouch": 0.18,
    "Travel pouch": 0.18,
    "Vibrant Medium Flow Kit": 0.18,
    "Vibrant Organic Day Pad": 0.18,
    "Vibrant organic Day pad plus": 0.18,
    "Vibrant Organic Day Pad Plus Twin Pack": 0.18,
    "Vibrant Organic Day Pad Twin Pack": 0.18,
    "Vibrant Organic Foldable Pad": 0.18,
    "Vibrant Organic Foldable Pad Twin Pack": 0.18,
    "Vibrant Organic Fully Cycle Kit": 0.18,
    "Vibrant Organic Night pad": 0.18,
    "Vibrant Organic Night Pad Twin Pack": 0.18,
    "Vibrant Organic Pantyliner without PUL (pack of 3)": 0.18,
    "Vibrant Organic Pantyliner with PUL": 0.18,
    "Vibrant Organic Super Comfy": 0.18,
    "Natural Make Your Own Kit": 0.18,
    "Vibrant Make Your Own Kit": 0.18,
    "Book": 0.0,
    "Key Chain": 0.18,
    "soap": 0.18,
    "SHE cups": 0.18,
    "Stickers": 0.18,
    "Sumo Style belt": 0.18,
    "Good Ol' Faithful Large - Square": 0.18,
    "Good Ol' Faithful Small - Square": 0.18,
    "FoldnFit Day Large - Insert": 0.18,
    "FoldnFit Day Small - Insert": 0.18,
    "FoldnFit Night Large - Insert": 0.18,
    "FoldnFit Night Small - Insert": 0.18,
    "Pad for Pad scheme": 0.18
}

# Function to get Tally product name from WooCommerce name
def get_tally_product_name(woo_name):
    return WOO_TO_TALLY_MAPPING.get(woo_name.strip(), woo_name.strip())

# Function to parse WooCommerce CSV and extract sales data
def read_woo_csv(csv_file):
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
                    tally_name = get_tally_product_name(product_name)
                    quantity = int(float(row.get("Quantity", "1").replace(",", "")))
                    item_cost = float(row.get("Item Cost", "0").replace(",", ""))
                    gst_rate = TALLY_TO_GST_MAPPING.get(tally_name, 0.0) if sales_data[order_id]["is_domestic"] else 0.0
                    
                    if quantity > 0:
                        base_price = item_cost / (1 + gst_rate) if gst_rate > 0 else item_cost
                        total_base = base_price * quantity
                        total_gst = (item_cost - base_price) * quantity if gst_rate > 0 else 0.0
                        cgst_amount = total_gst / 2 if gst_rate > 0 else 0.0
                        sgst_amount = total_gst / 2 if gst_rate > 0 else 0.0
                        
                        sales_data[order_id]["products"].append({
                            "name": tally_name,
                            "quantity": quantity,
                            "base_rate": base_price,
                            "base_amount": total_base,
                            "gst_rate": gst_rate,
                            "cgst_amount": cgst_amount,
                            "sgst_amount": sgst_amount
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
        
        # Inventory entries without batch allocations
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
            ET.SubElement(accounting, "LEDGERNAME").text = "Local GST Sales @ 18%" if product["gst_rate"] > 0 else "Local Exempt Sales"
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
        
        # Sales Ledger Entry
        base_total = sum(p["base_amount"] for p in sale["products"])
        gst_rates_in_order = set(p["gst_rate"] for p in sale["products"])
        if not sale["is_domestic"]:
            sales_ledger = "Export Sales"
        elif 0.18 in gst_rates_in_order:
            sales_ledger = "Local GST Sales @ 18%"
        else:
            sales_ledger = "Local Exempt Sales"
        
        sales_entry = ET.SubElement(voucher, "LEDGERENTRIES.LIST")
        ET.SubElement(sales_entry, "LEDGERNAME").text = sales_ledger
        ET.SubElement(sales_entry, "ISDEEMEDPOSITIVE").text = "No"
        ET.SubElement(sales_entry, "AMOUNT").text = f"{base_total:.2f}"
        
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
    print("WooCommerce CSV to Tally XML Converter with GST")
    csv_file = input("Enter the name of your WooCommerce CSV file (e.g., woo_orders.csv): ").strip()
    
    existing_files = glob.glob("*.xml")
    print("Existing XML files in directory:", existing_files if existing_files else "None")
    
    sales_data = read_woo_csv(csv_file)
    
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
