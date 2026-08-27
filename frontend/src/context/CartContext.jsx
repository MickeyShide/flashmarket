import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { CART_KEY } from '../config/constants';
import { apiJson } from '../services/api';
import { useAuth } from './AuthContext';
import { useToast } from './ToastContext';

const CartContext = createContext(null);

export const CartProvider = ({ children }) => {
  const { user } = useAuth();
  const { triggerToast } = useToast();
  const [stockCache, setStockCache] = useState({});

  const storageKey = user?.id ? `${CART_KEY}_${user.id}` : `${CART_KEY}_guest`;

  const [cart, setCart] = useState(() => {
    try {
      const raw = localStorage.getItem(storageKey) || localStorage.getItem(CART_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      console.warn('Corrupt cart in localStorage, resetting cart');
      return [];
    }
  });

  // Switch cart when user logs in or out
  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      const parsed = raw ? JSON.parse(raw) : [];
      setCart(Array.isArray(parsed) ? parsed : []);
    } catch (e) {
      setCart([]);
    }
  }, [storageKey]);

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(cart));
    } catch (e) {
      console.error('saveCart error', e);
    }
  }, [cart, storageKey]);

  const fetchStock = useCallback(async (productId, variantId = null) => {
    try {
      const cacheKey = variantId ? `${productId}_${variantId}` : productId;
      const url = variantId
        ? `/api/v1/stocks/${productId}?variant_id=${variantId}`
        : `/api/v1/stocks/${productId}`;
      const stock = await apiJson(url, { skipCache: true });
      setStockCache(prev => ({ ...prev, [cacheKey]: stock }));
      return stock;
    } catch (err) {
      const fallback = { total: 0, available: 0, reserved: 0, sold: 0 };
      const cacheKey = variantId ? `${productId}_${variantId}` : productId;
      setStockCache(prev => ({ ...prev, [cacheKey]: fallback }));
      return fallback;
    }
  }, []);

  const addToCart = async (product, selectedVariant = null, dropInfo = null, requestedQty = 1) => {
    if (!product) return;

    const variantId = selectedVariant?.id || null;

    try {
      const stock = await fetchStock(product.id, variantId);
      const available = stock.available || 0;

      const dropId = dropInfo?.id || dropInfo?.drop_id || null;
      const maxPerUser = dropInfo?.max_per_user ? Number(dropInfo.max_per_user) : null;

      const existingIndex = cart.findIndex(i =>
        i.id === product.id &&
        (i.variant_id || null) === variantId &&
        (i.drop_id || null) === dropId
      );
      const currentCartQty = existingIndex > -1 ? cart[existingIndex].qty : 0;

      if (maxPerUser && currentCartQty + requestedQty > maxPerUser) {
        triggerToast(`Превышен лимит на пользователя для этого дропа (макс. ${maxPerUser} шт.)`, true);
        return;
      }

      if (currentCartQty + requestedQty > available) {
        triggerToast(`Недостаточно товара на складе (доступно: ${available} шт.)`, true);
        return;
      }

      const priceToUse = selectedVariant?.effective_price !== undefined && selectedVariant?.effective_price !== null
        ? Number(selectedVariant.effective_price)
        : Number(product.price);

      setCart(prevCart => {
        const idx = prevCart.findIndex(i =>
          i.id === product.id &&
          (i.variant_id || null) === variantId &&
          (i.drop_id || null) === dropId
        );

        if (idx > -1) {
          const updated = [...prevCart];
          updated[idx] = { ...updated[idx], qty: updated[idx].qty + requestedQty };
          return updated;
        } else {
          return [...prevCart, {
            id: product.id,
            slug: product.slug,
            name: product.name,
            price: priceToUse,
            currency: product.currency || 'RUB',
            size: selectedVariant?.size || selectedVariant?.attributes?.size || 'OS',
            color: selectedVariant?.color || selectedVariant?.attributes?.color || null,
            variant_id: variantId,
            variant_sku: selectedVariant?.sku || null,
            variant_size: selectedVariant?.size || null,
            variant_color: selectedVariant?.color || null,
            drop_id: dropId,
            drop_slug: dropInfo?.slug || dropInfo?.drop_slug || null,
            qty: requestedQty
          }];
        }
      });

      triggerToast('Товар успешно добавлен в корзину!');
    } catch (err) {
      triggerToast('Не удалось проверить наличие товара', true);
    }
  };

  // Legacy helper signature for backward compatibility
  const addToCartCurrent = async (product, size = 'OS') => {
    return addToCart(product, { size }, null, 1);
  };

  const removeCartItem = (index) => {
    setCart(prev => prev.filter((_, i) => i !== index));
  };

  const changeQty = async (index, delta) => {
    const item = cart[index];
    if (!item) return;

    // Optimistic UI update: instantly apply delta
    setCart(prev => {
      if (!prev[index]) return prev;
      const updated = [...prev];
      const newQty = updated[index].qty + delta;
      if (newQty <= 0) {
        return updated.filter((_, i) => i !== index);
      } else {
        updated[index] = { ...updated[index], qty: newQty };
        return updated;
      }
    });

    // If increasing quantity, verify with fresh stock from backend
    if (delta > 0) {
      try {
        const stock = await fetchStock(item.id, item.variant_id);
        const available = stock.available ?? 0;

        if (item.qty + delta > available) {
          triggerToast(`Достигнут лимит наличия на складе (${available} шт.)`, true);
          setCart(prev => {
            const currentItemIdx = prev.findIndex(i =>
              i.id === item.id &&
              (i.variant_id || null) === (item.variant_id || null) &&
              (i.drop_id || null) === (item.drop_id || null)
            );
            if (currentItemIdx === -1) return prev;
            const updated = [...prev];
            updated[currentItemIdx] = {
              ...updated[currentItemIdx],
              qty: Math.min(updated[currentItemIdx].qty, available)
            };
            return updated;
          });
        }
      } catch (e) {
        // Handled silently
      }
    }
  };

  const clearCart = () => {
    setCart([]);
    setStockCache({});
    try {
      localStorage.removeItem(storageKey);
    } catch (e) { }
  };

  const cartTotal = () => {
    return cart.reduce((sum, item) => sum + item.price * item.qty, 0);
  };

  const getCartCount = () => {
    return cart.reduce((sum, item) => sum + item.qty, 0);
  };

  return (
    <CartContext.Provider value={{
      cart,
      stockCache,
      addToCart,
      addToCartCurrent,
      removeCartItem,
      changeQty,
      clearCart,
      cartTotal,
      getCartCount,
      fetchStock
    }}>
      {children}
    </CartContext.Provider>
  );
};

export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) throw new Error('useCart must be used within CartProvider');
  return context;
};
