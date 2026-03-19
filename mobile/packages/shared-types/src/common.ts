export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

/** Matches the backend's paginated response format (capture events, etc.) */
export interface PagedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ErrorResponse {
  error: string;
  code: string;
}

export interface ApiResponse<T> {
  data: T | null;
  error: ErrorResponse | null;
  loading: boolean;
}
