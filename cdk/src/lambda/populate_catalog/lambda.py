"""
Lambda function to populate the PostgreSQL RDS instance with product data.
This function is deployed in the same VPC as the RDS instance to have network access.
"""

import json
import os
import boto3
import psycopg2
from psycopg2.extras import execute_values


def get_db_credentials():
    """Retrieve database credentials from Secrets Manager."""
    secret_arn = os.environ["POSTGRES_SECRET_ARN"]
    region = os.environ.get("AWS_REGION", "ap-southeast-2")

    secrets_client = boto3.client("secretsmanager", region_name=region)
    secret_response = secrets_client.get_secret_value(SecretId=secret_arn)
    credentials = json.loads(secret_response["SecretString"])

    return credentials["username"], credentials["password"]


def get_products():
    """Return the list of products to insert."""
    return [
        {
            "product_id": "MILK001",
            "name": "Full Cream Milk",
            "category": "Dairy",
            "price": 4.50,
            "unit": "2L",
            "stock": 0,
            "description": "Fresh full cream milk",
        },
        {
            "product_id": "MILK002",
            "name": "Skim Milk",
            "category": "Dairy",
            "price": 4.20,
            "unit": "2L",
            "stock": 120,
            "description": "Low fat skim milk",
        },
        {
            "product_id": "BREAD001",
            "name": "White Bread",
            "category": "Bakery",
            "price": 3.50,
            "unit": "700g",
            "stock": 80,
            "description": "Fresh white bread loaf",
        },
        {
            "product_id": "BREAD002",
            "name": "Wholemeal Bread",
            "category": "Bakery",
            "price": 4.00,
            "unit": "700g",
            "stock": 65,
            "description": "Healthy wholemeal bread",
        },
        {
            "product_id": "EGG001",
            "name": "Free Range Eggs",
            "category": "Dairy",
            "price": 7.50,
            "unit": "12 pack",
            "stock": 200,
            "description": "Free range eggs",
        },
        {
            "product_id": "APPLE001",
            "name": "Royal Gala Apples",
            "category": "Fruit",
            "price": 5.99,
            "unit": "1kg",
            "stock": 300,
            "description": "Sweet Royal Gala apples",
        },
        {
            "product_id": "APPLE002",
            "name": "Granny Smith Apples",
            "category": "Fruit",
            "price": 4.99,
            "unit": "1kg",
            "stock": 250,
            "description": "Tart Granny Smith apples",
        },
        {
            "product_id": "CHICKEN001",
            "name": "Chicken Breast",
            "category": "Meat",
            "price": 12.99,
            "unit": "1kg",
            "stock": 0,
            "description": "Fresh chicken breast fillets",
        },
        {
            "product_id": "CHICKEN002",
            "name": "Chicken Thighs",
            "category": "Meat",
            "price": 9.99,
            "unit": "1kg",
            "stock": 150,
            "description": "Fresh chicken thigh fillets",
        },
        {
            "product_id": "RICE001",
            "name": "Jasmine Rice",
            "category": "Pantry",
            "price": 8.50,
            "unit": "2kg",
            "stock": 150,
            "description": "Premium jasmine rice",
        },
        {
            "product_id": "RICE002",
            "name": "Basmati Rice",
            "category": "Pantry",
            "price": 9.99,
            "unit": "2kg",
            "stock": 120,
            "description": "Aromatic basmati rice",
        },
        {
            "product_id": "TOMATO001",
            "name": "Tomatoes",
            "category": "Vegetables",
            "price": 6.99,
            "unit": "1kg",
            "stock": 180,
            "description": "Fresh ripe tomatoes",
        },
        {
            "product_id": "CHEESE001",
            "name": "Cheddar Cheese",
            "category": "Dairy",
            "price": 10.99,
            "unit": "500g",
            "stock": 75,
            "description": "Tasty cheddar cheese block",
        },
        {
            "product_id": "CHEESE002",
            "name": "Mozzarella Cheese",
            "category": "Dairy",
            "price": 8.99,
            "unit": "500g",
            "stock": 60,
            "description": "Fresh mozzarella cheese",
        },
        {
            "product_id": "BUTTER001",
            "name": "Salted Butter",
            "category": "Dairy",
            "price": 5.50,
            "unit": "500g",
            "stock": 90,
            "description": "Salted butter block",
        },
        {
            "product_id": "COFFEE001",
            "name": "Ground Coffee",
            "category": "Pantry",
            "price": 12.99,
            "unit": "500g",
            "stock": 110,
            "description": "Medium roast ground coffee",
        },
        {
            "product_id": "COFFEE002",
            "name": "Instant Coffee",
            "category": "Pantry",
            "price": 8.99,
            "unit": "200g",
            "stock": 95,
            "description": "Premium instant coffee",
        },
    ]


def handler(event, context):
    """Lambda handler to populate the database."""

    # Get environment variables
    db_host = os.environ["POSTGRES_HOST"]
    db_port = os.environ["POSTGRES_PORT"]
    db_name = os.environ["POSTGRES_DB"]

    # Check operation mode
    operation = event.get("operation", "insert")  # Options: "insert" or "select"
    clear_existing = event.get("clear_existing", False)

    try:
        # Get credentials
        print("Retrieving database credentials...")
        db_username, db_password = get_db_credentials()

        # Connect to database
        print(f"Connecting to database at {db_host}:{db_port}...")
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_username,
            password=db_password,
            connect_timeout=10,
        )
        cursor = conn.cursor()
        print("Connected successfully!")

        # If operation is "select", just display the catalog and return
        if operation == "select":
            print("Operation: SELECT - Displaying product catalog...")

            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) FROM products
            """)
            total_count = cursor.fetchone()[0]

            if total_count == 0:
                message = "No products found in the catalog."
                print(message)
                cursor.close()
                conn.close()
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": message,
                        "total_products": 0
                    })
                }

            # Retrieve and display all products
            print("\n" + "="*80)
            print("PRODUCT CATALOG - ALL ITEMS")
            print("="*80)
            cursor.execute("""
                SELECT product_id, name, category, price, unit, stock, description
                FROM products
                ORDER BY category, name
            """)
            all_products = cursor.fetchall()

            catalog_list = []
            for product in all_products:
                product_id, name, category, price, unit, stock, description = product
                stock_flag = "✓ IN STOCK" if stock > 0 else "✗ OUT OF STOCK"
                print(f"\n{product_id} | {name}")
                print(f"  Category: {category}")
                print(f"  Price: ${price} per {unit}")
                print(f"  Stock: {stock} units [{stock_flag}]")
                print(f"  Description: {description}")

                catalog_list.append({
                    "product_id": product_id,
                    "name": name,
                    "category": category,
                    "price": float(price),
                    "unit": unit,
                    "stock": stock,
                    "description": description,
                    "in_stock": stock > 0
                })

            print("\n" + "="*80)

            cursor.close()
            conn.close()

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": f"Retrieved {len(catalog_list)} products",
                    "total_products": len(catalog_list),
                    "products": catalog_list
                })
            }

        # Create products table if it doesn't exist (for insert operation)
        print("Operation: INSERT - Populating product catalog...")
        print("Creating products table if it doesn't exist...")
        create_table_query = """
        CREATE TABLE IF NOT EXISTS products (
            product_id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(100) NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            unit VARCHAR(50) NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_query)
        conn.commit()
        print("Products table created/verified")

        # Check existing data
        cursor.execute("SELECT COUNT(*) FROM products")
        existing_count = cursor.fetchone()[0]
        print(f"Found {existing_count} existing products in the database")

        if existing_count > 0 and clear_existing:
            print("Clearing existing products...")
            cursor.execute("DELETE FROM products")
            conn.commit()
            print("Existing products deleted")
        elif existing_count > 0:
            message = f"Database already contains {existing_count} products. Pass 'clear_existing': true in the event to clear them first."
            print(message)
            cursor.close()
            conn.close()
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": message,
                        "existing_count": existing_count,
                        "inserted": 0,
                    }
                ),
            }

        # Insert products
        products = get_products()
        print(f"Inserting {len(products)} products...")

        insert_query = """
        INSERT INTO products (product_id, name, category, price, unit, stock, description)
        VALUES %s
        ON CONFLICT (product_id) DO UPDATE SET
            name = EXCLUDED.name,
            category = EXCLUDED.category,
            price = EXCLUDED.price,
            unit = EXCLUDED.unit,
            stock = EXCLUDED.stock,
            description = EXCLUDED.description,
            updated_at = CURRENT_TIMESTAMP
        """

        values = [
            (
                p["product_id"],
                p["name"],
                p["category"],
                p["price"],
                p["unit"],
                p["stock"],
                p["description"],
            )
            for p in products
        ]

        execute_values(cursor, insert_query, values)
        conn.commit()

        print(f"Successfully inserted/updated {len(products)} products")

        # Get category summary
        categories = {}
        for p in products:
            categories[p["category"]] = categories.get(p["category"], 0) + 1

        # Verify data
        cursor.execute("SELECT COUNT(*) FROM products")
        final_count = cursor.fetchone()[0]

        # Retrieve and display all products in the catalog
        print("\n" + "="*80)
        print("PRODUCT CATALOG - ALL ITEMS")
        print("="*80)
        cursor.execute("""
            SELECT product_id, name, category, price, unit, stock, description
            FROM products
            ORDER BY category, name
        """)
        all_products = cursor.fetchall()

        for product in all_products:
            product_id, name, category, price, unit, stock, description = product
            stock_flag = "✓ IN STOCK" if stock > 0 else "✗ OUT OF STOCK"
            print(f"\n{product_id} | {name}")
            print(f"  Category: {category}")
            print(f"  Price: ${price} per {unit}")
            print(f"  Stock: {stock} units [{stock_flag}]")
            print(f"  Description: {description}")

        print("\n" + "="*80)

        cursor.close()
        conn.close()

        result = {
            "message": f"Successfully populated {len(products)} products",
            "total_products": final_count,
            "categories": categories,
            "inserted": len(products),
        }

        print(json.dumps(result, indent=2))

        return {"statusCode": 200, "body": json.dumps(result)}

    except Exception as e:
        error_message = f"Error populating database: {str(e)}"
        print(error_message)
        import traceback

        traceback.print_exc()

        return {"statusCode": 500, "body": json.dumps({"error": error_message})}
