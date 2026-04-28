"""
worker.py - Queue Consumer (Module 2: Order Processing)
Đọc message từ RabbitMQ và insert vào MySQL Database
"""

import os
import json
import time
import pika
import mysql.connector
from mysql.connector import Error

# ─────────────────────────────────────
# Kết nối MySQL với retry
# ─────────────────────────────────────
def get_db_connection():
    host     = os.environ.get("MYSQL_HOST", "localhost")
    user     = os.environ.get("MYSQL_USER", "root")
    password = os.environ.get("MYSQL_PASSWORD", "rootpassword")
    database = os.environ.get("MYSQL_DB", "noah_db")

    for attempt in range(10):
        try:
            conn = mysql.connector.connect(
                host=host, user=user,
                password=password, database=database
            )
            print(f"[Worker] Connected to MySQL!")
            return conn
        except Error as e:
            print(f"[Worker] MySQL connection failed (attempt {attempt+1}/10): {e}")
            time.sleep(5)

    raise Exception("Cannot connect to MySQL after 10 attempts")


# ─────────────────────────────────────
# Xử lý từng message từ Queue
# ─────────────────────────────────────
def process_message(ch, method, properties, body):
    try:
        data = json.loads(body)
        order_id   = data["order_id"]
        product_id = data["product_id"]
        quantity   = data["quantity"]

        print(f"[Worker] Processing order_id={order_id}, product_id={product_id}, qty={quantity}")

        conn   = get_db_connection()
        cursor = conn.cursor()

        # Kiểm tra product tồn tại
        cursor.execute("SELECT id FROM products WHERE id = %s", (product_id,))
        if not cursor.fetchone():
            print(f"[Worker] ERROR: product_id={product_id} không tồn tại → skip")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Kiểm tra duplicate order
        cursor.execute("SELECT id FROM orders WHERE id = %s", (order_id,))
        if cursor.fetchone():
            print(f"[Worker] WARNING: order_id={order_id} đã tồn tại → skip (duplicate)")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Insert vào bảng orders
        cursor.execute(
            "INSERT INTO orders (id, product_id, quantity) VALUES (%s, %s, %s)",
            (order_id, product_id, quantity)
        )
        conn.commit()
        print(f"[Worker] ✅ Inserted order_id={order_id} successfully")

        cursor.close()
        conn.close()

        # ACK: xác nhận đã xử lý xong
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"[Worker] ❌ Error processing message: {e}")
        # NACK: không requeue để tránh lặp vô hạn
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


# ─────────────────────────────────────
# Kết nối RabbitMQ với retry
# ─────────────────────────────────────
def get_rabbitmq_connection():
    host     = os.environ.get("RABBITMQ_HOST", "localhost")
    user     = os.environ.get("RABBITMQ_USER", "guest")
    password = os.environ.get("RABBITMQ_PASS", "guest")

    credentials = pika.PlainCredentials(user, password)
    parameters  = pika.ConnectionParameters(
        host=host,
        credentials=credentials,
        heartbeat=600
    )

    for attempt in range(10):
        try:
            conn = pika.BlockingConnection(parameters)
            print("[Worker] Connected to RabbitMQ!")
            return conn
        except Exception as e:
            print(f"[Worker] RabbitMQ connection failed (attempt {attempt+1}/10): {e}")
            time.sleep(5)

    raise Exception("Cannot connect to RabbitMQ after 10 attempts")


# ─────────────────────────────────────
# Main: Start consuming
# ─────────────────────────────────────
def main():
    print("[Worker] Starting...")
    connection = get_rabbitmq_connection()
    channel    = connection.channel()

    channel.queue_declare(queue="order_queue", durable=True)
    channel.basic_qos(prefetch_count=1)  # Xử lý 1 message tại 1 thời điểm
    channel.basic_consume(queue="order_queue", on_message_callback=process_message)

    print("[Worker] 🚀 Waiting for messages...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
