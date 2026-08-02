-- ==============================================================================
-- FLASHMARKET: SQL SEED SCRIPT FOR DBEAVER
-- Contains 100% valid hex UUIDs for PostgreSQL
-- ==============================================================================

-- 1. INSERT PRODUCTS
INSERT INTO products (
    id, name, slug, description, price, currency, status, category_id, brand_id, cover_image, created_at, updated_at, published_at
)
VALUES
-- 1. SIBERIA BOMBER in BLACK (12 000 руб)
(
    'e1000000-0000-0000-0000-000000000001'::uuid,
    'SIBERIA BOMBER in BLACK',
    'siberia-bomber-black',
    '- 100%-хлопковый вощёный деним' || CHR(10) || '- выдержит до -25' || CHR(10) || '- наполнитель - синтепон+синтепух' || CHR(10) || '- брендированный пуллер',
    12000.00,
    'RUB',
    'ACTIVE',
    '09021c8e-a988-4a45-bf06-fed27e0dcfe2'::uuid,
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb'::uuid,
    'https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
-- 2. SIBERIA BOMBER in BLUE (12 000 руб)
(
    'e1000000-0000-0000-0000-000000000002'::uuid,
    'SIBERIA BOMBER in BLUE',
    'siberia-bomber-blue',
    '- 100%-хлопковый вощёный деним' || CHR(10) || '- выдержит до -25' || CHR(10) || '- сине-металлический оттенок вощёной ткани' || CHR(10) || '- фурнитура Marcelo Miracles',
    12000.00,
    'RUB',
    'ACTIVE',
    '09021c8e-a988-4a45-bf06-fed27e0dcfe2'::uuid,
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb'::uuid,
    'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
-- 3. EDEC FUR COAT in RED (50 000 руб)
(
    'e1000000-0000-0000-0000-000000000003'::uuid,
    'EDEC FUR COAT in RED',
    'edec-fur-coat-red',
    '- Искусственный экологичный эко-мех премиум класса' || CHR(10) || '- Объёмный капюшон и брендированный подклад' || CHR(10) || '- Яркий насыщенный красный цвет',
    50000.00,
    'RUB',
    'ACTIVE',
    '09021c8e-a988-4a45-bf06-fed27e0dcfe2'::uuid,
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb'::uuid,
    'https://images.unsplash.com/photo-1539533018447-63fcce2678e3?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
-- 4. REVERSIBLE FUR ZIP HOODIE in BLACK/BROWN (12 900 руб)
(
    'e1000000-0000-0000-0000-000000000004'::uuid,
    'REVERSIBLE FUR ZIP HOODIE in BLACK/BROWN',
    'reversible-fur-zip-hoodie-black-brown',
    '- Двусторонняя куртка-зипка с капюшоном' || CHR(10) || '- Леопардовый искусственный мех изнутри' || CHR(10) || '- Плотный оверсайз хлопок 450 г/м²',
    12900.00,
    'RUB',
    'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1'::uuid,
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb'::uuid,
    'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
-- 5. REVERSIBLE FUR ZIP HOODIE in GREY (12 900 руб)
(
    'e1000000-0000-0000-0000-000000000005'::uuid,
    'REVERSIBLE FUR ZIP HOODIE in GREY',
    'reversible-fur-zip-hoodie-grey',
    '- Двусторонняя толстовка меланжевого серого оттенка' || CHR(10) || '- Двусторонний замок с металлическим крестом' || CHR(10) || '- Леопардовый подклад',
    12900.00,
    'RUB',
    'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1'::uuid,
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb'::uuid,
    'https://images.unsplash.com/photo-1509967419530-da38b4704bc6?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
-- 6. 10 YEARS GOTHIC LOGO HOODIE in BLACK (10 000 руб)
(
    'e1000000-0000-0000-0000-000000000006'::uuid,
    '10 YEARS GOTHIC LOGO HOODIE in BLACK',
    '10-years-gothic-logo-hoodie-black',
    '- Юбилейная коллекция 10 Years Marcelo Miracles' || CHR(10) || '- Готический вышитый логотип на груди' || CHR(10) || '- Тяжёлый хлопок 480 г/м²',
    10000.00,
    'RUB',
    'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1'::uuid,
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb'::uuid,
    'https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
-- 7. 10 YEARS GOTHIC LOGO HOODIE in GREY (10 000 руб)
(
    'e1000000-0000-0000-0000-000000000007'::uuid,
    '10 YEARS GOTHIC LOGO HOODIE in GREY',
    '10-years-gothic-logo-hoodie-grey',
    '- Меланжевый светло-серый цвет' || CHR(10) || '- Готический вышитый логотип 10 Years' || CHR(10) || '- Объёмный карман-кенгуру',
    10000.00,
    'RUB',
    'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1'::uuid,
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb'::uuid,
    'https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
-- 8. REVERSIBLE FUR ZIP HOODIE in BLACK (19 000 руб)
(
    'e1000000-0000-0000-0000-000000000008'::uuid,
    'REVERSIBLE FUR ZIP HOODIE in BLACK',
    'reversible-fur-zip-hoodie-black',
    '- Чёрная двусторонняя худи-зипка премиум издания' || CHR(10) || '- Мягкий эко-мех изнутри' || CHR(10) || '- Замок-крест',
    19000.00,
    'RUB',
    'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1'::uuid,
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb'::uuid,
    'https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
-- 9. REVERSIBLE FUR ZIP HOODIE in BROWN (19 000 руб)
(
    'e1000000-0000-0000-0000-000000000009'::uuid,
    'REVERSIBLE FUR ZIP HOODIE in BROWN',
    'reversible-fur-zip-hoodie-brown',
    '- Глубокий шоколадно-коричневый цвет' || CHR(10) || '- Двусторонний мягкий эко-мех' || CHR(10) || '- Усиленные манжеты',
    19000.00,
    'RUB',
    'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1'::uuid,
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb'::uuid,
    'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
)
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    price = EXCLUDED.price,
    cover_image = EXCLUDED.cover_image,
    status = EXCLUDED.status;

-- 2. INSERT PRODUCT VARIANTS
INSERT INTO product_variants (
    id, product_id, sku, size, color, is_active, sort_order, created_at
)
VALUES
-- Siberia Bomber Black
('f1000000-0001-0000-0000-000000000001'::uuid, 'e1000000-0000-0000-0000-000000000001'::uuid, 'SIBERIA-BOMBER-BLK-S', 'S', 'Black', true, 0, NOW()),
('f1000000-0001-0000-0000-000000000002'::uuid, 'e1000000-0000-0000-0000-000000000001'::uuid, 'SIBERIA-BOMBER-BLK-M', 'M', 'Black', true, 1, NOW()),
('f1000000-0001-0000-0000-000000000003'::uuid, 'e1000000-0000-0000-0000-000000000001'::uuid, 'SIBERIA-BOMBER-BLK-L', 'L', 'Black', true, 2, NOW()),
('f1000000-0001-0000-0000-000000000004'::uuid, 'e1000000-0000-0000-0000-000000000001'::uuid, 'SIBERIA-BOMBER-BLK-XL', 'XL', 'Black', true, 3, NOW()),

-- Siberia Bomber Blue
('f1000000-0002-0000-0000-000000000001'::uuid, 'e1000000-0000-0000-0000-000000000002'::uuid, 'SIBERIA-BOMBER-BLU-S', 'S', 'Blue', true, 0, NOW()),
('f1000000-0002-0000-0000-000000000002'::uuid, 'e1000000-0000-0000-0000-000000000002'::uuid, 'SIBERIA-BOMBER-BLU-M', 'M', 'Blue', true, 1, NOW()),
('f1000000-0002-0000-0000-000000000003'::uuid, 'e1000000-0000-0000-0000-000000000002'::uuid, 'SIBERIA-BOMBER-BLU-L', 'L', 'Blue', true, 2, NOW()),
('f1000000-0002-0000-0000-000000000004'::uuid, 'e1000000-0000-0000-0000-000000000002'::uuid, 'SIBERIA-BOMBER-BLU-XL', 'XL', 'Blue', true, 3, NOW()),

-- Edec Fur Coat Red
('f1000000-0003-0000-0000-000000000001'::uuid, 'e1000000-0000-0000-0000-000000000003'::uuid, 'EDEC-FUR-COAT-RED-S', 'S', 'Red', true, 0, NOW()),
('f1000000-0003-0000-0000-000000000002'::uuid, 'e1000000-0000-0000-0000-000000000003'::uuid, 'EDEC-FUR-COAT-RED-M', 'M', 'Red', true, 1, NOW()),
('f1000000-0003-0000-0000-000000000003'::uuid, 'e1000000-0000-0000-0000-000000000003'::uuid, 'EDEC-FUR-COAT-RED-L', 'L', 'Red', true, 2, NOW()),
('f1000000-0003-0000-0000-000000000004'::uuid, 'e1000000-0000-0000-0000-000000000003'::uuid, 'EDEC-FUR-COAT-RED-XL', 'XL', 'Red', true, 3, NOW()),

-- Reversible Fur Zip Black/Brown
('f1000000-0004-0000-0000-000000000001'::uuid, 'e1000000-0000-0000-0000-000000000004'::uuid, 'REV-FUR-ZIP-BLK-BRN-S', 'S', 'Black/Brown', true, 0, NOW()),
('f1000000-0004-0000-0000-000000000002'::uuid, 'e1000000-0000-0000-0000-000000000004'::uuid, 'REV-FUR-ZIP-BLK-BRN-M', 'M', 'Black/Brown', true, 1, NOW()),
('f1000000-0004-0000-0000-000000000003'::uuid, 'e1000000-0000-0000-0000-000000000004'::uuid, 'REV-FUR-ZIP-BLK-BRN-L', 'L', 'Black/Brown', true, 2, NOW()),
('f1000000-0004-0000-0000-000000000004'::uuid, 'e1000000-0000-0000-0000-000000000004'::uuid, 'REV-FUR-ZIP-BLK-BRN-XL', 'XL', 'Black/Brown', true, 3, NOW()),

-- Reversible Fur Zip Grey
('f1000000-0005-0000-0000-000000000001'::uuid, 'e1000000-0000-0000-0000-000000000005'::uuid, 'REV-FUR-ZIP-GRY-S', 'S', 'Grey', true, 0, NOW()),
('f1000000-0005-0000-0000-000000000002'::uuid, 'e1000000-0000-0000-0000-000000000005'::uuid, 'REV-FUR-ZIP-GRY-M', 'M', 'Grey', true, 1, NOW()),
('f1000000-0005-0000-0000-000000000003'::uuid, 'e1000000-0000-0000-0000-000000000005'::uuid, 'REV-FUR-ZIP-GRY-L', 'L', 'Grey', true, 2, NOW()),
('f1000000-0005-0000-0000-000000000004'::uuid, 'e1000000-0000-0000-0000-000000000005'::uuid, 'REV-FUR-ZIP-GRY-XL', 'XL', 'Grey', true, 3, NOW()),

-- 10 Years Gothic Black
('f1000000-0006-0000-0000-000000000001'::uuid, 'e1000000-0000-0000-0000-000000000006'::uuid, '10Y-GOTHIC-BLK-S', 'S', 'Black', true, 0, NOW()),
('f1000000-0006-0000-0000-000000000002'::uuid, 'e1000000-0000-0000-0000-000000000006'::uuid, '10Y-GOTHIC-BLK-M', 'M', 'Black', true, 1, NOW()),
('f1000000-0006-0000-0000-000000000003'::uuid, 'e1000000-0000-0000-0000-000000000006'::uuid, '10Y-GOTHIC-BLK-L', 'L', 'Black', true, 2, NOW()),
('f1000000-0006-0000-0000-000000000004'::uuid, 'e1000000-0000-0000-0000-000000000006'::uuid, '10Y-GOTHIC-BLK-XL', 'XL', 'Black', true, 3, NOW()),

-- 10 Years Gothic Grey
('f1000000-0007-0000-0000-000000000001'::uuid, 'e1000000-0000-0000-0000-000000000007'::uuid, '10Y-GOTHIC-GRY-S', 'S', 'Grey', true, 0, NOW()),
('f1000000-0007-0000-0000-000000000002'::uuid, 'e1000000-0000-0000-0000-000000000007'::uuid, '10Y-GOTHIC-GRY-M', 'M', 'Grey', true, 1, NOW()),
('f1000000-0007-0000-0000-000000000003'::uuid, 'e1000000-0000-0000-0000-000000000007'::uuid, '10Y-GOTHIC-GRY-L', 'L', 'Grey', true, 2, NOW()),
('f1000000-0007-0000-0000-000000000004'::uuid, 'e1000000-0000-0000-0000-000000000007'::uuid, '10Y-GOTHIC-GRY-XL', 'XL', 'Grey', true, 3, NOW()),

-- Reversible Fur Zip Black
('f1000000-0008-0000-0000-000000000001'::uuid, 'e1000000-0000-0000-0000-000000000008'::uuid, 'REV-FUR-ZIP-BLK-S', 'S', 'Black', true, 0, NOW()),
('f1000000-0008-0000-0000-000000000002'::uuid, 'e1000000-0000-0000-0000-000000000008'::uuid, 'REV-FUR-ZIP-BLK-M', 'M', 'Black', true, 1, NOW()),
('f1000000-0008-0000-0000-000000000003'::uuid, 'e1000000-0000-0000-0000-000000000008'::uuid, 'REV-FUR-ZIP-BLK-L', 'L', 'Black', true, 2, NOW()),
('f1000000-0008-0000-0000-000000000004'::uuid, 'e1000000-0000-0000-0000-000000000008'::uuid, 'REV-FUR-ZIP-BLK-XL', 'XL', 'Black', true, 3, NOW()),

-- Reversible Fur Zip Brown
('f1000000-0009-0000-0000-000000000001'::uuid, 'e1000000-0000-0000-0000-000000000009'::uuid, 'REV-FUR-ZIP-BRN-S', 'S', 'Brown', true, 0, NOW()),
('f1000000-0009-0000-0000-000000000002'::uuid, 'e1000000-0000-0000-0000-000000000009'::uuid, 'REV-FUR-ZIP-BRN-M', 'M', 'Brown', true, 1, NOW()),
('f1000000-0009-0000-0000-000000000003'::uuid, 'e1000000-0000-0000-0000-000000000009'::uuid, 'REV-FUR-ZIP-BRN-L', 'L', 'Brown', true, 2, NOW()),
('f1000000-0009-0000-0000-000000000004'::uuid, 'e1000000-0000-0000-0000-000000000009'::uuid, 'REV-FUR-ZIP-BRN-XL', 'XL', 'Brown', true, 3, NOW())
ON CONFLICT (sku) DO NOTHING;
