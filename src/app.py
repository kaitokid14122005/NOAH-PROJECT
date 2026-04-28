"""
app.py - Flask API (Module 2: Order Processing)
Nhận file CSV và đẩy từng record vào RabbitMQ queue
"""

import os
import csv
import json
import pika
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

# ─────────────────────────────────────
# Kết nối RabbitMQ với retry
# ─────────────────────────────────────
def get_rabbitmq_connection():
    host = os.environ.get("RABBITMQ_HOST", "localhost")
    user = os.environ.get("RABBITMQ_USER", "guest")
    password = os.environ.get("RABBITMQ_PASS", "guest")

    credentials = pika.PlainCredentials(user, password)
    parameters = pika.ConnectionParameters(
        host=host,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )

    for attempt in range(5):
        try:
            connection = pika.BlockingConnection(parameters)
            print(f"[Flask] Connected to RabbitMQ!")
            return connection
        except Exception as e:
            print(f"[Flask] RabbitMQ connection failed (attempt {attempt+1}/5): {e}")
            time.sleep(3)

    raise Exception("Cannot connect to RabbitMQ after 5 attempts")


# ─────────────────────────────────────
# Route: Health Check
# ─────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "flask-api"}), 200


# ─────────────────────────────────────
# Route: Upload CSV Orders
# ─────────────────────────────────────
@app.route("/api/upload", methods=["POST"])
def upload_csv():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if not file.filename.endswith(".csv"):
        return jsonify({"error": "Only CSV files are accepted"}), 400

    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        channel.queue_declare(queue="order_queue", durable=True)

        content = file.stream.read().decode("utf-8").splitlines()
        reader = csv.DictReader(content)

        sent = 0
        errors = 0

        for row in reader:
            try:
                order_id  = int(row["order_id"])
                product_id = int(row["product_id"])
                quantity   = int(row["quantity"])

                message = json.dumps({
                    "order_id":   order_id,
                    "product_id": product_id,
                    "quantity":   quantity
                })

                channel.basic_publish(
                    exchange="",
                    routing_key="order_queue",
                    body=message,
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                sent += 1

            except Exception as e:
                print(f"[Flask] Skipping invalid row: {row} → {e}")
                errors += 1

        connection.close()

        return jsonify({
            "message": "CSV processed successfully",
            "sent_to_queue": sent,
            "skipped_rows": errors
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
