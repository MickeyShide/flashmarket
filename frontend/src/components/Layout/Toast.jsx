import React from 'react';
import { useToast } from '../../context/ToastContext';

export const Toast = () => {
  const { toast } = useToast();

  return (
    <div className={`toast-container ${toast.show ? 'show' : ''} ${toast.isError ? 'toast-error' : ''}`}>
      <svg
        className="w-4 h-4 shrink-0"
        viewBox="0 0 24 24"
        fill="none"
        stroke={toast.isError ? '#FFFFFF' : '#BFF532'}
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
      <span>{toast.msg}</span>
    </div>
  );
};
