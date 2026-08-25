import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useCart } from '../../context/CartContext';
import { useToast } from '../../context/ToastContext';
import { apiJson } from '../../services/api';
import { formatPrice } from '../../utils/formatters';

export const CheckoutView = ({ onBack, onCheckoutSuccess, onGoToAuth }) => {
  const { user } = useAuth();
  const { cart, cartTotal, clearCart } = useCart();
  const { triggerToast } = useToast();

  const [recipientName, setRecipientName] = useState(() => user?.full_name || '');
  const [address, setAddress] = useState('');
  const [phone, setPhone] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Promocode state
  const [promoCodeInput, setPromoCodeInput] = useState('');
  const [appliedPromo, setAppliedPromo] = useState(null);
  const [loadingPromo, setLoadingPromo] = useState(false);
  const [promoError, setPromoError] = useState('');

  if (!user) {
    return (
      <div className="max-w-[600px] mx-auto my-8 px-4 text-center">
        <button className="text-[11px] font-bold uppercase mb-6 cursor-pointer text-text-muted hover:text-black" onClick={onBack}>
          ← Назад в корзину
        </button>
        <div className="bg-white border border-border-color rounded-lg p-8">
          <p className="text-base font-extrabold uppercase mb-4">Войдите в аккаунт для оформления заказа</p>
          <button
            className="bg-black text-white py-3 px-6 text-xs font-black tracking-wider uppercase rounded hover:bg-gray-800"
            onClick={onGoToAuth}
          >
            Войти / Зарегистрироваться
          </button>
        </div>
      </div>
    );
  }

  const rawTotalRub = cartTotal();
  const rawTotalMinor = Math.round(rawTotalRub * 100);

  const discountMinor = appliedPromo ? Number(appliedPromo.discount_amount || 0) : 0;
  const finalTotalMinor = appliedPromo
    ? Number(appliedPromo.final_amount)
    : rawTotalMinor;
  const finalTotalRub = finalTotalMinor / 100;
  const discountRub = discountMinor / 100;

  // Handle promocode validation
  const handleApplyPromocode = async () => {
    if (!promoCodeInput.trim()) return;
    setLoadingPromo(true);
    setPromoError('');

    try {
      const result = await apiJson('/api/v1/promocodes/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: promoCodeInput.trim().toUpperCase(),
          order_amount: rawTotalMinor,
          user_id: user.id
        })
      });
      if (!result.valid) throw new Error(result.error || 'Недействительный промокод');
      setAppliedPromo({ ...result, code: promoCodeInput.trim().toUpperCase() });
      triggerToast('Промокод успешно применен!');
    } catch (err) {
      setPromoError(err.message || 'Недействительный промокод');
      setAppliedPromo(null);
    } finally {
      setLoadingPromo(false);
    }
  };

  const handleRemovePromocode = () => {
    setAppliedPromo(null);
    setPromoCodeInput('');
    setPromoError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (!recipientName.trim() || recipientName.trim().length < 3) {
      setErrorMsg('Укажите ФИО получателя');
      return;
    }
    if (!address.trim() || address.trim().length < 5) {
      setErrorMsg('Укажите полный адрес доставки');
      return;
    }
    if (!phone.trim() || phone.trim().length < 7) {
      setErrorMsg('Укажите контактный телефон');
      return;
    }

    setSubmitting(true);
    const successfulReservations = [];

    try {
      // 1. Reserve every line
      for (const item of cart) {
        const reserveBody = {
          user_id: user.id,
          quantity: item.qty
        };
        if (item.variant_id) reserveBody.variant_id = item.variant_id;
        if (item.drop_id) reserveBody.drop_id = item.drop_id;

        try {
          const reserveRes = await apiJson(`/api/v1/stocks/${item.id}/reserve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(reserveBody)
          });

          const reservationObj = reserveRes.reservation || reserveRes;
          successfulReservations.push({
            productId: item.id,
            reservationId: reservationObj.id,
            expiresAt: reservationObj.expires_at,
            item
          });
        } catch (err) {
          throw new Error(`Ошибка резервирования "${item.name}": ${err.message}`);
        }
      }

      // 2. Submit Orders Batch
      const linesData = successfulReservations.map(resObj => {
        const item = resObj.item;
        const linePriceMinor = Math.round(item.price * 100);
        const lineData = {
          user_id: user.id,
          product_id: item.id,
          product_name: item.name,
          price: linePriceMinor,
          currency: item.currency || 'RUB',
          quantity: item.qty,
          reservation_id: resObj.reservationId
        };
        if (item.variant_id) lineData.variant_id = item.variant_id;
        if (item.variant_sku) lineData.variant_sku = item.variant_sku;
        if (item.variant_size || item.size) lineData.variant_size = item.variant_size || item.size;
        if (item.variant_color) lineData.variant_color = item.variant_color;
        if (item.drop_id) lineData.drop_id = item.drop_id;
        if (resObj.expiresAt) lineData.payment_expires_at = resObj.expiresAt;
        return lineData;
      });

      const batchPayload = {
        lines: linesData,
        receipt_email: user.email
      };
      if (appliedPromo?.code || promoCodeInput) {
        batchPayload.promocode_code = (appliedPromo?.code || promoCodeInput).toUpperCase();
      }

      const createdOrdersResponse = await apiJson('/api/v1/orders/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(batchPayload)
      });

      // Success! Clear cart
      clearCart();
      const firstOrderId = createdOrdersResponse.orders?.[0]?.id || createdOrdersResponse[0]?.id || '';
      triggerToast(`Заказ успешно оформлен!${firstOrderId ? ' ID: ' + firstOrderId : ''}`);
      onCheckoutSuccess();

    } catch (err) {
      // ROLLBACK: Release all reservations created during this attempt
      setErrorMsg(`${err.message}. Выполняем откат резервов...`);

      for (const resItem of successfulReservations) {
        try {
          await apiJson(`/api/v1/stocks/${resItem.productId}/release`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              reservation_id: resItem.reservationId
            })
          });
        } catch (releaseErr) {
          console.error('Rollback release error:', releaseErr);
        }
      }

      setErrorMsg(`Ошибка при оформлении: ${err.message}. Все зарезервированные позиции были освобождены.`);
      triggerToast('Ошибка оформления заказа', true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-[700px] mx-auto my-6 md:my-8 px-3.5 md:px-6">
      <button className="text-[11px] font-bold uppercase mb-6 cursor-pointer text-text-muted hover:text-black" onClick={onBack}>
        ← Назад в корзину
      </button>

      <h2 className="text-xl md:text-2xl font-black uppercase tracking-wide mb-6">
        ОФОРМЛЕНИЕ ЗАКАЗА
      </h2>

      <div className="bg-white border border-border-color rounded-lg p-6 md:p-8 space-y-6">
        {/* Order Summary */}
        <div className="bg-gray-50 border border-border-color rounded-md p-4 text-xs space-y-3">
          <div className="font-extrabold uppercase tracking-wider mb-2 text-[11px] text-gray-500">
            Содержимое заказа:
          </div>
          {cart.map((item, idx) => (
            <div key={idx} className="flex justify-between font-medium">
              <div>
                <span>{item.name} × {item.qty}</span>
                <span className="text-gray-500 text-[10px] ml-1">({item.variant_size || item.size}{item.variant_color ? `, ${item.variant_color}` : ''})</span>
              </div>
              <span className="font-bold">{formatPrice(item.price * item.qty, item.currency, false)}</span>
            </div>
          ))}

          {/* Promocode Input Box */}
          <div className="pt-3 border-t border-gray-200">
            <label className="block text-[10px] font-extrabold uppercase tracking-wider text-gray-600 mb-1.5">
              Промокод
            </label>
            {appliedPromo ? (
              <div className="flex items-center justify-between bg-emerald-50 border border-emerald-200 p-2.5 rounded">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-black text-emerald-700">✓ {appliedPromo.code || promoCodeInput.toUpperCase()}</span>
                  <span className="text-[10px] text-emerald-600 font-bold">
                    (Скидка: {formatPrice(discountRub, 'RUB', false)})
                  </span>
                </div>
                <button
                  type="button"
                  className="text-xs text-red-600 hover:text-red-800 font-bold underline"
                  onClick={handleRemovePromocode}
                >
                  Удалить
                </button>
              </div>
            ) : (
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Введите промокод (напр. FLASH10)"
                  className="flex-1 border border-gray-300 rounded px-3 py-1.5 text-xs font-mono uppercase outline-none focus:border-black"
                  value={promoCodeInput}
                  onChange={(e) => setPromoCodeInput(e.target.value)}
                />
                <button
                  type="button"
                  disabled={loadingPromo || !promoCodeInput.trim()}
                  className="bg-black text-white px-3 py-1.5 text-xs font-bold uppercase rounded hover:bg-gray-800 disabled:opacity-50"
                  onClick={handleApplyPromocode}
                >
                  {loadingPromo ? '…' : 'Применить'}
                </button>
              </div>
            )}
            {promoError && (
              <div className="text-[10px] font-bold text-red-600 mt-1">{promoError}</div>
            )}
          </div>

          {/* Amount Breakdown */}
          <div className="border-t border-border-color pt-3 space-y-1.5">
            <div className="flex justify-between text-gray-500 font-medium">
              <span>Сумма товаров:</span>
              <span>{formatPrice(rawTotalRub, 'RUB', false)}</span>
            </div>
            {discountRub > 0 && (
              <div className="flex justify-between text-emerald-600 font-extrabold">
                <span>Скидка по промокоду:</span>
                <span>−{formatPrice(discountRub, 'RUB', false)}</span>
              </div>
            )}
            <div className="flex justify-between font-black text-base uppercase pt-1 border-t border-gray-200">
              <span>ИТОГО К ОПЛАТЕ:</span>
              <span>{formatPrice(finalTotalRub, 'RUB', false)}</span>
            </div>
          </div>
        </div>

        {errorMsg && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded text-xs font-bold">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[10.5px] font-extrabold uppercase tracking-wider text-gray-700 mb-1">
              ФИО получателя *
            </label>
            <input
              type="text"
              required
              className="w-full border border-border-color rounded px-3.5 py-2.5 text-xs focus:outline-none focus:border-black font-sans"
              placeholder="Иванов Иван Иванович"
              value={recipientName}
              onChange={(e) => setRecipientName(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-[10.5px] font-extrabold uppercase tracking-wider text-gray-700 mb-1">
              Адрес доставки *
            </label>
            <input
              type="text"
              required
              className="w-full border border-border-color rounded px-3.5 py-2.5 text-xs focus:outline-none focus:border-black font-sans"
              placeholder="г. Москва, ул. Тверская, д. 1, кв. 10"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-[10.5px] font-extrabold uppercase tracking-wider text-gray-700 mb-1">
              Телефон *
            </label>
            <input
              type="tel"
              required
              className="w-full border border-border-color rounded px-3.5 py-2.5 text-xs focus:outline-none focus:border-black font-sans"
              placeholder="+7 (999) 000-00-00"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-black text-white py-4 px-6 text-xs font-black tracking-[1.5px] uppercase cursor-pointer rounded hover:bg-gray-900 disabled:opacity-50 transition-colors mt-4"
          >
            {submitting ? 'ОБРАБОТКА И РЕЗЕРВИРОВАНИЕ...' : `ОПЛАТИТЬ ${formatPrice(finalTotalRub, 'RUB', false)}`}
          </button>
        </form>
      </div>
    </div>
  );
};
