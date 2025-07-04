# GST Tally Converter

A tool to convert WooCommerce order exports to Tally-compatible XML import files with proper GST calculations for domestic and international sales. Supports automatic currency conversion using PayPal and CCAvenue payout data.

## Day-to-Day Usage

**Note**: These instructions assume you're processing orders once per month. Export interface details are current as of June 3, 2025 and may change with plugin/platform updates.

### Step 1: Export Payment Gateway Data (for Foreign Currency Orders)

The converter automatically handles currency conversion using actual payout amounts from payment gateways.

#### CCAvenue Export

NOTE THAT CCAVENUE PAYOUTS ARE SOMETIMES DELAYED BY SEVERAL DAYS. YOU MAY NEED TO INCLUDE A FEW DAYS AFTER THE END OF THE MONTH TO ENSURE ALL PAYOUTS ARE INCLUDED.

1. Log into the CCAvenue dashboard
2. Go to **Reports** and select **Payment Summary**
3. Click the **Search icon** and select dates for the first half of the month (e.g., 1st - 15th)
4. Click **Transaction Export (Zip)** and download the file (e.g., `payoutTransactionSummary(1).zip`)
5. Click the **Search icon** again and select dates for the second half of the month (e.g., 16th - 31st)
6. Click **Transaction Export (Zip)** and download the second file (e.g., `payoutTransactionSummary(2).zip`)
7. Extract both ZIP files into your data folder (default: `~/Woo Orders`)
8. The extracted files will have names like `PayoutTransactionSummary1748423030410.csv`

#### PayPal Export

1. Log into the PayPal dashboard
2. Select **Activity** and click **All Transactions**
3. Click the **Download** symbol (top right above transactions)
4. Under **Activity report** configure:
   - **Transaction Type**: Select "Balance affecting"
   - **Date range**: Select from one day before the month to two days after the month ends
     - Example: For May transactions, select April 30th to June 2nd
     - This ensures incomplete transactions aren't missed
5. Press **Create Report** and wait for the file to appear
6. Click **Download** under the **Action** header
7. Move the downloaded `Download.CSV` file into your data folder (default: `~/Woo Orders`)

### Step 2: Export Orders from WooCommerce

1. In your WordPress admin, go to **All Export** in the sidebar and click **New Export**
2. Make sure **Specific Post Type** is selected
3. In the dropdown "Choose a post type", select **WooCommerce Orders**
4. Click **Add Filtering Options**
5. Set up date range filters:
   - **First filter**: Select "Order Date" as element, "equal to or newer than" as rule, and enter start date (e.g., "06/01/2025")
   - Click **Add Rule**
   - **Second filter**: Select "Order Date" as element, "equal to or older than" as rule, and enter end date (e.g., "06/30/2025")
   - Click **Add Rule**
6. Click **Customize Export File**
7. On the next page, select the template **"Order by SKU"** (which has all required fields pre-selected)
8. Hit **Continue**
9. **Confirm and Run Export**
10. Save the exported file with a name starting with `Orders-Export` (e.g., `Orders-Export-June-2025.csv`)
11. Place the CSV file in your configured data folder (default: `~/Woo Orders`)

### Step 3: Run the Converter

1. Double-click the **GST Tally Converter** application icon
2. Click the **Convert** button
3. Wait for the conversion to complete - you'll see progress messages in the window
4. The converter will:
   - Process payment gateway data for currency conversion
   - Create XML files with names like `sales-January-2025.xml`
   - Generate missing payout reports if some foreign orders lack payment data

### Step 4: Send Files to Your Accountant

1. The XML files are saved in the same folder as your CSV files
2. Email these XML files to your accountant with instructions to import them into Tally
3. Your accountant can import them using **Gateway of Tally > Import > XML**

**Note**: The converter automatically skips files that have already been processed to avoid duplicates.

## Managing Product Changes

### Adding New Products

There are two types of products to consider:

#### A. Simple/Single Products

You need the product's **Tally name**, **WooCommerce SKU**, **GST percentage**, and **Godown name**.

**Update these 2 files:**

1. **`woo_sku_to_tally.json`** - Map the WooCommerce SKU to Tally name:

   ```json
   "EF-P": ["Pad"]
   ```

2. **`tally_products.csv`** - Add product details:
   ```csv
   Tally Name,GST Percentage,Godown Name
   Pad,0%,Eco Femme
   ```

#### B. Variable/Bundle Products

For products that contain multiple items (like kits with bags, or books), you need the **individual component prices** in addition to the above information.

**Update these 3 files:**

1. **`woo_sku_to_tally.json`** - Map to all components:

   ```json
   "EF-PK": ["Pad Kit"],
   "EF-PK(B)": ["Pad Kit", "Bag"]
   ```

2. **`tally_product_prices.csv`** - Add individual component prices:

   ```csv
   Tally Name,Normal Price
   Pad Kit,915
   Bag,75
   ```

3. **`tally_products.csv`** - Add all components with their GST rates:
   ```csv
   Tally Name,GST Percentage,Godown Name
   Pad Kit,0%,Eco Femme
   Bag,5%,Eco Femme
   ```

### When Prices Change

Update the price in **`tally_product_prices.csv`**:

```csv
Tally Name,Normal Price
SHE cups,950
```

_Note: Price changes only affect products that appear as components in bundled products. Single products always use the actual WooCommerce order price._

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
   git clone https://github.com/ecofemme/gst-tally.git
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
payout_prefix: PayoutTransactionSummary
paypal_prefix: Download
missing_payout_prefix: missing-payout
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

#### Command Line Usage

**For GUI version**:

```bash
uv run gst-tally-gui
```

**For command line version**:

```bash
uv run gst-tally
```

#### Linux Desktop Shortcut

Create a desktop shortcut file for easy access:

1. **Create the desktop entry file**:

   ```bash
   nano ~/.local/share/applications/gst-tally.desktop
   ```

2. **Add the following content** (adjust the path to match your installation):

   ```ini
   [Desktop Entry]
   Version=0.0.1
   Type=Application
   Name=Tally Order Exporter
   Comment=Convert WooCommerce CSV exports to Tally XML import format
   Exec=bash -c "cd ~/GitHub/gst-tally/ && uv run python tally_launcher.py"
   Icon=accessories-calculator
   Terminal=false
   Categories=Office;Finance
   ```

3. **The shortcut should now appear in your applications menu** under Office or Finance categories.

**Note**: Adjust the path in the `Exec` line to match where you installed the project.

## Keeping the Software Updated

### Updating from GitHub

1. **Navigate to the project folder**:

   ```bash
   cd ~/GitHub/gst-tally
   ```

2. **Check current status**:

   ```bash
   git status
   ```

   This shows if you're in a Git repository and which branch you're on (e.g., "On branch main")

3. **Get the latest updates**:

   ```bash
   git pull origin main
   ```

4. **Update dependencies if needed**:
   ```bash
   uv sync
   ```

## Technical Details

### Currency Conversion Logic

- **PayPal**: Tracks payments in foreign currencies and applies exchange rates from actual withdrawals
- **CCAvenue**: Uses payout amounts directly from transaction reports
- **Missing payouts**: Creates separate reports for orders without matching payment data
- **Domestic orders**: No currency conversion needed (INR)

### WooCommerce Export Requirements

Your CSV export must include these columns:

- Order ID, Order Status, Order Date, Order Total, Order Currency
- Billing First Name, Billing Last Name, Billing Phone, Billing Email Address
- Billing Country, SKU, Quantity, Item Cost
- Shipping Cost, Total Fee Amount, Fee Amount (per surcharge)

**Note**: The "Fee Amount (per surcharge)" column must be included to ensure "Total Fee Amount" exports correctly, even though it's not used in processing.

### Processing Logic

- **Domestic orders** (India): Calculate CGST and SGST based on product GST rates
- **International orders**: Use "Export Sales" ledger with zero GST
- **Products with Godown names**: Treated as inventory items in Tally with stock tracking
- **Products without Godown names**: Treated as regular ledger entries (services/non-inventory items)
- **Bundled products**: Individual component prices from `tally_product_prices.csv` are used to distribute the total bundle cost proportionally
- **Single products**: Use the actual price from WooCommerce orders directly
- **Currency conversion**: Apply actual exchange rates from payment gateway data
- **Rounding**: Automatic rounding adjustments to match order totals

### File Structure

```
~/Woo Orders/              # Default data folder
├── Orders-Export-*.csv     # WooCommerce exports
├── PayoutTransaction*.csv  # CCAvenue payout data
├── Download.CSV           # PayPal transaction data
├── sales-*.xml           # Generated Tally import files
├── missing-payout-*.csv  # Orders without payout data
└── paypal_orders_summary.csv  # PayPal processing details
```

### Troubleshooting

**Common Error Messages:**

- `"SKU 'XXX' not found in mapping"` → Add the SKU to `woo_sku_to_tally.json`
- `"Missing prices for products"` → Add product prices to `tally_product_prices.csv`
- `"Tally product 'XXX' not found"` → Check product name spelling in `tally_products.csv`
- `"No payout amount found for foreign currency order"` → Check payment gateway exports
- `"Configuration file not found"` → Ensure `config.yaml` exists in the project folder

**Getting Help:**

- Check the status messages in the converter window for specific error details
- Ensure all product names match exactly across all configuration files
- Verify that your WooCommerce export includes all required columns
- Check that payment gateway files are properly extracted and named

## License

This project is licensed under the MIT License.
