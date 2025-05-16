# GST Tally

A tool to convert WooCommerce CSV exports to Tally-compatible XML import files with proper GST calculations.

## Features

- Converts WooCommerce order data to Tally XML format
- Handles GST rate calculations for domestic and international sales
- Maps WooCommerce product SKUs to Tally product names
- Supports multiple product types and tax structures
- Handles proportional pricing for bundled products

## Requirements

- Python 3.6 or higher
- UV (Python package manager)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/aurovilledotcom/gst-tally.git
   cd gst-tally
   ```

2. Create a virtual environment and install dependencies using UV:
   ```
   uv venv
   ```

## Configuration Files

The program uses the following configuration files:

### 1. `config.yaml` - Main configuration file

```yaml
woo_prefix: Orders-Export
tally_prefix: sales
tally_products_file: tally_products.csv
sku_mapping_file: woo_sku_to_tally.json
product_prices_file: tally_product_prices.csv
```

- `woo_prefix`: Prefix for WooCommerce CSV export files
- `tally_prefix`: Prefix for generated Tally XML files
- `tally_products_file`: Path to CSV file containing Tally product information
- `sku_mapping_file`: Path to JSON file mapping WooCommerce SKUs to Tally products
- `product_prices_file`: Path to CSV file with product prices (required for bundled products)

### 2. `tally_products.csv` - Tally Product Information

Required columns:
- `Tally Name`: The exact name of the product in Tally
- `GST Percentage`: GST rate applicable to the product (format: "12%", "5%", "0%", etc.)
- `Godown Name`: Tally godown/warehouse name (leave empty for non-inventory items)

Example from actual data:
```csv
Tally Name,GST Percentage,Godown Name
Natural Organic Day Pad,0%,Eco Femme
Travel pouch,5%,Eco Femme
SHE cups,12%,Eco Femme
soap,18%,Eco Femme
Clit Kit,18%,Eco Femme
Pad for Pad scheme,0%,
```

### 3. `woo_sku_to_tally.json` - SKU to Tally Product Mapping

JSON format that maps WooCommerce SKUs to one or more Tally product names.

- Single product mapping: `"EF-n-DP": ["Natural Organic Day Pad"]`
- Multiple product (bundle) mapping: `"EF-n-SK(SB)": ["Natural Organic starter kit", "Storage Pouch"]`

Example from actual data:
```json
{
  "EF-n-DP": ["Natural Organic Day Pad"],
  "ACS-TP": ["Travel pouch"],
  "ACS-SHC": ["SHE cups"],
  "ACS-SP": ["soap"],
  "EF-n-SK(SB)": ["Natural Organic starter kit", "Storage Pouch"],
  "EF-v-FPKB": ["Vibrant Organic First Period Kit With Book", "Book"],
  "EF-LFK": ["Natural Light Flow Kit", "Vibrant Light Flow Kit"]
}
```

### 4. `tally_product_prices.csv` - Product Pricing Information

Required columns:
- `Tally Name`: Exact name of the product in Tally
- `Normal Price`: Standard selling price of the product (numerical value without currency symbol)

Example (based on product names from your data):
```csv
Tally Name,Normal Price
Natural Organic Day Pad,350
Travel pouch,120
Storage Pouch,200
SHE cups,850
Vibrant Organic Full Cycle Kit,1500
Book,250
```

This file is **essential** for handling bundled products. When a WooCommerce SKU maps to multiple Tally products, the system uses these prices to proportionally distribute the bundle price.

## Data Formats and Structure

### WooCommerce CSV Export Requirements

Your WooCommerce export must include these columns:
- `Order ID`: Unique identifier for the order
- `Order Status`: Status of the order (only "wc-completed" orders are processed)
- `Order Date`: Date and time of the order (format: "YYYY-MM-DD HH:MM:SS")
- `Order Total`: Total order amount
- `Billing First Name`: Customer's first name
- `Billing Last Name`: Customer's last name
- `Billing Phone`: Customer's phone number
- `Billing Email Address`: Customer's email address
- `Billing Country`: Customer's country code (e.g., "IN" for India)
- `SKU`: Product SKU
- `Quantity`: Number of items ordered
- `Item Cost`: Cost of the item

### Generated Tally XML Structure

The program generates Tally-compatible XML files with:
- Sales vouchers for each order
- Appropriate ledger entries for sales
- GST calculations for domestic orders (using ledgers like "CGST Collected @ 9%" and "SGST Collected @ 9%")
- Inventory entries for items with godown names (like "Eco Femme")
- Separate handling for international orders with "Export Sales" ledger

## Updating Data When Products or Prices Change

### Adding New Products

1. **Update Tally Products CSV**:
   - Add a new row to `tally_products.csv` with the product's name, GST rate, and godown name
   - Example: `New Organic Pad,5%,Eco Femme`
   - Ensure the Tally Name matches exactly with your Tally ERP system

2. **Update SKU Mapping**:
   - Add the new product to `woo_sku_to_tally.json` with the WooCommerce SKU as the key
   - For a single product: `"EF-n-NOP": ["New Organic Pad"]`
   - For a bundle including the new product: `"EF-n-NKB": ["New Organic Pad", "Book"]`

3. **Update Product Prices**:
   - Add the product to `tally_product_prices.csv` with its standard price
   - Example: `New Organic Pad,400`
   - This is crucial if the product is part of any bundle

### Updating Prices

1. **Modify `tally_product_prices.csv`**:
   - Update the `Normal Price` value for the product(s)
   - Example: Change `SHE cups,850` to `SHE cups,950`
   - This affects price distribution for bundled products
   - Regular single products use WooCommerce pricing directly

### Modifying GST Rates

1. **Update `tally_products.csv`**:
   - Modify the `GST Percentage` value for the affected product(s)
   - Example: Change `Travel pouch,5%,Eco Femme` to `Travel pouch,12%,Eco Femme`
   - Make sure to include the percentage symbol (e.g., "12%")

### Changing Product Names

If you need to change a product name:

1. Update the name in `tally_products.csv`:
   - Example: Change `Natural Organic Day Pad` to `Natural Cotton Day Pad`

2. Update all references to the product in `woo_sku_to_tally.json`:
   - Update `"EF-n-DP": ["Natural Organic Day Pad"]` to `"EF-n-DP": ["Natural Cotton Day Pad"]`
   - Update any bundles containing this product

3. Update the name in `tally_product_prices.csv`:
   - Change `Natural Organic Day Pad,350` to `Natural Cotton Day Pad,350`

## Usage

1. Prepare your WooCommerce CSV exports with the required format
2. Name your file with the prefix specified in config.yaml (default: `Orders-Export.csv`)
3. Run the conversion script:
   ```
   uv run python woo_csv_to_tally_xml.py
   ```
4. The program generates XML files with the prefix specified in config.yaml
5. Import the generated XML into Tally using its import functionality

## Processing Logic for Bundled Products

When a WooCommerce SKU maps to multiple Tally products (a bundle):

1. The system looks up the standard prices for all products in the bundle from `tally_product_prices.csv`
2. For example, for the bundle `"EF-v-FPKB": ["Vibrant Organic First Period Kit With Book", "Book"]`:
   - It looks up prices for `Vibrant Organic First Period Kit With Book` and `Book`
   - Calculates the total standard price of the bundle
3. The actual WooCommerce price is distributed proportionally across bundle items
4. Each item is entered separately in Tally with its proportional share of the price
5. GST is calculated separately for each item based on its specific GST rate

## Troubleshooting

- **Missing Price Error**: Ensure all products have entries in `tally_product_prices.csv`
  - Example: "Error: Missing prices for products: Vibrant Organic First Period Kit With Book. SKU 'EF-v-FPKB' requires prices for all mapped Tally products."

- **SKU Not Found**: Add missing SKUs to `woo_sku_to_tally.json`
  - Example: "Warning: SKU 'EF-n-SP' not found in mapping"

- **Tally Product Not Found**: Verify product names match exactly in all files
  - Example: "Warning: Tally product 'Natural Organic Day Pad Plus' not found in tally_products"

- **CSV Format Issues**: Check that your WooCommerce export contains all required columns
  - Make sure your export includes 'Order ID', 'SKU', 'Order Status', etc.

- **GST Calculation Problems**: Verify GST percentages are correctly formatted with % symbol
  - Example: Use "12%" instead of "12" or "0.12"

## License

This project is licensed under the Apache License 2.0.
