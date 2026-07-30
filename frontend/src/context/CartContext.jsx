import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { CART_KEY } from '../config/constants';
import { apiJson } from '../services/api';
import { useToast } from './ToastContext';

const CartContext = createContext(null);

export const CartProvider = ({ children }) => {
  const { triggerToast } = useToast();
  const [stockCache, setStockCache] = useState({});

  const [cart, setCart] = useState(() => {
    try {
      const raw = localStorage.getItem(CART_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      console.warn('Corrupt cart in localStorage, resetting cart');
      localStorage.removeItem(CART_KEY);
      return [];
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(CART_KEY, JSON.stringify(cart));
    } catch (e) {
      console.error('saveCart error', e);
    }
  }, [cart]);

  const fetchStock = useCallback(async (productId) => {
    try {
      const stock = await apiJson('/api/v1/stocks/' + productId);
      setStockCache(prev => ({ ...prev, [productId]: stock }));
      return stock;
    } catch (err) {
      const fallback = { total: 0, available: 0, reserved: 0, sold: 0 };
      setStockCache(prev => ({ ...prev, [productId]: fallback }));
      return fallback;
    }
  }, []);

  const addToCartCurrent = async (product, size = 'OS') => {
    if (!product) return;

    try {
      const stock = await fetchStock(product.id);
      const available = stock.available || 0;

      const existing = cart.find(i => i.id === product.id && i.size === size);
      const currentCartQty = existing ? existing.qty : 0;

      if (currentCartQty + 1 > available) {
        triggerToast('Недостаточно товара на складе', true);
        return;
      }

      setCart(prevCart => {
        const idx = prevCart.findIndex(i => i.id === product.id && i.size === size);
        if (idx > -1) {
          const updated = [...prevCart];
          updated[idx] = { ...updated[idx], qty: updated[idx].qty + 1 };
          return updated;
        } else {
          return [...prevCart, {
            id: product.id,
            slug: product.slug,
            name: product.name,
            price: Number(product.price),
            currency: product.currency,
            size,
            qty: 1
          }];
        }
      });

      triggerToast('Товар успешно добавлен в корзину!');
    } catch (err) {
      triggerToast('Не удалось проверить наличие товара', true);
    }
  };

  const removeCartItem = (index) => {
    setCart(prev => prev.filter((_, i) => i !== index));
  };

  const changeQty = async (index, delta) => {
    const item = cart[index];
    if (!item) return;

    if (delta > 0) {
      try {
        const stock = stockCache[item.id] || await fetchStock(item.id);
        const available = stock.available || 0;

        if (item.qty + delta > available) {
          triggerToast(`Достигнут лимит наличия на складе (${available} шт.)`, true);
          setCart(prev => {
            const updated = [...prev];
            updated[index] = { ...updated[index], qty: Math.min(updated[index].qty, available) };
            return updated;
          });
          return;
        }
      } catch (e) {}
    }

    setCart(prev => {
      const updated = [...prev];
      const newQty = updated[index].qty + delta;
      if (newQty <= 0) {
        return updated.filter((_, i) => i !== index);
      } else {
        updated[index] = { ...updated[index], qty: newQty };
        return updated;
      }
    });
  };

  const clearCart = () => {
    setCart([]);
    setStockCache({});
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
