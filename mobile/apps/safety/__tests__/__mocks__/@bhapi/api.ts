export class ApiClient {
  constructor(_config: any) {}
  async get<T>(_path: string): Promise<T> { return {} as T; }
  async post<T>(_path: string, _body: any): Promise<T> { return {} as T; }
  async put<T>(_path: string, _body: any): Promise<T> { return {} as T; }
  async delete<T>(_path: string): Promise<T> { return {} as T; }
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}
