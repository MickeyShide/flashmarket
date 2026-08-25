import React, { useState, useEffect } from 'react';
import { useCart } from '../../context/CartContext';
import { formatPrice } from '../../utils/formatters';
import { CartSkeleton } from './CartSkeleton';

export const CartView = ({ onBack, onGoToCheckout, onGoToCatalog }) => {
  const { cart, removeCartItem, changeQty, cartTotal, fetchStock, stockCache } = useCart();
  const [stockStatusMap, setStockStatusMap] = useState({});
  const [loadingValidation, setLoadingValidation] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function validateCartStock() {
      if (cart.length === 0) {
        setLoadingValidation(false);
        return;
      }
      setLoadingValidation(true);
      const map = {};
      await Promise.all(cart.map(async (item) => {
        const cacheKey = item.variant_id ? `${item.id}_${item.variant_id}` : item.id;
        let stock = stockCache[cacheKey];
        if (!stock) {
          stock = await fetchStock(item.id, item.variant_id);
        }
        map[cacheKey] = stock;
      }));
      if (isMounted) {
        setStockStatusMap(map);
        setLoadingValidation(false);
      }
    }
    validateCartStock();
  }, [cart, fetchStock, stockCache]);

  if (cart.length === 0) {
    return (
      <div className="max-w-[800px] mx-auto my-8 px-4">
        <button className="text-[11px] font-bold uppercase mb-6 cursor-pointer text-text-muted hover:text-black" onClick={onBack}>
          ← Назад в каталог
        </button>
        <div className="bg-white border border-border-color rounded-lg p-10 text-center">
          <p className="text-base font-extrabold uppercase mb-4">Корзина пуста</p>
          <button
            className="bg-black text-white py-3 px-6 text-xs font-black tracking-wider uppercase rounded hover:bg-gray-800"
            onClick={onGoToCatalog}
          >
            Перейти в каталог
          </button>
        </div>
      </div>
    );
  }

  let hasAnyStockIssue = false;

  return (
    <div className="max-w-[800px] mx-auto my-6 md:my-8 px-3.5 md:px-6">
      <button className="text-[11px] font-bold uppercase mb-6 cursor-pointer text-text-muted hover:text-black" onClick={onBack}>
        ← Назад в каталог
      </button>

      <h2 className="text-xl md:text-2xl font-black uppercase tracking-wide mb-6">
        КОРЗИНА
      </h2>

      {loadingValidation ? (
        <CartSkeleton />
      ) : (
        <div className="space-y-4 mb-8">
          {cart.map((item, idx) => {
            const cacheKey = item.variant_id ? `${item.id}_${item.variant_id}` : item.id;
            const stock = stockStatusMap[cacheKey] || stockCache[cacheKey];
            const avail = stock?.available ?? 0;
            let warning = '';
            let isIssue = false;
            let isOutOfStock = false;

            if (stock) {
              if (avail === 0) {
                warning = 'Нет в наличии на складе!';
                isOutOfStock = true;
                isIssue = true;
                hasAnyStockIssue = true;
              } else if (item.qty > avail) {
                warning = `Внимание: в наличии осталось только ${avail} шт.!`;
                isIssue = true;
                hasAnyStockIssue = true;
              }
            }

            return (
              <div
                key={`${item.id}-${item.variant_id || 'novar'}-${item.size}-${idx}`}
                className={`p-4 border rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-colors ${
                  isOutOfStock ? 'bg-red-50 border-red-200' : isIssue ? 'bg-amber-50 border-amber-200' : 'bg-white border-border-color'
                }`}
              >
                <div className="flex items-center gap-4">
                  {/* Thumbnail Box */}
                  <div className="w-14 h-14 bg-black rounded shrink-0 flex items-center justify-center relative overflow-hidden">
                    <svg className="w-6 h-6 stroke-white fill-none stroke-2" viewBox="0 0 24 24">
                      <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
                    </svg>
                  </div>

                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-extrabold text-[12.5px] uppercase">{item.name}</span>
                      {item.drop_id && (
                        <span className="px-1.5 py-0.5 bg-purple-100 text-purple-700 font-bold text-[9px] uppercase rounded">
                          DROP
                        </span>
                      )}
                    </div>
                    <div className="text-[10.5px] text-gray-500 mt-1 flex flex-wrap items-center gap-2">
                      {item.variant_sku && <span>SKU: {item.variant_sku}</span>}
                      {item.variant_sku && <span>|</span>}
                      <span>Размер: {item.variant_size || item.size}</span>
                      {item.variant_color && (
                        <>
                          <span>|</span>
                          <span>Цвет: {item.variant_color}</span>
                        </>
                      )}
                      <span>|</span>
                      <span>Кол-во:</span>
                      <div className="inline-flex items-center gap-1">
                        <button
                          className="px-1.5 py-0.5 bg-gray-200 rounded text-xs font-bold hover:bg-gray-300"
                          onClick={() => changeQty(idx, -1)}
                        >
                          −
                        </button>
                        <span className="font-bold px-1">{item.qty}</span>
                        <button
                          className="px-1.5 py-0.5 bg-gray-200 rounded text-xs font-bold hover:bg-gray-300"
                          onClick={() => changeQty(idx, 1)}
                        >
                          +
                        </button>
                      </div>
                    </div>
                    {warning && (
                      <div className="text-[10px] font-bold text-red-600 mt-1">{warning}</div>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between sm:justify-end gap-4 shrink-0">
                  <div className="font-extrabold text-[12.5px]">
                    {formatPrice(item.price * item.qty, item.currency, false)}
                  </div>
                  <button
                    className="text-[10px] bg-black text-white border-none rounded px-2.5 py-1.5 font-bold cursor-pointer hover:bg-gray-800"
                    onClick={() => removeCartItem(idx)}
                  >
                    ×
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Total section & Checkout Button */}
      <div className="bg-gray-50 border border-border-color rounded-lg p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <div className="text-[10px] font-extrabold uppercase text-text-muted tracking-wider">Итого к оплате:</div>
          <div className="text-2xl font-black mt-0.5">{formatPrice(cartTotal(), 'RUB', false)}</div>
        </div>

        <button
          className="w-full sm:w-auto bg-black text-white py-4 px-8 text-xs font-black tracking-[1.5px] uppercase cursor-pointer rounded hover:bg-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          disabled={hasAnyStockIssue || loadingValidation}
          onClick={onGoToCheckout}
        >
          {hasAnyStockIssue ? 'ПРЕВЫШЕН ЛИМИТ ОСТАТКОВ' : 'ОФОРМИТЬ ЗАКАЗ'}
        </button>
      </div>
    </div>
  );
};
