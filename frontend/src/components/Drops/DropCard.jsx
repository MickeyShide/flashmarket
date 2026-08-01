import React from 'react';
import { Countdown } from './Countdown';

export const DropCard = ({ drop, onClick, onRefresh }) => {
  const isScheduled = drop.status === 'SCHEDULED' || (drop.starts_at && new Date(drop.starts_at) > new Date());
  const isActive = drop.status === 'ACTIVE' || (!isScheduled && drop.status !== 'ENDED' && drop.status !== 'CANCELLED');

  const targetDate = isScheduled ? drop.starts_at : (drop.ends_at || null);
  const countdownLabel = isScheduled ? 'До старта:' : 'До окончания:';

  const coverStyle = drop.cover_image
    ? { background: `url(${drop.cover_image}) center/cover no-repeat #000` }
    : {};

  return (
    <div
      className="bg-white border border-border-color rounded-lg overflow-hidden cursor-pointer group hover:border-black transition-all flex flex-col justify-between"
      onClick={onClick}
    >
      <div
        className="w-full h-44 bg-black relative flex flex-col justify-between p-3"
        style={coverStyle}
      >
        <div className="flex items-center justify-between z-10">
          <span className={`text-[9px] font-black tracking-wider uppercase px-2 py-0.5 rounded ${
            isActive ? 'bg-emerald-500 text-white' : 'bg-purple-600 text-white'
          }`}>
            {isActive ? '● АКТИВЕН' : 'АНОНС'}
          </span>

          {drop.max_per_user && (
            <span className="text-[9px] font-bold bg-black/70 text-white px-2 py-0.5 rounded">
              Лимит: {drop.max_per_user} шт./чел
            </span>
          )}
        </div>

        {!drop.cover_image && (
          <div className="my-auto text-center">
            <span className="font-mono text-xs tracking-[2px] text-[#888888] uppercase font-bold">
              LIMITED DROP
            </span>
          </div>
        )}

        <div className="z-10 flex items-center justify-between">
          {targetDate && (
            <div className="flex items-center gap-1">
              <span className="text-[9px] text-gray-300 font-bold uppercase">{countdownLabel}</span>
              <Countdown targetDate={targetDate} onExpire={onRefresh} />
            </div>
          )}
        </div>
      </div>

      <div className="p-4 flex flex-col flex-1 justify-between">
        <div>
          <h3 className="font-black text-sm uppercase tracking-wide group-hover:text-purple-600 transition-colors mb-1">
            {drop.name || drop.title || drop.slug}
          </h3>
          {drop.description && (
            <p className="text-xs text-gray-500 line-clamp-2 mb-3">
              {drop.description}
            </p>
          )}
        </div>

        <div className="pt-2 border-t border-gray-100 flex items-center justify-between text-[10px] text-gray-500 font-mono">
          <span>Товаров: {drop.items_count || drop.product_ids?.length || (drop.items ? drop.items.length : 0)}</span>
          <span className="font-extrabold text-black group-hover:translate-x-1 transition-transform">
            Смотреть дроп →
          </span>
        </div>
      </div>
    </div>
  );
};
