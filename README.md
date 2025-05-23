# GST Tally Converter

A tool to convert WooCommerce order exports to Tally-compatible XML import files with proper GST calculations for domestic and international sales.

## Day-to-Day Usage

### Step 1: Export Orders from WooCommerce

1. In your WooCommerce admin, go to **WooCommerce > Orders**
2. Click **Export** at the top of the orders list
3. Select the date range for orders you want to process
4. Make sure **Order Status** is set to "Completed" only
5. Export and save the file with a name starting with `Orders-Export` (e.g., `Orders-Export-January-2025.csv`)
6. Place the CSV file in your configured data folder (default: `~/Woo Orders`)

### Step 2: Run the Converter

1. Double-click the **GST Tally Converter** application icon
2. Click the **Convert** button
3. Wait for the conversion to complete - you'll see progress messages in the window
4. The converter will create XML files with names like `sales-January-2025.xml`

### Step 3: Send Files to Your Accountant

1. The XML files are saved in the same folder as your CSV files
2. Email these XML files to your accountant with instructions to import them into Tally
3. Your accountant can import them using **Gateway of Tally > Import > XML**

**Note**: The converter automatically skips files that have already been processed to avoid duplicates.

## Managing Product Changes

### When You Add New Products

**You need to update three files:**

1. **`tally_products.csv`** - Add product with GST rate and warehouse:
   ```csv
   Tally Name,GST Percentage,Godown Name
   New Organic Pad,5%,Eco Femme
   ```

2. **`woo_sku_to_tally.json`** - Map the WooCommerce SKU to the product:
   ```json
   "NEW-SKU": ["New Organic Pad"]
   ```

3. **`tally_product_prices.csv`** - Add the standard price:
   ```csv
   Tally Name,Normal Price
   New Organic Pad,400
   ```

### When Prices Change

Update the price in **`tally_product_prices.csv`**:
```csv
Tally Name,Normal Price
SHE cups,950
```
*Note: This only affects bundled products. Single products use WooCommerce prices directly.*

### When GST Rates Change

Update the GST percentage in **`tally_products.csv`**:
```csv
Tally Name,GST Percentage,Godown Name
Travel pouch,12%,Eco Femme
```

### When You Stop Selling Products

1. Remove or comment out the SKU mapping in `woo_sku_to_tally.json`
2. Keep the product in other files in case old orders need reprocessing

**Important**: Always test with a small export after making changes to ensure everything works correctly.

## Installation and Setup

### Prerequisites

- **UV** (Python package manager) - Download from [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)

### Installation Steps

1. **Download the project**:
   ```bash
   git clone https://github.com/aurovilledotcom/gst-tally.git
   cd gst-tally
   ```

2. **Install dependencies**:
   ```bash
   uv venv
   uv sync
   ```

3. **Set up your configuration**:
   - Edit `config.yaml` to point to your data folder
   - Ensure your product files are properly configured (see examples below)

### Configuration Files Setup

#### `config.yaml` - Main Settings
```yaml
data_folder: ~/Woo Orders
woo_prefix: Orders-Export
tally_prefix: sales
tally_products_file: tally_products.csv
sku_mapping_file: woo_sku_to_tally.json
product_prices_file: tally_product_prices.csv
```

#### `tally_products.csv` - Product Information
```csv
Tally Name,GST Percentage,Godown Name
Natural Organic Day Pad,0%,Eco Femme
Travel pouch,5%,Eco Femme
SHE cups,12%,Eco Femme
soap,18%,Eco Femme
Pad for Pad scheme,0%,
```

#### `woo_sku_to_tally.json` - SKU Mapping
```json
{
  "EF-n-DP": ["Natural Organic Day Pad"],
  "ACS-TP": ["Travel pouch"],
  "EF-n-SK(SB)": ["Natural Organic starter kit", "Storage Pouch"],
  "EF-v-FPKB": ["Vibrant Organic First Period Kit With Book", "Book"]
}
```

#### `tally_product_prices.csv` - Standard Prices
```csv
Tally Name,Normal Price
Natural Organic starter kit,915
Starter Kit,915
Storage Pouch,75
Book,499
```

### Creating a Desktop Launcher (Optional)

To create a desktop shortcut:

**For GUI version**:
```bash
uv run gst-tally-gui
```

**For command line version**:
```bash
uv run gst-tally
```

## Technical Details

### WooCommerce Export Requirements

Your CSV export must include these columns:
- Order ID, Order Status, Order Date, Order Total
- Billing First Name, Billing Last Name, Billing Phone, Billing Email Address
- Billing Country, SKU, Quantity, Item Cost

### Processing Logic

- **Domestic orders** (India): Calculate CGST and SGST based on product GST rates
- **International orders**: Use "Export Sales" ledger with zero GST
- **Bundled products**: Distribute bundle price proportionally based on standard prices
- **Rounding**: Automatic rounding adjustments to match order totals

### Troubleshooting

**Common Error Messages:**

- `"SKU 'XXX' not found in mapping"` → Add the SKU to `woo_sku_to_tally.json`
- `"Missing prices for products"` → Add product prices to `tally_product_prices.csv`
- `"Tally product 'XXX' not found"` → Check product name spelling in `tally_products.csv`
- `"Configuration file not found"` → Ensure `config.yaml` exists in the project folder

**Getting Help:**
- Check the status messages in the converter window for specific error details
- Ensure all product names match exactly across all configuration files
- Verify that your WooCommerce export includes all required columns

## License

This project is licensed under the MIT License.
