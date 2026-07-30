import React, { createContext, useContext, useState, useCallback } from 'react';

const ToastContext = createContext(null);

export const ToastProvider = ({ children }) => {
  const [toast, setToast] = useState({ show: false, msg: '', isError: false });
  const [timer, setTimer] = useState(null);

  const triggerToast = useCallback((msg, isError = false) => {
    setToast({ show: true, msg, isError });
    if (timer) clearTimeout(timer);
    const newTimer = setTimeout(() => {
      setToast(t => ({ ...t, show: false }));
    }, 3500);
    setTimer(newTimer);
  }, [timer]);

  return (
    <ToastContext.Provider value={{ toast, triggerToast }}>
      {children}
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastProvider');
  return context;
};
