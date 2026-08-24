import React, { useEffect, useMemo, useState } from 'react';
import { apiJson } from '../../services/api';

const MAX_POLLS = 15;

export const PaymentReturnView = ({ orderId, onOpenOrder, onGoToOrders }) => {
  const resolvedOrderId = useMemo(
    () => orderId || window.sessionStorage.getItem('flashmarket:lastPaymentOrderId'),
    [orderId]
  );
  const [state, setState] = useState('checking');
  const [message, setMessage] = useState('Проверяем статус платежа…');

  useEffect(() => {
    if (!resolvedOrderId) {
      setState('error');
      setMessage('Не удалось определить заказ. Откройте его из списка заказов.');
      return undefined;
    }

    let cancelled = false;
    let timerId = null;

    const poll = async (attempt = 0) => {
      try {
        const payment = await apiJson(`/api/v1/payments/orders/${resolvedOrderId}`);
        if (cancelled) return;
        if (payment.status === 'SUCCESS') {
          window.sessionStorage.removeItem('flashmarket:lastPaymentOrderId');
          setState('success');
          setMessage('Оплата подтверждена. Заказ оформлен.');
          return;
        }
        if (payment.status === 'REFUNDED') {
          window.sessionStorage.removeItem('flashmarket:lastPaymentOrderId');
          setState('refunded');
          setMessage('Платёж возвращён, потому что заказ уже был отменён.');
          return;
        }
        if (payment.status === 'FAILED' || payment.status === 'CANCELLED') {
          setState('failed');
          setMessage('Платёж не завершён. Деньги не были приняты.');
          return;
        }
      } catch (err) {
        if (cancelled) return;
        if (err.data?.error?.code !== 'payment_not_ready') {
          setState('error');
          setMessage(err.message || 'Не удалось проверить платёж.');
          return;
        }
      }

      if (attempt + 1 >= MAX_POLLS) {
        setState('delayed');
        setMessage('Проверка занимает больше времени. Статус обновится в заказе.');
        return;
      }
      timerId = window.setTimeout(() => poll(attempt + 1), 2000);
    };

    poll();
    return () => {
      cancelled = true;
      if (timerId !== null) window.clearTimeout(timerId);
    };
  }, [resolvedOrderId]);

  const tones = {
    checking: 'border-amber-200 bg-amber-50 text-amber-900',
    delayed: 'border-amber-200 bg-amber-50 text-amber-900',
    success: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    refunded: 'border-blue-200 bg-blue-50 text-blue-900',
    failed: 'border-red-200 bg-red-50 text-red-800',
    error: 'border-red-200 bg-red-50 text-red-800',
  };

  return (
    <div className="w-full max-w-[680px] mx-auto my-10 px-4">
      <div className={`border rounded-lg p-7 ${tones[state]}`}>
        <div className="text-[10px] font-black tracking-[0.18em] uppercase mb-2">
          Результат оплаты
        </div>
        <h1 className="text-xl font-black uppercase mb-3">
          {state === 'success' ? 'Оплата прошла' : state === 'checking' ? 'Проверяем оплату' : 'Статус платежа'}
        </h1>
        <p className="text-sm font-semibold">{message}</p>
        {state === 'checking' && <div className="spinner mt-6" aria-label="Проверка платежа" />}
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mt-5">
        {resolvedOrderId && (
          <button
            className="bg-black text-white py-3 px-5 text-xs font-black uppercase rounded"
            onClick={() => onOpenOrder(resolvedOrderId)}
          >
            Открыть заказ
          </button>
        )}
        <button
          className="border border-border-color bg-white py-3 px-5 text-xs font-black uppercase rounded"
          onClick={onGoToOrders}
        >
          Все заказы
        </button>
      </div>
    </div>
  );
};
