const STORAGE_UNAVAILABLE_MESSAGE =
  'Хранилище файлов недоступно или блокирует запрос CORS. Проверьте адрес хранилища и его CORS-политику.';

export async function uploadPresignedFile(file, uploadUrl, uploadFields = {}) {
  if (!uploadUrl) {
    throw new Error('Сервер не вернул адрес для загрузки файла');
  }

  const formData = new FormData();
  Object.entries(uploadFields).forEach(([key, value]) => {
    formData.append(key, value);
  });
  formData.append('file', file);

  let uploadRes;
  try {
    uploadRes = await fetch(uploadUrl, {
      method: 'POST',
      body: formData
    });
  } catch (cause) {
    throw new Error(STORAGE_UNAVAILABLE_MESSAGE, { cause });
  }

  if (!uploadRes.ok) {
    throw new Error(`Ошибка загрузки файла на сервер хранения: ${uploadRes.status}`);
  }

  return uploadRes;
}
