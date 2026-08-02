-- ==============================================================================
-- FLASHMARKET: FULL CLEAN DATABASE SEED SCRIPT
-- Live catalog from https://ru.marcelomiracles.com/
-- Ready to run on an EMPTY database in DBeaver (Alt + X)
-- ==============================================================================

BEGIN;

-- 1. CREATE BRAND: Marcelo Miracles
INSERT INTO brands (id, name, slug, description, logo_url, created_at)
VALUES (
    '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'Marcelo Miracles',
    'marcelo_miracles',
    'Официальный бренд стритвир одежды лимитированных дропов.',
    'https://aws.kiiiosk.store/uploads/shop/11204/favicons/14dfa619-36e1-456d-a1b3-e8352d3bb6b2.png',
    NOW()
)
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    logo_url = EXCLUDED.logo_url;

-- 2. CREATE CATEGORIES
INSERT INTO categories (id, name, slug, created_at)
VALUES 
    ('09021c8e-a988-4a45-bf06-fed27e0dcfe2', 'Куртки', 'jackets', NOW()),
    ('019fc26b-cf03-7037-8029-f617d4c135a1', 'Худи', 'hoodies', NOW()),
    ('09021c8e-a988-4a45-bf06-fed27e0dcfe1', 'Обувь', 'shoes', NOW()),
    ('019fc26c-d0fe-7411-93ed-bba06e1bd9e8', 'Джинсы', 'jeans', NOW()),
    ('019fc26c-a07e-7344-9605-54febf0df57b', 'Штаны', 'pants', NOW()),
    ('019fc26c-4b9f-71e8-94cb-387a6d62488e', 'Футболки', 'tshirts', NOW()),
    ('019fc26c-75f1-74b4-ba38-2cd59ca5e5a4', 'Лонгсливы', 'longsleeves', NOW()),
    ('019fc26c-f20a-744c-97c9-5db86ae9c1c4', 'Сумки', 'bags', NOW()),
    ('019fc26c-109a-74c6-b8e5-4a252ecf4e12', 'Аксессуары', 'accessories', NOW())
ON CONFLICT (slug) DO NOTHING;

-- 3. INSERT PRODUCTS FROM RU.MARCELOMIRACLES.COM
INSERT INTO products (
    id, name, slug, description, price, currency, status, category_id, brand_id, cover_image, created_at, updated_at, published_at
)
VALUES
-- --- КУРТКИ ---
(
    'e1000000-0000-0000-0000-000000000001',
    'SIBERIA BOMBER in BLACK',
    'siberia-bomber-black',
    '- 100%-хлопковый вощёный деним' || CHR(10) || '- выдержит до -25' || CHR(10) || '- наполнитель - синтепон+синтепух' || CHR(10) || '- брендированный пуллер',
    12000.00, 'RUB', 'ACTIVE',
    '09021c8e-a988-4a45-bf06-fed27e0dcfe2', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000002',
    'SIBERIA BOMBER in BLUE',
    'siberia-bomber-blue',
    '- 100%-хлопковый вощёный деним' || CHR(10) || '- выдержит до -25' || CHR(10) || '- сине-металлический оттенок вощёной ткани' || CHR(10) || '- фурнитура Marcelo Miracles',
    12000.00, 'RUB', 'ACTIVE',
    '09021c8e-a988-4a45-bf06-fed27e0dcfe2', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000003',
    'EDEC FUR COAT in RED',
    'edec-fur-coat-red',
    '- Искусственный экологичный эко-мех премиум класса' || CHR(10) || '- Объёмный капюшон и брендированный подклад' || CHR(10) || '- Яркий насыщенный красный цвет',
    50000.00, 'RUB', 'ACTIVE',
    '09021c8e-a988-4a45-bf06-fed27e0dcfe2', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1539533018447-63fcce2678e3?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),

-- --- ХУДИ И ЗИПКИ ---
(
    'e1000000-0000-0000-0000-000000000004',
    'REVERSIBLE FUR ZIP HOODIE in GREY',
    'reversible-fur-zip-hoodie-in-grey',
    '- Двусторонняя толстовка меланжевого серого оттенка' || CHR(10) || '- Двусторонний замок с металлическим крестом' || CHR(10) || '- Леопардовый искусственный мех изнутри',
    12900.00, 'RUB', 'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/846443/___________.png',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000005',
    'REVERSIBLE FUR ZIP HOODIE in BLACK/BROWN',
    'reversible-fur-zip-hoodie-in-black-brown',
    '- Двусторонняя куртка-зипка с капюшоном' || CHR(10) || '- Леопардовый искусственный мех изнутри' || CHR(10) || '- Плотный оверсайз хлопок 450 г/м²',
    12900.00, 'RUB', 'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/859003/____________________________________3.png',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000006',
    '10 YEARS GOTHIC LOGO HOODIE in BLACK',
    '10-years-gothic-logo-hoodie-black',
    '- Юбилейная коллекция 10 Years Marcelo Miracles' || CHR(10) || '- Готический вышитый логотип на груди' || CHR(10) || '- Тяжёлый хлопок 480 г/м²',
    10000.00, 'RUB', 'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000007',
    '10 YEARS GOTHIC LOGO HOODIE in GREY',
    '10-years-gothic-logo-hoodie-grey',
    '- Меланжевый светло-серый цвет' || CHR(10) || '- Готический вышитый логотип 10 Years' || CHR(10) || '- Объёмный карман-кенгуру',
    10000.00, 'RUB', 'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000008',
    'REVERSIBLE FUR ZIP HOODIE in BLACK',
    'reversible-fur-zip-hoodie-black',
    '- Чёрная двусторонняя худи-зипка премиум издания' || CHR(10) || '- Мягкий эко-мех изнутри' || CHR(10) || '- Замок-крест',
    19000.00, 'RUB', 'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000009',
    'REVERSIBLE FUR ZIP HOODIE in BROWN',
    'reversible-fur-zip-hoodie-brown',
    '- Глубокий шоколадно-коричневый цвет' || CHR(10) || '- Двусторонний мягкий эко-мех' || CHR(10) || '- Усиленные манжеты',
    19000.00, 'RUB', 'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=800&q=80',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000010',
    'ADDRESS LOGO ZIP-HOODIE in BLACK',
    'address-logo-zip-hoodie-in-black',
    '- Оверсайз зипка с фиштейлом' || CHR(10) || '- Вышитый адресный принтовый логотип' || CHR(10) || '- Ткань хлопок 450г',
    8930.00, 'RUB', 'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/844851/h_b1.png',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000011',
    'ADDRESS LOGO ZIP-HOODIE in GREY',
    'address-logo-zip-hoodie-in-grey',
    '- Серый меланж зип-худи' || CHR(10) || '- Металлическая фурнитура YKK' || CHR(10) || '- Фирменная вышивка',
    8930.00, 'RUB', 'ACTIVE',
    '019fc26b-cf03-7037-8029-f617d4c135a1', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/858877/ZippO________________________.png',
    NOW(), NOW(), NOW()
),

-- --- ОБУВЬ ---
(
    'e1000000-0000-0000-0000-000000000012',
    'BOOTLEG BOOTS in BLACK',
    'bootleg-boots-in-black',
    '- Массивные ботинки из натуральной вощёной кожи' || CHR(10) || '- Высокая тракторная подошва' || CHR(10) || '- Металлические люверсы и тиснение',
    11900.00, 'RUB', 'ACTIVE',
    '09021c8e-a988-4a45-bf06-fed27e0dcfe1', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/858848/3__1_.png',
    NOW(), NOW(), NOW()
),

-- --- ДЖИНСЫ ---
(
    'e1000000-0000-0000-0000-000000000013',
    '27 CLUB DISTRESSED DENIM in BLUE',
    '27-club-distressed-denim-in-blue',
    '- Рваный широкие джинсы 27 Club' || CHR(10) || '- Синий стираный деним с потертостями' || CHR(10) || '- Фирменная металлическая фурнитура',
    9600.00, 'RUB', 'ACTIVE',
    '019fc26c-d0fe-7411-93ed-bba06e1bd9e8', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/852980/____3.png',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000014',
    '27 CLUB DISTRESSED DENIM in GREY',
    '27-club-distressed-denim-in-grey',
    '- Серые джинсы прямого широкого кроя' || CHR(10) || '- Эффект старения и ручные потертости' || CHR(10) || '- Кожаный патч сзади',
    9600.00, 'RUB', 'ACTIVE',
    '019fc26c-d0fe-7411-93ed-bba06e1bd9e8', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/852978/____1.png',
    NOW(), NOW(), NOW()
),

-- --- ЛОНГСЛИВЫ ---
(
    'e1000000-0000-0000-0000-000000000015',
    'ADDRESS LOGO LONGSLEEVE in WASHED BLACK',
    'address-logo-longsleeve-in-washed-black',
    '- Оверсайз лонгслив со стираным эффектом (Washed Black)' || CHR(10) || '- Принт Address Logo на груди и спине',
    4650.00, 'RUB', 'ACTIVE',
    '019fc26c-75f1-74b4-ba38-2cd59ca5e5a4', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/859223/________________________1.png',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000016',
    'ADDRESS LOGO LONGSLEEVE in WASHED GREY',
    'address-logo-longsleeve-in-washed-grey',
    '- Винтажный серый оверсайз лонгслив' || CHR(10) || '- Хлопок 240 г/м²',
    4650.00, 'RUB', 'ACTIVE',
    '019fc26c-75f1-74b4-ba38-2cd59ca5e5a4', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/859224/________________________2.png',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000017',
    'ADDRESS LOGO LONGSLEEVE in BLACK',
    'address-logo-longsleeve-in-black',
    '- Классический чёрный лонгслив оверсайз кроя' || CHR(10) || '- Шелкография высокой чёткости',
    4650.00, 'RUB', 'ACTIVE',
    '019fc26c-75f1-74b4-ba38-2cd59ca5e5a4', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/858884/_____1.png',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000018',
    'ADDRESS LOGO LONGSLEEVE in WHITE',
    'address-logo-longsleeve-in-white',
    '- Белоснежный хлопковый лонгслив' || CHR(10) || '- Контрастный логотип на спинке',
    4650.00, 'RUB', 'ACTIVE',
    '019fc26c-75f1-74b4-ba38-2cd59ca5e5a4', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/858885/_____1.png',
    NOW(), NOW(), NOW()
),

-- --- ФУТБОЛКИ ---
(
    'e1000000-0000-0000-0000-000000000019',
    'FMM CRYSTALS T-SHIRT in BLACK',
    'fmm-crystals-t-shirt-in-black',
    '- Футболка с принтом инкрустированным стразами' || CHR(10) || '- 100% гребной хлопок',
    3520.00, 'RUB', 'ACTIVE',
    '019fc26c-4b9f-71e8-94cb-387a6d62488e', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/859166/_________.png',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000020',
    'FMM CRYSTALS T-SHIRT in GREY',
    'fmm-crystals-t-shirt-in-grey',
    '- Серый меланж футболки с мерцающими кристаллами',
    3520.00, 'RUB', 'ACTIVE',
    '019fc26c-4b9f-71e8-94cb-387a6d62488e', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/859191/_________.png',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000021',
    'FMM CRYSTALS T-SHIRT in WHITE',
    'fmm-crystals-t-shirt-in-white',
    '- Белая футболка премиум плотности со стразами',
    3520.00, 'RUB', 'ACTIVE',
    '019fc26c-4b9f-71e8-94cb-387a6d62488e', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/859178/_________.png',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000022',
    'DEVIL OG LOGO T-SHIRT in BLACK',
    'devil-og-logo-t-shirt-in-black',
    '- Принт Devil OG Logo' || CHR(10) || '- Оверсайз крой с приспущенным плечом',
    3720.00, 'RUB', 'ACTIVE',
    '019fc26c-4b9f-71e8-94cb-387a6d62488e', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/859193/mm_______1.png',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000023',
    'PANTHERA OG LOGO T-SHIRT in GREY',
    'panthera-og-logo-t-shirt-in-grey',
    '- Серая футболка с принтом дикой пантеры',
    3720.00, 'RUB', 'ACTIVE',
    '019fc26c-4b9f-71e8-94cb-387a6d62488e', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/859198/mm_______2.png',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000024',
    'RHINESTONES OG LOGO TEE in WHITE',
    'rhinestones-og-logo-tee-in-white',
    '- Оверсайз белая футболка с фирменными стразами',
    4500.00, 'RUB', 'ACTIVE',
    '019fc26c-4b9f-71e8-94cb-387a6d62488e', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/859001/______.png',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000025',
    'ADDRESS LOGO T-SHIRT in BLACK',
    'address-logo-t-shirt-in-black',
    '- Базовая чёрная футболка с вышивкой Address Logo',
    3540.00, 'RUB', 'ACTIVE',
    '019fc26c-4b9f-71e8-94cb-387a6d62488e', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/844857/t_b1.png',
    NOW(), NOW(), NOW()
),

-- --- МАЙКИ И ШОРТЫ ---
(
    'e1000000-0000-0000-0000-000000000026',
    'ADDRESS LOGO TANK TOP in GREEN CAMO',
    'address-logo-tank-top-in-green-camo',
    '- Камуфляжная майка-борцовка зеленого оттенка',
    3120.00, 'RUB', 'ACTIVE',
    '019fc26c-4b9f-71e8-94cb-387a6d62488e', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/859143/_________________________.png',
    NOW(), NOW(), NOW()
),
(
    'e1000000-0000-0000-0000-000000000027',
    'ADDRESS LOGO SHORTS in BLACK',
    'address-logo-shorts-in-black',
    '- Хлопковые шорты на резинке с глубокими карманами',
    4320.00, 'RUB', 'ACTIVE',
    '019fc26c-a07e-7344-9605-54febf0df57b', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/847774/___b1___________.png',
    NOW(), NOW(), NOW()
),

-- --- АКСЕССУАРЫ ---
(
    'e1000000-0000-0000-0000-000000000028',
    'ADDRESS LOGO IPHONE CASE in BLACK',
    'address-logo-iphone-case-in-black',
    '- Защитный силиконовый чехол с покрытием soft-touch',
    2500.00, 'RUB', 'ACTIVE',
    '019fc26c-109a-74c6-b8e5-4a252ecf4e12', '09021c8e-a988-4a45-bf06-fed27e0dcfeb',
    'https://aws.kiiiosk.store/uploads/shop/11204/uploads/product_image/image/844845/___b1.png',
    NOW(), NOW(), NOW()
)
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    price = EXCLUDED.price,
    cover_image = EXCLUDED.cover_image,
    status = EXCLUDED.status;

-- 4. INSERT PRODUCT VARIANTS (FOR CLOTHING: S, M, L, XL)
INSERT INTO product_variants (id, product_id, sku, size, color, is_active, sort_order, created_at)
SELECT
    gen_random_uuid(),
    p.id,
    UPPER(p.slug) || '-' || s.size,
    s.size,
    'Standard',
    true,
    s.sort,
    NOW()
FROM products p
CROSS JOIN (
    VALUES ('S', 0), ('M', 1), ('L', 2), ('XL', 3)
) AS s(size, sort)
WHERE p.category_id != '09021c8e-a988-4a45-bf06-fed27e0dcfe1' -- НЕ обувь
ON CONFLICT (sku) DO NOTHING;

-- 5. INSERT PRODUCT VARIANTS (FOR SHOES: 40, 41, 42, 43, 44)
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
    VALUES ('40', 0), ('41', 1), ('42', 2), ('43', 3), ('44', 4)
) AS s(size, sort)
WHERE p.category_id = '09021c8e-a988-4a45-bf06-fed27e0dcfe1' -- Обувь
ON CONFLICT (sku) DO NOTHING;

COMMIT;
