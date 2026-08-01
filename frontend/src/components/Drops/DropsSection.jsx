import React, { useState, useEffect, useCallback } from 'react';
import { apiJson } from '../../services/api';
import { DropCard } from './DropCard';

export const DropsSection = ({ onSelectDrop, onViewAllDrops, showAll = false }) => {
  const [drops, setDrops] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchDrops = useCallback(async () => {
    try {
      const [active, upcoming] = await Promise.all([
        apiJson('/api/v1/drops/active'),
        apiJson('/api/v1/drops/upcoming')
      ]);
      setDrops([...(active || []), ...(upcoming || [])]);
    } catch (err) {
      console.warn('Failed to load drops section:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDrops();
  }, [fetchDrops]);

  if (loading || drops.length === 0) return null;

  return (
    <section className="max-w-[1280px] mx-auto my-6 px-3.5 md:px-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-purple-600 animate-pulse"></span>
          <h2 className="text-lg md:text-xl font-black uppercase tracking-wider">
            ЛИМИТИРОВАННЫЕ ДРОПЫ
          </h2>
        </div>

        {onViewAllDrops && (
          <button
            className="text-xs font-black uppercase tracking-wider text-purple-600 hover:text-purple-800 transition-colors cursor-pointer"
            onClick={onViewAllDrops}
          >
            Все дропы ({drops.length}) →
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        {(showAll ? drops : drops.slice(0, 3)).map(drop => (
          <DropCard
            key={drop.id || drop.slug}
            drop={drop}
            onClick={() => onSelectDrop(drop.slug || drop.id)}
            onRefresh={fetchDrops}
          />
        ))}
      </div>
    </section>
  );
};
