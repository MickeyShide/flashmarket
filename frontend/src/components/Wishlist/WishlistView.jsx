import React, { useState, useEffect } from 'react';
import { apiJson } from '../../services/api';
import { ProductCard } from '../Catalog/ProductCard';
import { ProductGridSkeleton } from '../Catalog/ProductGridSkeleton';
import { useWishlist } from '../../context/WishlistContext';
import { useToast } from '../../context/ToastContext';

export const WishlistView = ({ onOpenProduct, onGoToCatalog }) => {
  const { wishedProductIds, loadWishlist } = useWishlist();
  const { triggerToast } = useToast();

  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function hydrateWishlist() {
      setLoading(true);
      setError(null);

      try {
        const ids = Array.from(wishedProductIds);
        if (ids.length === 0) {
          setProducts([]);
          setLoading(false);
          return;
        }

        // Hydrate product IDs in chunks through Catalog batch endpoint
        const chunkSize = 50;
        let allHydrated = [];
        for (let i = 0; i < ids.length; i += chunkSize) {
          const chunk = ids.slice(i, i + chunkSize);
          const chunkRes = await apiJson('/api/v1/products/batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_ids: chunk })
          });
          const list = Array.isArray(chunkRes) ? chunkRes : (chunkRes.items || []);
          allHydrated = [...allHydrated, ...list];
        }

        if (isMounted) {
          setProducts(allHydrated);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      }
    }

    hydrateWishlist();
  }, [wishedProductIds]);

  if (loading) {
    return (
      <div className="my-4">
        <ProductGridSkeleton count={4} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 p-6 rounded-lg text-center my-4">
        <div className="font-bold text-sm mb-2">Не удалось загрузить список избранного</div>
        <div className="text-xs">{error}</div>
        <button
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded text-xs font-bold hover:bg-red-700"
          onClick={loadWishlist}
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="bg-white border border-border-color rounded-lg p-10 text-center my-4">
        <svg className="w-12 h-12 stroke-gray-400 fill-none mx-auto mb-3 stroke-1" viewBox="0 0 24 24">
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
        </svg>
        <p className="text-base font-extrabold uppercase mb-2">В избранном пока ничего нет</p>
        <p className="text-xs text-gray-500 mb-6">Добавляйте понравившиеся товары, нажимая на иконку сердечка</p>
        <button
          className="bg-black text-white py-3 px-6 text-xs font-black tracking-wider uppercase rounded hover:bg-gray-800"
          onClick={onGoToCatalog}
        >
          Перейти в каталог
        </button>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 md:gap-6 my-4">
      {products.map(product => (
        <ProductCard
          key={product.id}
          product={product}
          onClick={() => onOpenProduct(product.slug || product.id)}
        />
      ))}
    </div>
  );
};
