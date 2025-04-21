# GST Tally

A tool to convert WooCommerce CSV exports to Tally-compatible XML import files with proper GST calculations.

## Features

- Converts WooCommerce order data to Tally XML format
- Handles GST rate calculations for domestic and international sales
- Maps WooCommerce product SKUs to Tally product names
- Supports multiple product types and tax structures

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

## Configuration

The program uses the following configuration files:

1. `config.yaml` - Main configuration file:
   ```yaml
   woo_prefix: woo_orders
   tally_prefix: sales
   tally_products_file: tally_products.csv
   sku_mapping_file: woo_sku_to_tally.json
   ```

2. `tally_products.csv` - Contains Tally product information with the following columns:
   - `Tally Name` - The exact name of the product in Tally
   - `GST Percentage` - GST rate applicable to the product (e.g., "12%")
   - `Godown Name` - Tally godown/warehouse name

3. `woo_sku_to_tally.json` - Maps WooCommerce SKUs to Tally product names:
   ```json
   {
     "SKU1": ["TallyProduct1"],
     "SKU2": ["TallyProduct2", "TallyProduct3"]
   }
   ```

## Preparing WooCommerce Data

1. Export your WooCommerce orders as CSV
2. The CSV should include the following columns:
   - Order ID
   - Order Status
   - Order Date
   - Order Total
   - Billing First Name
   - Billing Last Name
   - Billing Phone
   - Billing Email Address
   - Billing Country
   - SKU
   - Product Name
   - Quantity
   - Item Cost

3. Name your file with the prefix specified in config.yaml (default: `woo_orders.csv`)

## Usage

1. Run the conversion script:
   ```
   uv run python woo_csv_to_tally_xml.py
   ```

2. The program will generate XML files with the prefix specified in config.yaml (default: `sales.xml`)

3. Import the generated XML into Tally using the import functionality

## Troubleshooting

- Ensure all required columns are present in your CSV file
- Check that your SKU mapping contains all product SKUs from your orders
- Verify Tally product names match exactly with the names in your Tally system

## License

This project is licensed under the Apache License 2.0.
