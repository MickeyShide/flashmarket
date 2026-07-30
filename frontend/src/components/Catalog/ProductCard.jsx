import React from 'react';
import { formatPrice } from '../../utils/formatters';

export const ProductCard = ({ product, onClick }) => {
  const coverStyle = product.cover_image
    ? { background: `url(${product.cover_image}) center/cover no-repeat #000` }
    : {};

  const brandTag = product.brand_name
    ? product.brand_name.toUpperCase()
    : (product.category_name ? product.category_name.toUpperCase() : 'FLASH MARKET');

  const catSubTag = product.category_name ? product.category_name.toUpperCase() : '';

  return (
    <div
      className="flex flex-col items-center text-center cursor-pointer relative group"
      onClick={onClick}
    >
      {/* Black Thumbnail Box */}
      <div
        className="w-full aspect-[3/4] max-h-[320px] bg-black rounded flex flex-col items-center justify-center relative mb-3 overflow-hidden"
        style={coverStyle}
      >
        {/* Status Badge */}
        <div className="absolute top-[10px] left-[8px] right-[8px] flex justify-center z-10 pointer-events-none">
          <span className="bg-[#333333] text-white text-[8.5px] font-extrabold tracking-wider uppercase px-2 py-0.5 rounded">
            {product.status}
          </span>
        </div>

        {/* Fallback Icon */}
        {!product.cover_image && (
          <svg className="w-9 md:w-12 h-9 md:h-12 stroke-white stroke-[1.2] fill-none opacity-90 mb-1.5" viewBox="0 0 24 24">
            <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
          </svg>
        )}

        {/* Brand Tag Overlay */}
        <span className="absolute bottom-[10px] font-mono text-[8.5px] tracking-[1.5px] text-[#666666] uppercase">
          {brandTag}
        </span>
      </div>

      {/* Brand Subtitle */}
      <div className="font-mono text-[9px] tracking-[1.5px] text-text-muted uppercase mb-0.5">
        {brandTag}{catSubTag ? ' · ' + catSubTag : ''}
      </div>

      {/* Product Title */}
      <div className="text-[11.5px] font-extrabold tracking-wide uppercase text-text-main mb-1 leading-snug group-hover:text-accent-red transition-colors">
        {product.name}
      </div>

      {/* Price */}
      <div className="text-[12.5px] font-bold text-black flex items-center gap-1.5">
        {formatPrice(product.price, product.currency, false)}
      </div>
    </div>
  );
};
