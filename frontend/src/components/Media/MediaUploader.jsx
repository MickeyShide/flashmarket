import React, { useState } from 'react';
import { uploadMediaAsset } from '../../services/media';
import { useToast } from '../../context/ToastContext';

export const MediaUploader = ({
  purpose = 'general',
  entityType = null,
  entityId = null,
  currentUrl = null,
  onSuccess,
  label = 'Загрузить файл'
}) => {
  const { triggerToast } = useToast();
  const [uploading, setUploading] = useState(false);

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const asset = await uploadMediaAsset(file, purpose, entityType, entityId);
      if (asset?.public_url) {
        triggerToast('Файл успешно загружен!');
        if (onSuccess) onSuccess(asset.public_url, asset);
      }
    } catch (err) {
      triggerToast(err.message || 'Ошибка загрузки медиа-файла', true);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      {currentUrl && (
        <div className="w-24 h-24 bg-black rounded border border-border-color overflow-hidden relative group">
          {/\.pdf(?:\?|$)/i.test(currentUrl) ? (
            <a href={currentUrl} target="_blank" rel="noreferrer" className="w-full h-full flex items-center justify-center text-white text-xs font-bold">PDF</a>
          ) : (
            <img src={currentUrl} alt="Preview" decoding="async" className="w-full h-full object-cover" />
          )}
        </div>
      )}

      <label className="inline-flex items-center justify-center px-3.5 py-2 bg-black text-white text-xs font-bold uppercase rounded cursor-pointer hover:bg-gray-800 disabled:opacity-50 transition-colors w-fit">
        {uploading ? 'Загрузка…' : label}
        <input
          type="file"
          accept={['notification_attachment', 'public_asset'].includes(purpose) ? 'image/*,.pdf' : 'image/*'}
          className="hidden"
          disabled={uploading}
          onChange={handleFileChange}
        />
      </label>
    </div>
  );
};
