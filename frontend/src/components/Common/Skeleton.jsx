import React from 'react';

/**
 * Base Skeleton component with subtle shimmer animation
 */
export const Skeleton = ({
  className = '',
  variant = 'rectangular', // 'rectangular' | 'circular' | 'text' | 'rounded'
  width,
  height,
  style = {},
  ...props
}) => {
  const baseClasses = 'relative overflow-hidden bg-gray-200 skeleton-shimmer';

  let variantClasses = 'rounded';
  if (variant === 'circular') {
    variantClasses = 'rounded-full';
  } else if (variant === 'text') {
    variantClasses = 'rounded h-3 my-1';
  } else if (variant === 'rounded') {
    variantClasses = 'rounded-lg';
  }

  const inlineStyles = {
    ...(width !== undefined ? { width: typeof width === 'number' ? `${width}px` : width } : {}),
    ...(height !== undefined ? { height: typeof height === 'number' ? `${height}px` : height } : {}),
    ...style,
  };

  return (
    <div
      className={`${baseClasses} ${variantClasses} ${className}`}
      style={inlineStyles}
      aria-hidden="true"
      {...props}
    />
  );
};
