#!/usr/bin/env python3
import argparse
import csv
import json
import yaml


def load_config(config_file="config.yaml"):
    try:
        with open(config_file, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None


def load_sku_mapping(sku_mapping_file):
    try:
        with open(sku_mapping_file, "r", encoding="utf-8") as f:
            return json.load(f)
        print(f"Loaded mapping from {sku_mapping_file}")
    except Exception as e:
        print(f"Error loading SKU mapping: {e}")
        return {}


def create_reverse_mapping(sku_mapping):
    reverse_mapping = {}
    for sku, tally_names in sku_mapping.items():
        for tally_name in tally_names:
            if tally_name not in reverse_mapping:
                reverse_mapping[tally_name] = []
            reverse_mapping[tally_name].append(sku)
    print(f"Created reverse mapping with {len(reverse_mapping)} Tally products")
    return reverse_mapping


def load_woo_products(woo_products_csv):
    products = {}
    try:
        with open(woo_products_csv, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row.get("SKU", "").strip()
                if sku:
                    try:
                        price = float(row.get("Regular price", "0").replace(",", ""))
                        products[sku] = {
                            "price": price,
                            "name": row.get("Name", ""),
                        }
                    except ValueError:
                        print(f"Warning: Invalid price for SKU '{sku}'")

        print(f"Loaded {len(products)} products from {woo_products_csv}")
        return products
    except Exception as e:
        print(f"Error loading WooCommerce products: {e}")
        return {}


def calculate_tally_prices(reverse_mapping, woo_products):
    tally_prices = {}
    for tally_name, skus in reverse_mapping.items():
        if len(skus) == 1:
            sku = skus[0]
            if sku in woo_products:
                tally_prices[tally_name] = woo_products[sku]["price"]
            else:
                print(
                    f"Warning: SKU '{sku}' for Tally product '{tally_name}' not found in WooCommerce data"
                )
    complex_mappings = {
        tally_name: skus
        for tally_name, skus in reverse_mapping.items()
        if len(skus) > 1
    }
    if complex_mappings:
        print(
            f"Found {len(complex_mappings)} Tally products with multiple SKU mappings"
        )
        print("These need to be resolved manually or through business rules")
    return tally_prices


def save_tally_prices(tally_prices, output_file):
    try:
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Tally Name", "Price"])
            for tally_name, price in sorted(tally_prices.items()):
                writer.writerow([tally_name, f"{price:.2f}"])
        print(f"Saved {len(tally_prices)} Tally product prices to {output_file}")
        return True
    except Exception as e:
        print(f"Error saving Tally prices: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate price list for Tally items from WooCommerce products"
    )
    parser.add_argument(
        "-c", "--config", default="config.yaml", help="Path to configuration file"
    )
    parser.add_argument(
        "-w", "--woo-products", required=True, help="Path to WooCommerce products CSV"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="tally_prices.csv",
        help="Output file for Tally prices",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    if not config:
        return
    sku_mapping_file = config.get("sku_mapping_file", "woo_sku_to_tally.json")
    sku_mapping = load_sku_mapping(sku_mapping_file)
    if not sku_mapping:
        return
    reverse_mapping = create_reverse_mapping(sku_mapping)
    if not reverse_mapping:
        return
    woo_products = load_woo_products(args.woo_products)
    if not woo_products:
        return
    tally_prices = calculate_tally_prices(reverse_mapping, woo_products)
    if not tally_prices:
        return
    save_tally_prices(tally_prices, args.output)


if __name__ == "__main__":
    main()
