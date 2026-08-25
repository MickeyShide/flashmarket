import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiJson } from '../services/api';
import { useAuth } from './AuthContext';
import { useToast } from './ToastContext';

const WishlistContext = createContext(null);

export const WishlistProvider = ({ children }) => {
  const { user } = useAuth();
  const { triggerToast } = useToast();
  const [wishedProductIds, setWishedProductIds] = useState(new Set());
  const [loadingWishlist, setLoadingWishlist] = useState(false);

  const loadWishlist = useCallback(async () => {
    if (!user) {
      setWishedProductIds(new Set());
      return;
    }
    setLoadingWishlist(true);
    try {
      const data = await apiJson(`/api/v1/wishlist/users/${user.id}/items?limit=100`);
      let items = Array.isArray(data) ? data : (data.items || []);
      if (data.total > items.length) {
        const next = await apiJson(`/api/v1/wishlist/users/${user.id}/items?limit=100&offset=100`);
        items = [...items, ...(next.items || [])];
      }
      const ids = new Set(items.map(item => item.product_id || item.id));
      setWishedProductIds(ids);
    } catch (err) {
      console.warn('Failed to load wishlist:', err);
    } finally {
      setLoadingWishlist(false);
    }
  }, [user]);

  useEffect(() => {
    loadWishlist();
  }, [loadWishlist]);

  const isWished = (productId) => {
    return wishedProductIds.has(productId);
  };

  const addToWishlist = async (productId) => {
    if (!user) {
      triggerToast('Войдите, чтобы добавить товар в избранное', true);
      window.dispatchEvent(new CustomEvent('flashmarket:auth-required', { detail: { tab: 'wishlist' } }));
      return false;
    }

    // Optimistic UI update: instantly mark as wished
    const previous = new Set(wishedProductIds);
    setWishedProductIds(prev => new Set([...prev, productId]));
    triggerToast('Товар добавлен в избранное');

    try {
      await apiJson(`/api/v1/wishlist/users/${user.id}/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId })
      });
      return true;
    } catch (err) {
      // Rollback on failure
      setWishedProductIds(previous);
      triggerToast(err.message || 'Не удалось добавить в избранное', true);
      return false;
    }
  };

  const removeFromWishlist = async (productId) => {
    if (!user) return false;

    // Optimistic UI update: instantly unmark
    const previous = new Set(wishedProductIds);
    setWishedProductIds(prev => {
      const next = new Set(prev);
      next.delete(productId);
      return next;
    });
    triggerToast('Товар удален из избранного');

    try {
      await apiJson(`/api/v1/wishlist/users/${user.id}/items/${productId}`, {
        method: 'DELETE'
      });
      return true;
    } catch (err) {
      // Rollback on failure
      setWishedProductIds(previous);
      triggerToast(err.message || 'Не удалось удалить из избранного', true);
      return false;
    }
  };

  const toggleWishlist = async (productId) => {
    if (isWished(productId)) {
      return await removeFromWishlist(productId);
    } else {
      return await addToWishlist(productId);
    }
  };

  const clearWishlist = () => {
    setWishedProductIds(new Set());
  };

  return (
    <WishlistContext.Provider value={{
      wishedProductIds,
      loadingWishlist,
      isWished,
      addToWishlist,
      removeFromWishlist,
      toggleWishlist,
      clearWishlist,
      loadWishlist
    }}>
      {children}
    </WishlistContext.Provider>
  );
};

export const useWishlist = () => {
  const context = useContext(WishlistContext);
  if (!context) throw new Error('useWishlist must be used within WishlistProvider');
  return context;
};
