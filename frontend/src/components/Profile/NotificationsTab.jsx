import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { formatDate, getNotificationStatusLabel } from '../../utils/formatters';

export const NotificationsTab = () => {
  const { notifications, markNotifRead } = useAuth();

  if (!notifications || notifications.length === 0) {
    return (
      <div className="text-center py-12 text-text-muted text-xs font-bold uppercase tracking-wider bg-white border border-border-color rounded-lg">
        У вас пока нет уведомлений
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {notifications.map(n => (
        <div
          key={n.id}
          className={`p-4 border rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-colors ${
            n.status === 'PENDING' ? 'bg-[#FFFDE7] border-amber-200' : 'bg-white border-border-color'
          }`}
        >
          <div>
            <div className="font-extrabold text-[12px] uppercase mb-1">{n.subject}</div>
            <div className="text-[11px] text-gray-700 mb-2">{n.body}</div>
            <div className="text-[9.5px] text-text-muted font-mono">
              {n.channel} · Статус: {getNotificationStatusLabel(n.status)} · {formatDate(n.created_at)}
            </div>
          </div>

          {n.status === 'PENDING' && (
            <button
              className="bg-black text-white text-[9.5px] font-extrabold px-3 py-1.5 rounded uppercase self-start sm:self-center hover:bg-gray-800 shrink-0"
              onClick={() => markNotifRead(n.id)}
            >
              Прочитано
            </button>
          )}
        </div>
      ))}
    </div>
  );
};
