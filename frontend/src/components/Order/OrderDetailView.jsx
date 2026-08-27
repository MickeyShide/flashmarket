import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { apiJson } from '../../services/api';
import { invalidatePrefetch } from '../../services/prefetch';
import {
  abortableDelay,
  isAbortError,
  paymentPollingDelay,
  waitForVisible,
} from '../../services/payment-polling';
import { formatDate, formatPrice, getOrderStatusClass, getOrderStatusLabel } from '../../utils/formatters';
import { OrderDetailSkeleton } from './OrderDetailSkeleton';

export const OrderDetailView = ({ orderId, onBack }) => {
  const { user } = useAuth();
  const { triggerToast } = useToast();

  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [paying, setPaying] = useState(false);
  const [paymentPreparation, setPaymentPreparation] = useState('');
  const paymentAbortRef = useRef(null);

  const fetchOrderDetails = async (isBackground = false) => {
    if (!isBackground) setLoading(true);
    setError(null);
    try {
      const data = await apiJson('/api/v1/orders/' + orderId, { skipCache: true });
      setOrder(data);
      if (!isBackground) setLoading(false);
    } catch (err) {
      setError(err.message);
      if (!isBackground) setLoading(false);
    }
  };

  useEffect(() => {
    if (orderId) {
      fetchOrderDetails();
    }
  }, [orderId]);

  useEffect(() => () => paymentAbortRef.current?.abort(), []);

  const handlePayOrder = async (orderId, payableAmountKopecks, currency) => {
    if (!window.confirm(`Подтвердите оплату на сумму ${formatPrice(payableAmountKopecks, currency, true)}`)) return;

    setPaying(true);
    setPaymentPreparation('Подготавливаем безопасный переход к оплате…');
    paymentAbortRef.current?.abort();
    const controller = new AbortController();
    paymentAbortRef.current = controller;
    try {
      let checkout = null;
      for (let attempt = 0; attempt < 5; attempt += 1) {
        try {
          checkout = await apiJson(`/api/v1/payments/orders/${orderId}/checkout`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ receipt_email: user?.email || null }),
            signal: controller.signal,
          });
          break;
        } catch (err) {
          if (err.data?.error?.code !== 'payment_not_ready' || attempt === 4) {
            throw err;
          }
          await abortableDelay(paymentPollingDelay(attempt), controller.signal);
        }
      }
      invalidatePrefetch(/^\/api\/v1\/orders/);
      window.sessionStorage.setItem('flashmarket:lastPaymentOrderId', orderId);
      if (checkout?.confirmation_url) {
        window.location.assign(checkout.confirmation_url);
        return;
      }
      if (checkout?.preparation_status !== 'pending') {
        throw new Error('Платёжная ссылка не получена');
      }
      setPaymentPreparation('ЮKassa обрабатывает запрос. Это обычно занимает несколько секунд…');
      for (let poll = 0; poll < 12; poll += 1) {
        await waitForVisible(controller.signal);
        const payment = await apiJson(`/api/v1/payments/orders/${orderId}`, {
          signal: controller.signal,
        });
        if (payment.confirmation_url) {
          window.location.assign(payment.confirmation_url);
          return;
        }
        if (['CANCELED', 'EXPIRED', 'FAILED'].includes(payment.current_attempt_status)) {
          throw new Error('Попытка оплаты завершилась. Нажмите «Оплатить» ещё раз.');
        }
        await abortableDelay(
          paymentPollingDelay(poll, checkout.retry_after_seconds),
          controller.signal,
        );
      }
      throw new Error('Подготовка заняла больше времени. Попробуйте снова чуть позже.');
    } catch (err) {
      if (isAbortError(err)) return;
      triggerToast('Ошибка оплаты: ' + err.message, true);
      setPaying(false);
      setPaymentPreparation('');
    }
  };

  if (loading) {
    return <OrderDetailSkeleton onBack={onBack} />;
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
          <div className="flex items-center gap-2 self-start sm:self-center">
            <span className={`order-status ${getOrderStatusClass(order.status)} text-xs font-black px-3 py-1 rounded uppercase`}>
              {getOrderStatusLabel(order.status)}
            </span>
            <button
              className="text-[10px] bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold px-2 py-1 rounded uppercase cursor-pointer"
              onClick={() => fetchOrderDetails(false)}
              title="Обновить статус заказа"
            >
              ↻
            </button>
          </div>
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
            {paying && paymentPreparation ? (
              <p className="mt-3 text-xs font-semibold text-amber-800" role="status">
                {paymentPreparation}
              </p>
            ) : null}
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
