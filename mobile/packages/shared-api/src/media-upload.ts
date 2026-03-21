/**
 * Media upload helper for Bhapi mobile apps.
 * Handles presigned URL flow: request upload URL -> upload to R2 -> return media_id.
 * Supports progress callbacks and retry on failure.
 */

import { ApiClient, ApiError } from './rest-client';

export interface MediaFile {
  uri: string;
  type: 'image' | 'video';
  filename?: string;
  mimeType?: string;
  /** File size in bytes (optional, used for server-side validation) */
  size?: number;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  /** 0-100 */
  percentage: number;
}

export type ProgressCallback = (progress: UploadProgress) => void;

export interface UploadResult {
  mediaId: string;
  uploadUrl: string;
}

export interface BatchUploadResult {
  uploads: UploadResult[];
  /** Files that failed to upload (index + error) */
  failures: Array<{ index: number; error: string }>;
}

interface UploadURLResponse {
  upload_url: string;
  media_id: string;
  expires_at: string;
}

interface BatchUploadURLResponse {
  uploads: UploadURLResponse[];
}

const MAX_RETRIES = 3;
const RETRY_BASE_DELAY_MS = 1000;

/**
 * Upload a single media file via the presigned URL flow.
 *
 * 1. Request a presigned upload URL from the backend
 * 2. PUT the file directly to Cloudflare R2
 * 3. Return the media_id for association with posts/messages
 */
export async function uploadMedia(
  client: ApiClient,
  file: MediaFile,
  onProgress?: ProgressCallback,
): Promise<UploadResult> {
  // 1. Request presigned upload URL
  const uploadUrlResp = await client.request<UploadURLResponse>(
    'POST',
    '/api/v1/media/upload',
    {
      media_type: file.type,
      content_length: file.size ?? undefined,
      filename: file.filename ?? undefined,
    },
  );

  const { upload_url, media_id } = uploadUrlResp;

  // 2. Upload file to R2 with retry
  await uploadToR2WithRetry(upload_url, file, onProgress);

  return {
    mediaId: media_id,
    uploadUrl: upload_url,
  };
}

/**
 * Upload multiple files in a single batch request.
 * Gets all presigned URLs at once, then uploads in parallel.
 */
export async function uploadMediaBatch(
  client: ApiClient,
  files: MediaFile[],
  onProgress?: (fileIndex: number, progress: UploadProgress) => void,
): Promise<BatchUploadResult> {
  if (files.length === 0) {
    return { uploads: [], failures: [] };
  }

  // 1. Request batch presigned URLs
  const batchResp = await client.request<BatchUploadURLResponse>(
    'POST',
    '/api/v1/media/upload/batch',
    {
      files: files.map((f) => ({
        media_type: f.type,
        content_length: f.size ?? undefined,
        filename: f.filename ?? undefined,
      })),
    },
  );

  // 2. Upload all files in parallel
  const results: UploadResult[] = [];
  const failures: Array<{ index: number; error: string }> = [];

  const uploadPromises = batchResp.uploads.map(async (urlData, index) => {
    try {
      const fileProgressCb = onProgress
        ? (p: UploadProgress) => onProgress(index, p)
        : undefined;

      await uploadToR2WithRetry(urlData.upload_url, files[index], fileProgressCb);

      results.push({
        mediaId: urlData.media_id,
        uploadUrl: urlData.upload_url,
      });
    } catch (err) {
      failures.push({
        index,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  });

  await Promise.allSettled(uploadPromises);

  return { uploads: results, failures };
}

/**
 * Upload file content to R2 via presigned URL with retry logic.
 */
async function uploadToR2WithRetry(
  uploadUrl: string,
  file: MediaFile,
  onProgress?: ProgressCallback,
): Promise<void> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      await uploadToR2(uploadUrl, file, onProgress);
      return;
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err));

      // Don't retry on client errors (4xx)
      if (err instanceof ApiError && err.statusCode >= 400 && err.statusCode < 500) {
        throw err;
      }

      if (attempt < MAX_RETRIES) {
        const delay = RETRY_BASE_DELAY_MS * Math.pow(2, attempt);
        await sleep(delay);
      }
    }
  }

  throw lastError ?? new Error('Upload failed after retries');
}

/**
 * Perform the actual upload to R2 using XMLHttpRequest (supports progress events).
 */
async function uploadToR2(
  uploadUrl: string,
  file: MediaFile,
  onProgress?: ProgressCallback,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', uploadUrl);

    if (file.mimeType) {
      xhr.setRequestHeader('Content-Type', file.mimeType);
    }

    if (onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          onProgress({
            loaded: event.loaded,
            total: event.total,
            percentage: Math.round((event.loaded / event.total) * 100),
          });
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new ApiError(xhr.status, 'UPLOAD_FAILED', `R2 upload failed: ${xhr.status}`));
      }
    };

    xhr.onerror = () => {
      reject(new ApiError(0, 'NETWORK_ERROR', 'Network error during upload'));
    };

    xhr.ontimeout = () => {
      reject(new ApiError(0, 'TIMEOUT', 'Upload timed out'));
    };

    // For React Native, we create a form data with the file URI
    const formData = new FormData();
    formData.append('file', {
      uri: file.uri,
      type: file.mimeType ?? 'application/octet-stream',
      name: file.filename ?? 'upload',
    } as unknown as Blob);

    xhr.send(formData);
  });
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
