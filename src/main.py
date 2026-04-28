from cleaner import clean_csv, write_clean_csv

INPUT_FILE = "data/inventory.csv"
OUTPUT_FILE = "output/clean_inventory.csv"


def main():
    print("Starting data cleaning...")

    data, total, fixed, skipped = clean_csv(INPUT_FILE)

    write_clean_csv(data, OUTPUT_FILE)

    print("\n=== SUMMARY ===")
    print(f"Total rows: {total}")
    print(f"Fixed rows (EXTRA_COLUMNS): {fixed}")
    print(f"Skipped rows: {skipped}")
    print(f"Valid unique products: {len(data)}")

    print("\nCleaning completed!")
    print("Check logs/error.log for details.")


if __name__ == "__main__":
    main()