import React from 'react';
import { flattenCategories } from '../../utils/formatters';

const DEFAULT_CATEGORY_COVERS = {
  'clothes': 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=800&q=80',
  'shoes': 'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=800&q=80',
  'accessories': 'https://images.unsplash.com/photo-1523293182086-7651a899d37f?auto=format&fit=crop&w=800&q=80',
  'hoodies': 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=800&q=80',
  't-shirts': 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=800&q=80'
};

export const CategoriesView = ({ categoriesData, onSelectCategory, activeCategoryId }) => {
  const flatCategories = flattenCategories(categoriesData || []);
  const displayList = (categoriesData && categoriesData.length > 0) ? categoriesData : flatCategories;

  return (
    <div className="max-w-[1280px] mx-auto my-4 md:my-6 px-3.5 md:px-6">
      {displayList.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-dashed border-border-color">
          <p className="text-sm font-bold uppercase text-text-muted">Категории не найдены</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2.5 md:gap-3.5">
          {displayList.map((category) => {
            const isSelected = activeCategoryId === category.id;
            const imgUrl = category.image_url || category.cover_url || DEFAULT_CATEGORY_COVERS[category.slug];
            const coverStyle = imgUrl
              ? { background: `linear-gradient(90deg, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.85) 100%), url('${imgUrl}') center/cover no-repeat` }
              : {};

            return (
              <div
                key={category.id || category.slug}
                className={`group relative bg-[#0A0A0A] rounded-lg px-5 py-4 text-white overflow-hidden cursor-pointer flex items-center justify-between border transition-all duration-200 hover:-translate-y-0.5 hover:border-[#555555] hover:shadow-xl ${
                  isSelected ? 'border-accent-lime ring-2 ring-accent-lime/30' : 'border-[#1F1F1F]'
                }`}
                onClick={() => onSelectCategory(category.id)}
              >
                {/* Background image & gradient overlay */}
                {imgUrl ? (
                  <div className="absolute inset-0 z-0 transition-transform duration-500 group-hover:scale-105" style={coverStyle} />
                ) : (
                  <div className="absolute inset-0 z-0 bg-gradient-to-r from-[#18181B] to-[#0A0A0A] transition-transform duration-500 group-hover:scale-105" />
                )}
                <div className="absolute inset-0 bg-radial-gradient from-white/10 to-transparent pointer-events-none z-10" />

                {/* Category Name */}
                <span className="z-20 relative text-[15px] md:text-[16px] font-black tracking-[1.5px] uppercase leading-none select-none">
                  {category.name}
                </span>

                {/* Arrow icon */}
                <div className="z-20 relative w-7 h-7 rounded-full bg-white/10 flex items-center justify-center shrink-0 ml-3 transition-all duration-200 group-hover:bg-white group-hover:translate-x-0.5">
                  <svg className="w-3.5 h-3.5 stroke-white group-hover:stroke-black stroke-[2.5] fill-none" viewBox="0 0 24 24">
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                    <polyline points="12 5 19 12 12 19"></polyline>
                  </svg>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
