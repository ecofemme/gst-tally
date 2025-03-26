import csv
from datetime import datetime
import xml.etree.ElementTree as ET
import os

# Product name mapping dictionary (Tally Name: WooCommerce Name)
PRODUCT_MAPPING = {
    "Breast Pad": "Breast Pads",
    "Clit Kit": "The Clit Kit – Teaching Aid",
    "Cuterus": "Cuterus – Teaching Aid",
    "Gift A Cloth Pad Kit": "Gift A Cloth Pad",
    "Heavy Flow Kit": "Heavy Flow Kit - Pack of 4",
    "Light Flow Kit": "Light Flow Kit - Pack of 4",
    "Nappy Covers": "Eco Bébé Nappy Cover",
    "Natural Organic Pantyliner without PUL (pack of 3)": "Pantyliners Without Leakproof Layer - Natural Organic",
    "Natural Organic Pantyliner with PUL (Pack of 3)": "Pantyliners with Leakproof Layer- Natural Organic",
    "Natural Light Flow Kit": "Light Flow Kit - Pack of 4 - Natural Range",
    "Natural Organic Day Pad": "Day Pad - Natural Organic",
    "Natural Organic Day Pad Plus": "Day Pad Plus - Natural Organic",
    "Natural Organic Day Pad Plus Twin Pack": "Day Pad Plus- Twin Pack - Natural Organic",
    "Natural Organic Day Pad Twin Pack": "Day Pad - Twin Pack - Natural Organic",
    "Natural Organic First Period Kit With Book": "First Period Kit",
    "Natural Organic Fully Cycle Kit": "Full Cycle Kit - Natural Organic - No, Thanks! / Full Cycle Kit - Natural Organic - Yes, Add Bag(+Rs.75)",
    "Natural Organic Night Pad": "Night Pad - Natural Organic",
    "Natural Organic Night Pad Twin Pack": "Night Pad - Twin Pack - Natural Organic",
    "Natural Organic starter kit": "Starter Kit - Natural Organic - No, Thanks! / Starter Kit - Natural Organic - Yes, Add Bag(+Rs.75)",
    "Natural Medium Flow Kit": "Medium Flow Kit - Pack of 4 - Natural Range",
    "Natural Make Your Own Kit": "Make Your Own Stitching Kit",
    "New Mum's Kit": "New Mum’s Kit",
    "Period Panty": "Period Panty - Hipster - [X-Small/Small/Medium/Large/X-Large/2X-Large/3X-Large] / Period Panty - Brief - [X-Small/Small/Medium/Large/X-Large]",
    "Starter Kit": "Starter Kit - Vibrant Organic - No, Thanks! / Starter Kit - Vibrant Organic - Yes, Add Bag(+Rs.75)",
    "Storage Pouch": "Cloth Storage Bag",
    "Travel pouch": "Travel Pouch",
    "Vibrant Medium Flow Kit": "Medium Flow Kit - Pack of 4 - Vibrant Range",
    "Vibrant Organic Day Pad": "Day Pad - Vibrant Organic",
    "Vibrant organic Day pad plus": "Day Pad Plus - Vibrant Organic",
    "Vibrant Organic Day Pad Plus Twin Pack": "Day Pad Plus- Twin pack - Vibrant organic",
    "Vibrant Organic Day Pad Twin Pack": "Day Pad - Twin Pack- Vibrant Organic",
    "Vibrant Organic Foldable Pad": "Foldable Pad - Vibrant Organic",
    "Vibrant Organic Foldable Pad Twin Pack": "Foldable Pad - Twin Pack - Vibrant Organic",
    "Vibrant Organic Fully Cycle Kit": "Full Cycle Kit - Vibrant - No, Thanks! / Full Cycle Kit - Vibrant - Yes, Add Bag(+Rs.75)",
    "Vibrant Organic Night pad": "Night Pad - Vibrant Organic",
    "Vibrant Organic Night Pad Twin Pack": "Night Pad - Twin Pack - Vibrant organic",
    "Vibrant Organic Pantyliner without PUL (pack of 3)": "Pantyliners Without Leakproof Layer - Vibrant Organic",
    "Vibrant Organic Pantyliner with PUL": "Pantyliners with Leakproof Layer- Vibrant Organic",
    "Vibrant Organic Super Comfy": "Super Comfy Pad - Vibrant organic / Super Comfy Twin Pack - Vibrant organic",
    "Vibrant Make Your Own Kit": "Make Your Own Stitching Kit",
    "First Period Kit": "First Period Kit",
    "Book": "Book – When Girls Grow Up",
    "Key Chain": "Up-cycled Cloth Pad Keychain",
    "soap": "Probiotic Cloth Pad Soap",
    "SHE cups": "SheCup – Menstrual Cup",
    "Stickers": "Cloth Pad Stickers – Set of 4",
    "Sumo Style belt": "Sumo Style belt",
    "Good Ol' Faithful Large - Square": "Good Ol’ Faithful Nappy Square – Pack of 3 - large",
    "Good Ol' Faithful Small - Square": "Good Ol’ Faithful Nappy Square – Pack of 3 - small",
    "FoldnFit Day Large - Insert": "Fit and Fold Inserts – Day (Pack of 3) - large",
    "FoldnFit Day Small - Insert": "Fit and Fold Inserts – Day (Pack of 3) - small",
    "FoldnFit Night Large - Insert": "Fit n Fold Nappy Insert – Night (Pack of 3) - large",
    "FoldnFit Night Small - Insert": "Fit n Fold Nappy Insert – Night (Pack of 3 - small",
    "Pad for Pad scheme": "Gift 1 Pad"
}

# Reverse mapping for lookup (WooCommerce Name -> Tally Name)
REVERSE_MAPPING = {v: k for k, v in PRODUCT_MAPPING.items()}

# Function to get Tally product name from WooCommerce name
def get_tally_product_name(woo_name):
    return REVERSE_MAPPING.get(woo_name, woo_name)

# Function to parse WooCommerce CSV and extract sales data
def read_woo_csv(csv_file):
    sales_data = {}
    try:
        with open(csv_file, newline='', encoding='utf-8-sig') as f:  # 'utf-8-sig' strips BOM
            reader = csv.DictReader(f)
            print("CSV Headers Found:", reader.fieldnames)
            for row in reader:
                try:
                    # Filter only completed orders
                    if row["Order Status"].lower() != "wc-completed":
                        continue
                    
                    order_id = row["Order ID"]
                    
                    # If this order ID is already processed, append product; otherwise, create new entry
                    if order_id not in sales_data:
                        sale_date = datetime.strptime(row["Order Date"], "%Y-%m-%d %H:%M:%S")
                        customer_name = f"{row['Billing First Name']} {row['Billing Last Name']}".strip() or "Unknown Customer"
                        customer_phone = row["Billing Phone"] or "N/A"
                        customer_email = row["Billing Email Address"] or "N/A"
                        amount = float(row["Order Total"])
                        
                        sales_data[order_id] = {
                            "date": sale_date,
                            "amount": amount,
                            "voucher_number": order_id,
                            "products": []
                        }
                    
                    # Add product to the order's product list
                    product_name = row["Product Name"]
                    tally_name = get_tally_product_name(product_name)
                    sales_data[order_id]["products"].append(tally_name)
                
                except (KeyError, ValueError) as e:
                    print(f"Error processing order {row.get('Order ID', 'unknown')}: {e}")
        
        # Convert to list format with narration
        final_sales_data = []
        for order_id, data in sales_data.items():
            narration = f"Customer: {customer_name}, Phone: {customer_phone}, Email: {customer_email}"
            if data["products"]:
                narration += f", Products: {', '.join(data['products'])}"
            data["narration"] = narration
            final_sales_data.append(data)
        
        return final_sales_data
    
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found!")
        return []
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return []

# Function to find the next available filename
def get_next_filename(base_name="sales", extension=".xml"):
    counter = 1
    while True:
        filename = f"{base_name}{counter}{extension}"
        if not os.path.exists(filename):
            return filename
        counter += 1

# Generate Tally XML from sales data
def create_tally_xml(sales_data):
    envelope = ET.Element("ENVELOPE")
    header = ET.SubElement(envelope, "HEADER")
    ET.SubElement(header, "VERSION").text = "1"
    ET.SubElement(header, "TALLYREQUEST").text = "Import"
    ET.SubElement(header, "TYPE").text = "Data"
    ET.SubElement(header, "ID").text = "Vouchers"

    body = ET.SubElement(envelope, "BODY")
    data = ET.SubElement(body, "DATA")

    for sale in sales_data:
        tally_msg = ET.SubElement(data, "TALLYMESSAGE")
        voucher = ET.SubElement(tally_msg, "VOUCHER", VCHTYPE="Sales")
        ET.SubElement(voucher, "DATE").text = sale["date"].strftime("%Y%m%d")
        ET.SubElement(voucher, "VOUCHERNUMBER").text = sale["voucher_number"]
        ET.SubElement(voucher, "VOUCHERTYPENAME").text = "Sales"
        ET.SubElement(voucher, "PARTYLEDGERNAME").text = "Online Shop Domestic"
        
        ET.SubElement(voucher, "NARRATION").text = sale["narration"]
        
        sales_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(sales_entry, "LEDGERNAME").text = "Local Exempt Sales"
        ET.SubElement(sales_entry, "AMOUNT").text = str(sale["amount"])
        
        party_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(party_entry, "LEDGERNAME").text = "Online Shop Domestic"
        ET.SubElement(party_entry, "AMOUNT").text = f"-{sale['amount']}"

    output_filename = get_next_filename(base_name="sales", extension=".xml")
    tree = ET.ElementTree(envelope)
    tree.write(output_filename, encoding="utf-8", xml_declaration=True)
    print(f"XML file '{output_filename}' generated successfully!")
    return output_filename

# Main function
def main():
    print("WooCommerce CSV to Tally XML Converter")
    csv_file = input("Enter the name of your WooCommerce CSV file (e.g., woo_orders.csv): ").strip()
    sales_data = read_woo_csv(csv_file)
    
    if sales_data:
        output_file = create_tally_xml(sales_data)
        print(f"Processed {len(sales_data)} completed orders.")
        print(f"You can now import '{output_file}' into Tally.")
    else:
        print("No valid sales data processed. Check your CSV file.")

if __name__ == "__main__":
    main()
    input("Press Enter to exit...")
