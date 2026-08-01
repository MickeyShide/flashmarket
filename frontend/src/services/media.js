import { apiJson } from './api';

/**
 * Helper to perform full presigned media upload:
 * 1. Initiate media asset creation
 * 2. Upload file binary directly to S3/MinIO using presigned form data
 * 3. Complete media asset registration
 */
export async function uploadMediaAsset(file, purpose = 'general', entityType = null, entityId = null) {
  if (!file) {
    throw new Error('Файл не выбран');
  }

  // Client-side file validations
  const maxSizeMb = {
    user_avatar: 5,
    product_image: 15,
    brand_logo: 10,
    drop_image: 15,
    notification_attachment: 10,
    public_asset: 25
  }[purpose] || 10;
  const maxSizeBytes = maxSizeMb * 1024 * 1024;
  if (file.size > maxSizeBytes) {
    throw new Error(`Размер файла превышает ${maxSizeMb} МБ`);
  }
  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
  if (['notification_attachment', 'public_asset'].includes(purpose)) allowedTypes.push('application/pdf');
  if (!allowedTypes.includes(file.type)) throw new Error('Неподдерживаемый тип файла');

  // 1. Create upload request
  const body = {
    filename: file.name,
    content_type: file.type || 'application/octet-stream',
    size: file.size,
    purpose
  };
  if (entityType && entityId) {
    body.entity_type = entityType;
    body.entity_id = entityId;
  }

  const initData = await apiJson('/api/v1/media/uploads', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });

  const assetId = initData.asset.id;
  const uploadUrl = initData.upload.url;
  const uploadFields = initData.upload.fields || {};

  // 2. Direct FormData POST to S3/MinIO presigned URL (no authorization headers)
  if (uploadUrl) {
    const formData = new FormData();
    Object.entries(uploadFields).forEach(([key, val]) => {
      formData.append(key, val);
    });
    formData.append('file', file);

    const uploadRes = await fetch(uploadUrl, {
      method: 'POST',
      body: formData
    });

    if (!uploadRes.ok && uploadRes.status !== 204) {
      throw new Error(`Ошибка загрузки файла на сервер хранения: ${uploadRes.status}`);
    }
  }

  // 3. Mark completion
  const completedData = await apiJson(initData.complete_url || `/api/v1/media/assets/${assetId}/complete`, {
    method: 'POST'
  });

  return completedData;
}
