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
    const createdOrders = [];

    try {
      for (const item of cart) {
        const tempOrderId = crypto.randomUUID();

        // 1. Reserve stock
        let reserveRes;
        try {
          reserveRes = await apiJson(`/api/v1/stocks/${item.id}/reserve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: user.id,
              quantity: item.qty,
              order_id: tempOrderId
            })
          });
          successfulReservations.push({ productId: item.id, orderId: tempOrderId, reservation: reserveRes.reservation });
        } catch (err) {
          throw new Error(`Ошибка резервирования "${item.name}": ${err.message}`);
        }

        // 2. Create Order (price in kopecks)
        const priceKopecks = Math.round(item.price * 100);
        try {
          const order = await apiJson('/api/v1/orders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: user.id,
              product_id: item.id,
              product_name: item.name,
              price: priceKopecks,
              currency: item.currency || 'RUB',
              quantity: item.qty,
              reservation_id: reserveRes.reservation.id
            })
          });
          createdOrders.push(order);
        } catch (err) {
          throw new Error(`Ошибка создания заказа для "${item.name}": ${err.message}`);
        }
      }

      // Success! Clear cart
      clearCart();
      triggerToast(`Заказ успешно оформлен! Номер заказа: ${createdOrders[0]?.id || ''}`);
      onCheckoutSuccess();

    } catch (err) {
      // ROLLBACK: Release all reservations
      setErrorMsg(`${err.message}. Выполняем откат резервов...`);

      for (const resItem of successfulReservations) {
        try {
          await apiJson(`/api/v1/stocks/${resItem.productId}/release`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order_id: resItem.orderId })
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
        <div className="bg-gray-50 border border-border-color rounded-md p-4 text-xs space-y-2">
          <div className="font-extrabold uppercase tracking-wider mb-2 text-[11px] text-gray-500">
            Содержимое заказа:
          </div>
          {cart.map((item, idx) => (
            <div key={idx} className="flex justify-between font-medium">
              <span>{item.name} × {item.qty} ({item.size})</span>
              <span className="font-bold">{formatPrice(item.price * item.qty, item.currency, false)}</span>
            </div>
          ))}
          <div className="border-t border-border-color pt-2 flex justify-between font-black text-sm uppercase">
            <span>ИТОГО:</span>
            <span>{formatPrice(cartTotal(), 'RUB', false)}</span>
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
            {submitting ? 'ОБРАБОТКА И РЕЗЕРВИРОВАНИЕ...' : 'ПОДТВЕРДИТЬ ЗАКАЗ'}
          </button>
        </form>
      </div>
    </div>
  );
};
