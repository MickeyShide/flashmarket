#!/usr/bin/env python3
"""Seed script for FlashMarket — populates all databases with test data via API."""

import json
import sys
import time
import urllib.request
import urllib.error

BASE = "http://localhost:8080"

def api_post(path, data):
    """POST JSON to API and return parsed response."""
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        print(f"  ⚠ {e.code} {path}: {detail[:200]}")
        return None

def api_get(path):
    """GET from API and return parsed response."""
    req = urllib.request.Request(BASE + path, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        print(f"  ⚠ {e.code} {path}: {detail[:200]}")
        return None

def api_post_auth(path, data, token):
    """POST JSON with auth token."""
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        print(f"  ⚠ {e.code} {path}: {detail[:200]}")
        return None


def main():
    print("=" * 60)
    print("  FLASHMARKET SEED SCRIPT")
    print("=" * 60)

    # -----------------------------------------------------------
    # 1. CATEGORIES
    # -----------------------------------------------------------
    print("\n📂 Creating categories...")

    categories = [
        {"name": "Верхняя одежда", "slug": "outerwear"},
        {"name": "Худи и свитеры", "slug": "hoodies"},
        {"name": "Сумки", "slug": "bags"},
        {"name": "Аксессуары", "slug": "accessories"},
        {"name": "Обувь", "slug": "shoes"},
    ]

    created_cats = {}
    for cat in categories:
        result = api_post("/api/v1/categories", cat)
        if result:
            created_cats[cat["slug"]] = result["id"]
            print(f"  ✓ {cat['name']} → {result['id']}")
        else:
            # Try to get existing
            print(f"  → Category '{cat['name']}' may already exist, continuing...")

    # If no categories created, try loading existing ones
    if not created_cats:
        print("  Loading existing categories...")
        tree = api_get("/api/v1/categories")
        if tree:
            for node in tree:
                created_cats[node["slug"]] = node["id"]
                print(f"  ✓ Found: {node['name']} → {node['id']}")

    if not created_cats:
        print("  ✗ No categories available. Exiting.")
        sys.exit(1)

    # -----------------------------------------------------------
    # 1.5 BRANDS
    # -----------------------------------------------------------
    print("\n🏢 Creating brands...")

    brands = [
        {
            "name": "Marcelo Miracles",
            "slug": "marcelo-miracles",
            "description": "Российский стритвир-бренд лимитированных дропов.",
            "logo_url": "https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=800&q=80",
        },
        {
            "name": "Flash Sect",
            "slug": "flash-sect",
            "description": "Эксклюзивные оверсайз худи и аксессуары.",
            "logo_url": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=800&q=80",
        },
        {
            "name": "Routine",
            "slug": "routine",
            "description": "Премиальная минималистичная одежда и аксессуары.",
            "logo_url": "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=800&q=80",
        },
        {
            "name": "Flash Market",
            "slug": "flash-market",
            "description": "Официальный бренд эксклюзивного мерча FlashMarket.",
            "logo_url": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=800&q=80",
        },
    ]

    created_brands = {}
    for brand in brands:
        result = api_post("/api/v1/brands", brand)
        if result:
            created_brands[brand["slug"]] = result["id"]
            print(f"  ✓ {brand['name']} → {result['id']}")
        else:
            print(f"  → Brand '{brand['name']}' may already exist, continuing...")

    if not created_brands:
        print("  Loading existing brands...")
        all_b = api_get("/api/v1/brands")
        if all_b:
            for b in all_b:
                created_brands[b["slug"]] = b["id"]
                print(f"  ✓ Found: {b['name']} → {b['id']}")

    # -----------------------------------------------------------
    # 2. PRODUCTS
    # -----------------------------------------------------------
    print("\n🏷️  Creating products...")

    # Get first available category IDs and brand IDs
    cat_ids = list(created_cats.values())
    b_marcelo = created_brands.get("marcelo-miracles")
    b_flash_sect = created_brands.get("flash-sect")
    b_routine = created_brands.get("routine")
    b_flash_market = created_brands.get("flash-market")

    products = [
        {
            "name": "Marcelo Miracles Reversible Bomber",
            "description": "Двусторонний бомбер из капсульной коллекции Marcelo Miracles '26. Водоотталкивающая ткань, контрастная подкладка.",
            "price": "24900.00",
            "currency": "RUB",
            "category_id": cat_ids[0] if len(cat_ids) > 0 else cat_ids[0],
            "brand_id": b_marcelo,
            "status": "ACTIVE",
        },
        {
            "name": "Flash Sect Oversized Hoodie",
            "description": "Оверсайз-худи Flash Sect с вышитым логотипом на груди. Плотный хлопок 400 г/м².",
            "price": "12900.00",
            "currency": "RUB",
            "category_id": cat_ids[1] if len(cat_ids) > 1 else cat_ids[0],
            "brand_id": b_flash_sect,
            "status": "ACTIVE",
        },
        {
            "name": "Routine Leather Tote Bag",
            "description": "Кожаная сумка-тоут Routine из натуральной зернистой кожи. Внутренний карман на молнии.",
            "price": "18500.00",
            "currency": "RUB",
            "category_id": cat_ids[2] if len(cat_ids) > 2 else cat_ids[0],
            "brand_id": b_routine,
            "status": "ACTIVE",
        },
        {
            "name": "FM Titanium Chain Bracelet",
            "description": "Браслет-цепь из титанового сплава с гравировкой FlashMarket. Регулируемый размер.",
            "price": "7900.00",
            "currency": "RUB",
            "category_id": cat_ids[3] if len(cat_ids) > 3 else cat_ids[0],
            "brand_id": b_flash_market,
            "status": "ACTIVE",
        },
        {
            "name": "Marcelo Miracles Track Pants",
            "description": "Спортивные брюки с боковыми лампасами и вышитым логотипом. Эластичный пояс.",
            "price": "15400.00",
            "currency": "RUB",
            "category_id": cat_ids[0] if len(cat_ids) > 0 else cat_ids[0],
            "brand_id": b_marcelo,
            "status": "ACTIVE",
        },
        {
            "name": "Flash Sect Beanie",
            "description": "Шапка-бини из мериносовой шерсти с нашивкой Flash Sect. Один размер.",
            "price": "4200.00",
            "currency": "RUB",
            "category_id": cat_ids[3] if len(cat_ids) > 3 else cat_ids[0],
            "brand_id": b_flash_sect,
            "status": "ACTIVE",
        },
        {
            "name": "Routine Minimal Sneakers",
            "description": "Минималистичные кроссовки из натуральной кожи. Анатомическая стелька, каучуковая подошва.",
            "price": "21000.00",
            "currency": "RUB",
            "category_id": cat_ids[4] if len(cat_ids) > 4 else cat_ids[0],
            "brand_id": b_routine,
            "status": "ACTIVE",
        },
        {
            "name": "FM Limited Drop Cap",
            "description": "Кепка лимитированной серии с вышивкой FM. Хлопок, регулируемая застёжка.",
            "price": "3500.00",
            "currency": "RUB",
            "category_id": cat_ids[3] if len(cat_ids) > 3 else cat_ids[0],
            "brand_id": b_flash_market,
            "status": "ACTIVE",
        },
    ]

    created_products = []
    for prod in products:
        result = api_post("/api/v1/products", prod)
        if result:
            created_products.append(result)
            print(f"  ✓ {result['name']} — {result['price']} {result['currency']} → {result['id']}")
        else:
            print(f"  → Product '{prod['name']}' may already exist, continuing...")

    # If no products were created, load existing
    if not created_products:
        print("  Loading existing products...")
        data = api_get("/api/v1/products")
        if data and data.get("items"):
            created_products = data["items"]
            for p in created_products:
                print(f"  ✓ Found: {p['name']} → {p['id']}")

    if not created_products:
        print("  ✗ No products available. Exiting.")
        sys.exit(1)

    # -----------------------------------------------------------
    # 3. INVENTORY (STOCK)
    # -----------------------------------------------------------
    print("\n📦 Creating stock entries...")

    stock_amounts = [25, 50, 10, 100, 30, 3, 15, 0]  # Last one: out of stock

    for i, product in enumerate(created_products):
        total = stock_amounts[i] if i < len(stock_amounts) else 20
        result = api_post("/api/v1/stocks", {
            "product_id": product["id"],
            "total": total,
        })
        if result:
            print(f"  ✓ {product['name'][:40]:40s} → total: {result['total']}, available: {result['available']}")
        else:
            print(f"  → Stock for '{product['name'][:30]}' may already exist")

    # -----------------------------------------------------------
    # 4. TEST USER
    # -----------------------------------------------------------
    print("\n👤 Creating test user...")

    user_data = {
        "email": "test@flashmarket.ru",
        "password": "TestPassword123!",
        "full_name": "Тестовый Покупатель",
    }

    auth_result = api_post("/auth/register", user_data)
    token = None
    user_id = None

    if auth_result and auth_result.get("tokens"):
        token = auth_result["tokens"]["access_token"]
        user_id = auth_result["user"]["id"]
        print(f"  ✓ User created: {auth_result['user']['email']} → {user_id}")
    else:
        # Try login instead
        print("  → User may exist, trying login...")
        auth_result = api_post("/auth/login", {
            "email": user_data["email"],
            "password": user_data["password"],
        })
        if auth_result and auth_result.get("tokens"):
            token = auth_result["tokens"]["access_token"]
            user_id = auth_result["user"]["id"]
            print(f"  ✓ Logged in: {auth_result['user']['email']} → {user_id}")
        else:
            print("  ⚠ Could not create or login test user. Skipping orders/payments/notifications.")

    # -----------------------------------------------------------
    # 5. TEST ORDER (reserve → order)
    # -----------------------------------------------------------
    if token and user_id and len(created_products) >= 2:
        print("\n🛒 Creating test order...")

        # Reserve stock for first product
        product = created_products[0]
        reserve_result = api_post(f"/api/v1/stocks/{product['id']}/reserve", {
            "user_id": user_id,
            "quantity": 1,
        })

        if reserve_result and reserve_result.get("reservation"):
            reservation = reserve_result["reservation"]
            print(f"  ✓ Reserved: {product['name'][:30]} → reservation {reservation['id']}")

            # Create order
            price_kopecks = round(float(product["price"]) * 100)
            order_result = api_post("/api/v1/orders", {
                "user_id": user_id,
                "product_id": product["id"],
                "product_name": product["name"],
                "price": price_kopecks,
                "currency": product["currency"],
                "quantity": 1,
                "reservation_id": reservation["id"],
            })

            if order_result:
                order_id = order_result["id"]
                print(f"  ✓ Order created: {order_result['product_name'][:30]} → {order_id} [{order_result['status']}]")

                # -----------------------------------------------------------
                # 6. TEST PAYMENT
                # -----------------------------------------------------------
                print("\n💳 Creating test payment...")

                payment_result = api_post("/api/v1/payments", {
                    "order_id": order_id,
                    "user_id": user_id,
                    "amount": price_kopecks,
                    "currency": product["currency"],
                    "provider": "mock",
                })

                if payment_result:
                    print(f"  ✓ Payment created: {payment_result['id']} [{payment_result['status']}]")
                    # Note: NOT confirming payment — leave it for user to test in UI
                else:
                    print("  ⚠ Payment creation failed")
            else:
                print("  ⚠ Order creation failed")
        else:
            print("  ⚠ Stock reservation failed")

        # Create a second order (already paid) for variety
        print("\n🛒 Creating second test order (confirmed)...")
        product2 = created_products[1]
        reserve2 = api_post(f"/api/v1/stocks/{product2['id']}/reserve", {
            "user_id": user_id,
            "quantity": 2,
        })

        if reserve2 and reserve2.get("reservation"):
            price_kopecks2 = round(float(product2["price"]) * 100)
            order2 = api_post("/api/v1/orders", {
                "user_id": user_id,
                "product_id": product2["id"],
                "product_name": product2["name"],
                "price": price_kopecks2,
                "currency": product2["currency"],
                "quantity": 2,
                "reservation_id": reserve2["reservation"]["id"],
            })
            if order2:
                print(f"  ✓ Order 2: {order2['product_name'][:30]} × 2 → {order2['id']} [{order2['status']}]")

                # Create and confirm payment for this order
                payment2 = api_post("/api/v1/payments", {
                    "order_id": order2["id"],
                    "user_id": user_id,
                    "amount": price_kopecks2 * 2,
                    "currency": product2["currency"],
                    "provider": "mock",
                })
                if payment2:
                    # Confirm the payment
                    confirm_req = urllib.request.Request(
                        f"{BASE}/api/v1/payments/{payment2['id']}/confirm",
                        headers={"Content-Type": "application/json", "Accept": "application/json"},
                        method="POST",
                    )
                    try:
                        with urllib.request.urlopen(confirm_req, timeout=10) as resp:
                            confirmed = json.loads(resp.read())
                            print(f"  ✓ Payment confirmed: {confirmed['id']} [{confirmed['status']}]")
                    except Exception as e:
                        print(f"  ⚠ Payment confirm failed: {e}")

    # -----------------------------------------------------------
    # 7. TEST NOTIFICATION
    # -----------------------------------------------------------
    if user_id:
        print("\n🔔 Creating test notifications...")

        notifications = [
            {
                "user_id": user_id,
                "channel": "EMAIL",
                "subject": "Добро пожаловать в FlashMarket!",
                "body": "Вы успешно зарегистрировались. Ознакомьтесь с нашим каталогом эксклюзивных дропов.",
                "recipient": "test@flashmarket.ru",
            },
            {
                "user_id": user_id,
                "channel": "EMAIL",
                "subject": "Ваш заказ оформлен",
                "body": "Заказ на Marcelo Miracles Reversible Bomber успешно создан. Ожидайте подтверждения оплаты.",
                "recipient": "test@flashmarket.ru",
            },
            {
                "user_id": user_id,
                "channel": "PUSH",
                "subject": "Новый дроп!",
                "body": "Коллекция Flash Sect уже доступна. Торопитесь — количество ограничено!",
                "recipient": "test@flashmarket.ru",
            },
        ]

        for notif in notifications:
            result = api_post("/api/v1/notifications", notif)
            if result:
                print(f"  ✓ [{result['channel']}] {result['subject'][:40]} → {result['id']} [{result['status']}]")
            else:
                print(f"  ⚠ Notification '{notif['subject'][:30]}' failed")

    # -----------------------------------------------------------
    # DONE
    # -----------------------------------------------------------
    print("\n" + "=" * 60)
    print("  ✅ SEED COMPLETE!")
    print("=" * 60)
    print(f"\n  Categories: {len(created_cats)}")
    print(f"  Products:   {len(created_products)}")
    print(f"  Test user:  {'test@flashmarket.ru / TestPassword123!' if user_id else 'N/A'}")
    print(f"\n  Open http://localhost:8080 to verify")
    print()


if __name__ == "__main__":
    main()
