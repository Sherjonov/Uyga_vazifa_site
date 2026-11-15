export const isImage = url => /\.(png|jpe?g|webp|gif)$/i.test((url || '').split('?')[0]);
export const fileName = url => decodeURIComponent((url || '').split('/').pop() || '').replace(/^[0-9a-f]{12}_/, '');
