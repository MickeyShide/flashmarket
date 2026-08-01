import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { formatDate } from '../../utils/formatters';

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
      {notifications.map(n => {
        const isUnread = !n.read_at && n.status !== 'READ';

        return (
          <div
            key={n.id}
            className={`p-4 border rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-colors ${
              isUnread ? 'bg-amber-50/70 border-amber-200' : 'bg-white border-border-color'
            }`}
          >
            <div>
              <div className="flex items-center gap-2 mb-1">
                {isUnread && (
                  <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0"></span>
                )}
                <span className="font-extrabold text-[12px] uppercase">{n.subject}</span>
              </div>

              <div className="text-[11.5px] text-gray-700 mb-2 leading-relaxed">{n.body}</div>

              {n.attachment_url && (
                <div className="mb-2">
                  <a
                    href={n.attachment_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-[10.5px] font-bold text-purple-600 hover:underline"
                  >
                    📎 Прикрепленный файл →
                  </a>
                </div>
              )}

              <div className="text-[9.5px] text-text-muted font-mono flex items-center gap-2">
                <span>{n.channel || 'SYSTEM'}</span>
                <span>·</span>
                <span>{isUnread ? 'НЕТРОНУТО' : 'ПРОЧИТАНО'}</span>
                <span>·</span>
                <span>{formatDate(n.created_at)}</span>
              </div>
            </div>

            {isUnread && (
              <button
                className="bg-black text-white text-[9.5px] font-extrabold px-3 py-1.5 rounded uppercase self-start sm:self-center hover:bg-gray-800 shrink-0"
                onClick={() => markNotifRead(n.id)}
              >
                Прочитано
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
};
