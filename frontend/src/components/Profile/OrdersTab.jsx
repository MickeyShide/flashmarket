import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { apiJson } from '../../services/api';
import { formatDate, formatPrice, getOrderStatusClass, getOrderStatusLabel } from '../../utils/formatters';

export const OrdersTab = ({ onSelectOrder }) => {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function loadOrders() {
      if (!user?.id) return;
      setLoading(true);
      setError(null);
      try {
        const data = await apiJson(`/api/v1/orders/users/${user.id}`);
        const items = data.items || [];
        // Sort newest first
        items.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        if (isMounted) {
          setOrders(items);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      }
    }
    loadOrders();
  }, [user?.id]);

  if (loading) return <div className="spinner"></div>;

  if (error) {
    return (
      <div className="text-center p-8 bg-red-50 text-red-600 rounded-lg text-xs font-bold">
        Ошибка загрузки заказов: {error}
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className="text-center py-12 text-text-muted text-xs font-bold uppercase tracking-wider bg-white border border-border-color rounded-lg">
        У вас пока нет заказов
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {orders.map(order => (
        <div
          key={order.id}
          className="p-4 bg-white border border-border-color rounded-lg hover:border-black transition-colors cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3"
          onClick={() => onSelectOrder(order.id)}
        >
          <div>
            <div className="font-extrabold text-[12.5px] uppercase mb-1">
              {order.product_name}
            </div>
            <div className="text-[10.5px] text-gray-500 font-mono">
              ID: {order.id.substring(0, 8)}... · {formatDate(order.created_at)} · Кол-во: {order.quantity} · {formatPrice(order.final_price ?? order.price * order.quantity, order.currency, true)}
            </div>
            {(order.variant_sku || order.variant_size || order.variant_color) && (
              <div className="text-[10px] text-gray-500 font-mono mt-1">
                {[order.variant_sku, order.variant_size, order.variant_color].filter(Boolean).join(' · ')}
              </div>
            )}
          </div>

          <div className="flex items-center gap-3 self-end sm:self-center">
            <span className={`order-status ${getOrderStatusClass(order.status)} text-[10px] font-extrabold px-2.5 py-1 rounded uppercase`}>
              {getOrderStatusLabel(order.status)}
            </span>
            {order.status === 'AWAITING_PAYMENT' && (
              <button
                className="bg-black text-white text-[10px] font-extrabold px-3 py-1.5 rounded uppercase hover:bg-gray-800"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectOrder(order.id);
                }}
              >
                ОПЛАТИТЬ
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
