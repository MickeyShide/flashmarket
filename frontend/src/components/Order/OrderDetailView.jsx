import React, { useState, useEffect } from 'react';
import { useToast } from '../../context/ToastContext';
import { apiJson } from '../../services/api';
import { formatDate, formatPrice, getOrderStatusClass, getOrderStatusLabel } from '../../utils/formatters';

export const OrderDetailView = ({ orderId, onBack }) => {
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

  const handlePayOrder = async (orderId, payableAmountKopecks, currency) => {
    if (!window.confirm(`Подтвердите оплату на сумму ${formatPrice(payableAmountKopecks, currency, true)}`)) return;

    setPaying(true);
    try {
      let checkout = null;
      for (let attempt = 0; attempt < 5; attempt += 1) {
        try {
          checkout = await apiJson(`/api/v1/payments/orders/${orderId}/checkout`, {
            method: 'POST'
          });
          break;
        } catch (err) {
          if (err.data?.error?.code !== 'payment_not_ready' || attempt === 4) {
            throw err;
          }
          await new Promise(resolve => window.setTimeout(resolve, 300 * (attempt + 1)));
        }
      }
      if (!checkout?.confirmation_url) {
        throw new Error('Платёжная ссылка не получена');
      }
      window.sessionStorage.setItem('flashmarket:lastPaymentOrderId', orderId);
      window.location.assign(checkout.confirmation_url);
    } catch (err) {
      triggerToast('Ошибка оплаты: ' + err.message, true);
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

  const origPriceKopecks = order.original_price ?? (order.price * order.quantity);
  const discountKopecks = order.discount_amount ?? 0;
  const finalPriceKopecks = order.final_price ?? Math.max(0, origPriceKopecks - discountKopecks);
  const paymentExpired = Boolean(
    order.payment_expires_at && new Date(order.payment_expires_at).getTime() <= Date.now()
  );

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
            {(order.variant_sku || order.variant_size || order.variant_color) && (
              <div className="text-[11px] text-gray-500 font-mono mt-0.5">
                {order.variant_sku && <span>SKU: {order.variant_sku} · </span>}
                {order.variant_size && <span>Размер: {order.variant_size} </span>}
                {order.variant_color && <span>· Цвет: {order.variant_color}</span>}
              </div>
            )}
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
            <div className="text-[9.5px] font-extrabold uppercase text-text-muted mb-1">Исходная сумма</div>
            <div className="text-xs font-bold">{formatPrice(origPriceKopecks, order.currency, true)}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded border border-border-color">
            <div className="text-[9.5px] font-extrabold uppercase text-text-muted mb-1">Скидка</div>
            <div className="text-xs font-bold text-emerald-600">−{formatPrice(discountKopecks, order.currency, true)}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded border border-border-color">
            <div className="text-[9.5px] font-extrabold uppercase text-text-muted mb-1">К оплате</div>
            <div className="text-xs font-black text-black">{formatPrice(finalPriceKopecks, order.currency, true)}</div>
          </div>
        </div>

        {/* Dates & Payment Deadline */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-gray-50 p-3 rounded border border-border-color">
            <div className="text-[9.5px] font-extrabold uppercase text-text-muted mb-1">Дата создания</div>
            <div className="text-xs font-bold">{formatDate(order.created_at)}</div>
          </div>
          {order.payment_expires_at && (
            <div className="bg-amber-50 p-3 rounded border border-amber-200 text-amber-900">
              <div className="text-[9.5px] font-extrabold uppercase mb-1">Срок оплаты до</div>
              <div className="text-xs font-black font-mono">{formatDate(order.payment_expires_at)}</div>
            </div>
          )}
        </div>

        {/* IDs */}
        <div className="space-y-2">
          <div className="bg-gray-50 p-3 rounded border border-border-color">
            <div className="text-[9.5px] font-extrabold uppercase text-text-muted mb-1">ID заказа</div>
            <code className="text-[10.5px] font-mono text-gray-800 break-all">{order.id}</code>
          </div>
          {order.reservation_id && (
            <div className="bg-gray-50 p-3 rounded border border-border-color">
              <div className="text-[9.5px] font-extrabold uppercase text-text-muted mb-1">ID резервирования</div>
              <code className="text-[10.5px] font-mono text-gray-800 break-all">{order.reservation_id}</code>
            </div>
          )}
          {order.promocode_id && (
            <div className="bg-gray-50 p-3 rounded border border-border-color">
              <div className="text-[9.5px] font-extrabold uppercase text-text-muted mb-1">Промокод</div>
              <code className="text-[10.5px] font-mono text-gray-800 break-all">{order.promocode_id}</code>
            </div>
          )}
        </div>

        {/* Payment Section */}
        {order.status === 'AWAITING_PAYMENT' ? (
          <div className="border-t border-border-color pt-4">
            <h3 className="text-xs font-extrabold uppercase mb-3">Оплата заказа</h3>
            <button
              className="w-full sm:max-w-[320px] bg-black text-white py-3.5 px-6 text-xs font-black tracking-wider uppercase rounded hover:bg-gray-800 disabled:opacity-50 transition-colors"
              disabled={paying || paymentExpired}
              onClick={() => handlePayOrder(order.id, finalPriceKopecks, order.currency)}
            >
              {paymentExpired
                ? 'СРОК ОПЛАТЫ ИСТЕК'
                : paying
                  ? 'ОБРАБОТКА ОПЛАТЫ...'
                  : `ОПЛАТИТЬ ${formatPrice(finalPriceKopecks, order.currency, true)}`}
            </button>
          </div>
        ) : order.payment_id ? (
          <div className="border-t border-border-color pt-4">
            <h3 className="text-xs font-extrabold uppercase mb-3">Информация об оплате</h3>
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
