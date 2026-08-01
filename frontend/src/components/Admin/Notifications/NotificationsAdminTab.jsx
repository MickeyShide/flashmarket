import React, { useState } from 'react';
import { apiJson } from '../../../services/api';
import { useToast } from '../../../context/ToastContext';
import { MediaUploader } from '../../Media/MediaUploader';

export const NotificationsAdminTab = () => {
  const { triggerToast } = useToast();
  const [userId, setUserId] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [channel, setChannel] = useState('SYSTEM');
  const [attachmentUrl, setAttachmentUrl] = useState('');
  const [sending, setSending] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!userId.trim() || !subject.trim() || !body.trim()) return;

    setSending(true);
    try {
      const payload = {
        user_id: userId.trim(),
        subject: subject.trim(),
        body: body.trim(),
        channel,
        attachment_url: attachmentUrl || null
      };

      await apiJson('/api/v1/notifications', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      triggerToast('Уведомление успешно отправлено!');
      setUserId('');
      setSubject('');
      setBody('');
      setAttachmentUrl('');
    } catch (err) {
      triggerToast(err.message || 'Ошибка отправки уведомления', true);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="max-w-2xl bg-white border border-border-color rounded-lg p-6 space-y-4">
      <h3 className="text-sm font-black uppercase">Отправка индивидуального уведомления</h3>

      <form onSubmit={handleSubmit} className="space-y-4 text-xs">
        <div>
          <label className="block font-bold uppercase mb-1">ID пользователя (UUID) *</label>
          <input
            type="text"
            required
            placeholder="00000000-0000-0000-0000-000000000000"
            className="w-full border p-2 rounded font-mono text-[11px]"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block font-bold uppercase mb-1">Заголовок *</label>
            <input
              type="text"
              required
              placeholder="Важная информация"
              className="w-full border p-2 rounded font-sans"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          </div>

          <div>
            <label className="block font-bold uppercase mb-1">Канал</label>
            <select
              className="w-full border p-2 rounded font-bold uppercase"
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
            >
              <option value="SYSTEM">SYSTEM</option>
              <option value="EMAIL">EMAIL</option>
              <option value="DROP_ALERT">DROP_ALERT</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block font-bold uppercase mb-1">Текст сообщения *</label>
          <textarea
            required
            rows={4}
            className="w-full border p-2 rounded font-sans"
            placeholder="Введите текст уведомления..."
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
        </div>

        <div>
          <label className="block font-bold uppercase mb-1">Прикрепить медиа-ассет (необязательно)</label>
          <MediaUploader
            purpose="public_asset"
            currentUrl={attachmentUrl}
            onSuccess={(url) => setAttachmentUrl(url)}
            label="Загрузить прикрепляемый файл"
          />
        </div>

        <button
          type="submit"
          disabled={sending}
          className="bg-black text-white px-6 py-3 rounded font-black uppercase tracking-wider hover:bg-gray-800 disabled:opacity-50 mt-2"
        >
          {sending ? 'Отправка...' : 'Отправить уведомление'}
        </button>
      </form>
    </div>
  );
};
