import React, { useEffect, useCallback } from 'react';
import { apiJson } from '../../../services/api';
import { formatDate } from '../../../utils/formatters';
import { usePaginatedResource } from '../../../hooks/usePaginatedResource';
import { InfiniteScrollTrigger } from '../../Common/InfiniteScrollTrigger';

const PAGE_SIZE = 25;
const auditKey = log => log.id || `${log.event_type}-${log.created_at}-${log.actor_user_id}`;

export const AuditTab = () => {
  const fetchAuditPage = useCallback(({ limit, offset, signal }) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    return apiJson(`/admin/audit-events?${params}`, { signal });
  }, []);

  const {
    items: logs,
    total,
    loading,
    loadingMore,
    error,
    hasMore,
    reload: loadAuditLogs,
    loadMore
  } = usePaginatedResource({ fetchPage: fetchAuditPage, pageSize: PAGE_SIZE, getKey: auditKey });

  useEffect(() => {
    loadAuditLogs();
  }, [loadAuditLogs]);

  if (loading) return <div className="spinner"></div>;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-black uppercase">Журнал аудит-событий ({total})</h3>

      {error && logs.length === 0 && (
        <button className="text-xs font-bold uppercase text-red-700" onClick={loadAuditLogs}>Повторить загрузку</button>
      )}

      {/* Mobile Audit Cards List (< md screens) */}
      <div className="md:hidden space-y-2.5 font-mono text-xs">
        {logs.length === 0 ? (
          <div className="bg-white border border-border-color rounded-lg p-6 text-center text-gray-400">
            Нет записанных событий аудита
          </div>
        ) : (
          logs.map((log, idx) => (
            <div key={log.id || idx} className="bg-white border border-border-color rounded-lg p-3 space-y-1.5 shadow-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="font-extrabold uppercase text-purple-700 text-xs">{log.action || log.event_type}</span>
                <span className="text-[10px] text-gray-400">{formatDate(log.created_at || log.timestamp)}</span>
              </div>
              <div className="text-[10.5px] text-gray-700">Пользователь: {log.actor_user_id || '-'}</div>
              <div className="text-[10px] text-gray-500 bg-gray-50 p-1.5 rounded border break-all leading-tight">
                {JSON.stringify(log.event_data || { subject_user_id: log.subject_user_id })}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Desktop Audit Table (>= md screens) */}
      <div className="hidden md:block bg-white border border-border-color rounded-lg overflow-x-auto w-full">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b text-[10px] font-black uppercase text-gray-500">
              <th className="p-3">Действие</th>
              <th className="p-3">Пользователь</th>
              <th className="p-3">Детали / Payload</th>
              <th className="p-3">Дата</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-xs font-mono">
            {logs.length === 0 ? (
              <tr>
                <td colSpan={4} className="p-4 text-center text-gray-400">Нет записанных событий аудита</td>
              </tr>
            ) : (
              logs.map((log, idx) => (
                <tr key={log.id || idx} className="hover:bg-gray-50 transition-colors">
                  <td className="p-3 font-extrabold uppercase text-purple-700">{log.action || log.event_type}</td>
                  <td className="p-3 text-gray-700">{log.actor_user_id || '-'}</td>
                  <td className="p-3 text-[10.5px] text-gray-600 truncate max-w-xs">
                    {JSON.stringify(log.event_data || { subject_user_id: log.subject_user_id })}
                  </td>
                  <td className="p-3 text-[10.5px] text-gray-500">{formatDate(log.created_at || log.timestamp)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <InfiniteScrollTrigger
        hasMore={hasMore}
        loading={loadingMore}
        error={logs.length > 0 ? error : null}
        onLoadMore={loadMore}
      />
    </div>
  );
};
