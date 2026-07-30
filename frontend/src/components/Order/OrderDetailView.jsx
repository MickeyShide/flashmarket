import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { apiJson } from '../../services/api';
import { formatDate, formatPrice, getOrderStatusClass, getOrderStatusLabel } from '../../utils/formatters';

export const OrderDetailView = ({ orderId, onBack }) => {
  const { user, loadNotifications } = useAuth();
  const { triggerToast } = useToast();

  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [paying, setPaying] = useState(false);

  const fetchOrderDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiJson('/api/v1/orders/' + orderId);
      setOrder(data);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    if (orderId) {
      fetchOrderDetails();
    }
  }, [orderId]);

  const handlePayOrder = async (orderId, amountKopecks, currency) => {
    if (!window.confirm(`Подтвердите оплату на сумму ${formatPrice(amountKopecks, currency, true)}`)) return;

    setPaying(true);
    try {
      // 1. Create payment
      const payment = await apiJson('/api/v1/payments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_id: orderId,
          user_id: user.id,
          amount: amountKopecks,
          currency: currency || 'RUB',
          provider: 'mock'
        })
      });

      // 2. Confirm payment via mock provider
      await apiJson(`/api/v1/payments/${payment.id}/confirm`, {
        method: 'POST'
      });

      // 3. Confirm order
      try {
        await apiJson(`/api/v1/orders/${orderId}/confirm?payment_id=${payment.id}`, {
          method: 'POST'
        });
      } catch (e) {
        console.warn('Order confirm endpoint error:', e);
      }

      triggerToast('Оплата прошла успешно!');
      loadNotifications();
      fetchOrderDetails();

    } catch (err) {
      triggerToast('Ошибка оплаты: ' + err.message, true);
    } finally {
      setPaying(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-[800px] mx-auto my-8 px-4">
        <button className="text-[11px] font-bold uppercase mb-6 cursor-pointer text-text-muted hover:text-black" onClick={onBack}>
          ← Назад к заказам
        </button>
        <div className="spinner"></div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="max-w-[800px] mx-auto my-8 px-4">
        <button className="text-[11px] font-bold uppercase mb-6 cursor-pointer text-text-muted hover:text-black" onClick={onBack}>
          ← Назад к заказам
        </button>
        <div className="bg-red-50 border border-red-200 text-red-700 p-6 rounded-lg text-center font-bold text-xs">
          Ошибка загрузки заказа: {error || 'Заказ не найден'}
        </div>
      </div>
    );
  }

  const totalAmountKopecks = order.price * order.quantity;

  return (
    <div className="max-w-[800px] mx-auto my-6 md:my-8 px-3.5 md:px-6">
      <button className="text-[11px] font-bold uppercase mb-6 cursor-pointer text-text-muted hover:text-black" onClick={onBack}>
        ← Назад к заказам
      </button>

      <div className="bg-white border border-border-color rounded-lg p-6 space-y-6">
        {/* Order Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-color pb-4">
          <div>
            <div className="text-[10px] text-text-muted font-black tracking-wider uppercase mb-1">
              ЗАКАЗ
            </div>
            <h2 className="text-lg font-black uppercase">
              {order.product_name}
            </h2>
          </div>
          <span className={`order-status ${getOrderStatusClass(order.status)} text-xs font-black px-3 py-1 rounded uppercase self-start sm:self-center`}>
            {getOrderStatusLabel(order.status)}
          </span>
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-gray-50 p-3 rounded border border-border-color">
            <div className="text-[9.5px] font-extrabold uppercase text-text-muted mb-1">Кол-во</div>
            <div className="text-xs font-bold">{order.quantity}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded border border-border-color">
            <div className="text-[9.5px] font-extrabold uppercase text-text-muted mb-1">Цена (шт.)</div>
            <div className="text-xs font-bold">{formatPrice(order.price, order.currency, true)}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded border border-border-color">
            <div className="text-[9.5px] font-extrabold uppercase text-text-muted mb-1">Сумма</div>
            <div className="text-xs font-bold">{formatPrice(totalAmountKopecks, order.currency, true)}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded border border-border-color">
            <div className="text-[9.5px] font-extrabold uppercase text-text-muted mb-1">Дата создания</div>
            <div className="text-xs font-bold">{formatDate(order.created_at)}</div>
          </div>
        </div>

        {/* IDs */}
        <div className="space-y-2">
          <div className="bg-gray-50 p-3 rounded border border-border-color">
            <div className="text-[9.5px] font-extrabold uppercase text-text-muted mb-1">ID заказа</div>
            <code className="text-[10.5px] font-mono text-gray-800 break-all">{order.id}</code>
          </div>
          <div className="bg-gray-50 p-3 rounded border border-border-color">
            <div className="text-[9.5px] font-extrabold uppercase text-text-muted mb-1">ID резервирования</div>
            <code className="text-[10.5px] font-mono text-gray-800 break-all">{order.reservation_id}</code>
          </div>
        </div>

        {/* Payment Section */}
        {order.status === 'AWAITING_PAYMENT' ? (
          <div className="border-t border-border-color pt-4">
            <h3 className="text-xs font-extrabold uppercase mb-3">Оплата</h3>
            <button
              className="w-full sm:max-w-[320px] bg-black text-white py-3.5 px-6 text-xs font-black tracking-wider uppercase rounded hover:bg-gray-800 disabled:opacity-50 transition-colors"
              disabled={paying}
              onClick={() => handlePayOrder(order.id, totalAmountKopecks, order.currency)}
            >
              {paying ? 'ОБРАБОТКА ОПЛАТЫ...' : `ОПЛАТИТЬ ${formatPrice(totalAmountKopecks, order.currency, true)}`}
            </button>
          </div>
        ) : order.payment_id ? (
          <div className="border-t border-border-color pt-4">
            <h3 className="text-xs font-extrabold uppercase mb-3">Оплата</h3>
            <div className="bg-gray-50 p-3 rounded border border-border-color">
              <div className="text-[9.5px] font-extrabold uppercase text-text-muted mb-1">ID платежа</div>
              <code className="text-[10.5px] font-mono text-gray-800 break-all">{order.payment_id}</code>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};
