-- ==============================================================================
-- FLASHMARKET: CLEANUP CATALOG DATABASE SCRIPT
-- Cleans all data related to products, variants, images, categories, and brands
-- ВАЖНО: Выполнять в базе данных "catalog"!
-- ==============================================================================

-- 0. Сброс зависших транзакций в DBeaver
ROLLBACK;

-- 1. Полная быстрая очистка таблиц со сбросом связей (CASCADE)
TRUNCATE TABLE product_variants, product_images, products, categories, brands CASCADE;

-- (Альтернативный вариант удаления через DELETE на случай отсутствия прав TRUNCATE):
-- DELETE FROM product_variants;
-- DELETE FROM product_images;
-- DELETE FROM products;
-- DELETE FROM categories;
-- DELETE FROM brands;
