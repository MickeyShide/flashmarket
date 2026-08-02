-- ==============================================================================
-- FLASHMARKET: DBeaver Fail-Safe SQL Seed Script
-- Uses gen_random_uuid() and CROSS JOIN for variants to prevent parser errors
-- ==============================================================================

-- 1. INSERT PRODUCTS
INSERT INTO products (
    id, name, slug, description, price, currency, status, category_id, brand_id, cover_image, created_at, updated_at, published_at
)
VALUES
(
    'e1000000-0000-0000-0000-000000000001',
    'SIBERIA BOMBER in BLACK',
    'siberia-bomber-black',
    '- 100%-хлопковый вощёный деним' || CHR(10) || '- выдержит до -25' || CHR(10) || '- наполнитель - синтепон+синтепух' || CHR(10) || '- брендированный пуллер',
    12000.00,
    'RUB',
    'ACTIVE',
    '09021c8e-a988-4a45-bf06-fed27e0dcfe2',
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000002',
    'SIBERIA BOMBER in BLUE',
    'siberia-bomber-blue',
    '- 100%-хлопковый вощёный деним' || CHR(10) || '- выдержит до -25' || CHR(10) || '- сине-металлический оттенок вощёной ткани' || CHR(10) || '- фурнитура Marcelo Miracles',
    12000.00,
    'RUB',
    'ACTIVE',
    '09021c8e-a988-4a45-bf06-fed27e0dcfe2',
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000003',
    'EDEC FUR COAT in RED',
    'edec-fur-coat-red',
    '- Искусственный экологичный эко-мех премиум класса' || CHR(10) || '- Объёмный капюшон и брендированный подклад' || CHR(10) || '- Яркий насыщенный красный цвет',
    50000.00,
    'RUB',
    'ACTIVE',
    '09021c8e-a988-4a45-bf06-fed27e0dcfe2',
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1539533018447-63fcce2678e3?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000004',
    'REVERSIBLE FUR ZIP HOODIE in BLACK/BROWN',
    'reversible-fur-zip-hoodie-black-brown',
    '- Двусторонняя куртка-зипка с капюшоном' || CHR(10) || '- Леопардовый искусственный мех изнутри' || CHR(10) || '- Плотный оверсайз хлопок 450 г/м²',
    12900.00,
    'RUB',
    'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1',
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000005',
    'REVERSIBLE FUR ZIP HOODIE in GREY',
    'reversible-fur-zip-hoodie-grey',
    '- Двусторонняя толстовка меланжевого серого оттенка' || CHR(10) || '- Двусторонний замок с металлическим крестом' || CHR(10) || '- Леопардовый подклад',
    12900.00,
    'RUB',
    'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1',
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1509967419530-da38b4704bc6?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000006',
    '10 YEARS GOTHIC LOGO HOODIE in BLACK',
    '10-years-gothic-logo-hoodie-black',
    '- Юбилейная коллекция 10 Years Marcelo Miracles' || CHR(10) || '- Готический вышитый логотип на груди' || CHR(10) || '- Тяжёлый хлопок 480 г/м²',
    10000.00,
    'RUB',
    'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1',
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000007',
    '10 YEARS GOTHIC LOGO HOODIE in GREY',
    '10-years-gothic-logo-hoodie-grey',
    '- Меланжевый светло-серый цвет' || CHR(10) || '- Готический вышитый логотип 10 Years' || CHR(10) || '- Объёмный карман-кенгуру',
    10000.00,
    'RUB',
    'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1',
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000008',
    'REVERSIBLE FUR ZIP HOODIE in BLACK',
    'reversible-fur-zip-hoodie-black',
    '- Чёрная двусторонняя худи-зипка премиум издания' || CHR(10) || '- Мягкий эко-мех изнутри' || CHR(10) || '- Замок-крест',
    19000.00,
    'RUB',
    'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1',
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000009',
    'REVERSIBLE FUR ZIP HOODIE in BROWN',
    'reversible-fur-zip-hoodie-brown',
    '- Глубокий шоколадно-коричневый цвет' || CHR(10) || '- Двусторонний мягкий эко-мех' || CHR(10) || '- Усиленные манжеты',
    19000.00,
    'RUB',
    'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1',
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
)
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    price = EXCLUDED.price,
    cover_image = EXCLUDED.cover_image,
    status = EXCLUDED.status;

-- 2. INSERT PRODUCT VARIANTS AUTOMATICALLY
INSERT INTO product_variants (id, product_id, sku, size, color, is_active, sort_order, created_at)
SELECT
    gen_random_uuid(),
    p.id,
    UPPER(p.slug) || '-' || s.size,
    s.size,
    'Black',
    true,
    s.sort,
    NOW()
FROM products p
CROSS JOIN (
    VALUES ('S', 0), ('M', 1), ('L', 2), ('XL', 3)
) AS s(size, sort)
WHERE p.id IN (
    'e1000000-0000-0000-0000-000000000001',
    'e1000000-0000-0000-0000-000000000002',
    'e1000000-0000-0000-0000-000000000003',
    'e1000000-0000-0000-0000-000000000004',
    'e1000000-0000-0000-0000-000000000005',
    'e1000000-0000-0000-0000-000000000006',
    'e1000000-0000-0000-0000-000000000007',
    'e1000000-0000-0000-0000-000000000008',
    'e1000000-0000-0000-0000-000000000009'
)
ON CONFLICT (sku) DO NOTHING;
