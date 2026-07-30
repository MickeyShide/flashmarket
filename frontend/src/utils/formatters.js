export function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

export function getCsrfToken() {
  return getCookie('flashmarket_csrf');
}

export function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

export function formatPrice(value, currency = 'RUB', isKopecks = false) {
  let num = Number(value);
  if (isNaN(num)) return '0 ₽';
  if (isKopecks || (Number.isInteger(num) && num > 100000)) {
    num = num / 100;
  }
  const formatted = num.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  const symbol = (currency === 'RUB' || !currency) ? '₽' : currency;
  return `${formatted} ${symbol}`;
}

export function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

export function getOrderStatusClass(status) {
  const map = {
    'PENDING': 'status-pending',
    'AWAITING_PAYMENT': 'status-awaiting',
    'PAID': 'status-paid',
    'CONFIRMED': 'status-confirmed',
    'PAYMENT_FAILED': 'status-failed',
    'CANCELLED': 'status-cancelled'
  };
  return map[status] || 'status-pending';
}

export function getOrderStatusLabel(status) {
  const map = {
    'PENDING': 'Ожидает',
    'AWAITING_PAYMENT': 'Ожидает оплаты',
    'PAID': 'Оплачен',
    'CONFIRMED': 'Подтверждён',
    'PAYMENT_FAILED': 'Ошибка оплаты',
    'CANCELLED': 'Отменён'
  };
  return map[status] || status;
}

export function getNotificationStatusLabel(status) {
  const map = { 'PENDING': 'Новое', 'SENT': 'Прочитано', 'FAILED': 'Ошибка' };
  return map[status] || status;
}

export function flattenCategories(tree, result = []) {
  for (const node of tree) {
    result.push({ id: node.id, name: node.name, slug: node.slug });
    if (node.children && node.children.length > 0) {
      flattenCategories(node.children, result);
    }
  }
  return result;
}
