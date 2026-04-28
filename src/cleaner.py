from logger import log_error

EXPECTED_COLUMNS = 2


def clean_csv(input_file):
    cleaned_data = {}
    
    total_rows = 0
    fixed_rows = 0
    skipped_rows = 0

    with open(input_file, "r", encoding="utf-8") as file:
        for line_num, line in enumerate(file, start=1):
            total_rows += 1

            try:
                line = line.strip()
                parts = line.split(",")

                # 🔹 bỏ header
                if line_num == 1:
                    continue

                # 🔥 EXTRA_COLUMNS
                if len(parts) > EXPECTED_COLUMNS:
                    log_error(f"Line {line_num}: EXTRA_COLUMNS ({len(parts)} → {EXPECTED_COLUMNS}) → trimmed")
                    parts = parts[:EXPECTED_COLUMNS]
                    fixed_rows += 1

                # 🔥 thiếu cột
                if len(parts) < EXPECTED_COLUMNS:
                    log_error(f"Line {line_num}: Missing columns → skipped")
                    skipped_rows += 1
                    continue

                # 🔥 convert dữ liệu
                try:
                    product_id = int(parts[0])
                    quantity = int(parts[1])

                    if quantity < 0:
                        raise ValueError("Negative quantity")

                except Exception as e:
                    log_error(f"Line {line_num}: Invalid data → {e}")
                    skipped_rows += 1
                    continue

                # 🔥 xử lý duplicate (cộng dồn)
                if product_id in cleaned_data:
                    cleaned_data[product_id] += quantity
                else:
                    cleaned_data[product_id] = quantity

            except Exception as e:
                log_error(f"Line {line_num}: Exception → {e}")
                skipped_rows += 1
                continue

    return cleaned_data, total_rows, fixed_rows, skipped_rows


def write_clean_csv(data, output_file):
    import os
    os.makedirs("output", exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("product_id,quantity\n")

        # 🔥 SORT product_id tăng dần
        for product_id in sorted(data.keys()):
            f.write(f"{product_id},{data[product_id]}\n")