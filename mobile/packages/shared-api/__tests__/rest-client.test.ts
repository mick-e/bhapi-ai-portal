import { ApiClient, ApiError } from '../src/rest-client';

const mockFetch = jest.fn();
global.fetch = mockFetch as any;

describe('ApiClient', () => {
  const client = new ApiClient({
    baseUrl: 'https://api.bhapi.ai',
    getToken: async () => 'test-token-123',
  });

  beforeEach(() => {
    mockFetch.mockReset();
  });

  test('GET request includes auth header', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ data: 'test' }),
    });
    await client.get('/api/v1/test');
    expect(mockFetch).toHaveBeenCalledWith(
      'https://api.bhapi.ai/api/v1/test',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token-123',
        }),
      }),
    );
  });

  test('POST request sends JSON body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: '1' }),
    });
    await client.post('/api/v1/test', { name: 'test' });
    expect(mockFetch).toHaveBeenCalledWith(
      'https://api.bhapi.ai/api/v1/test',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'test' }),
      }),
    );
  });

  test('throws ApiError on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 403,
      json: async () => ({ error: 'Forbidden', code: 'FORBIDDEN' }),
    });
    await expect(client.get('/api/v1/secret')).rejects.toThrow(ApiError);
  });

  test('ApiError contains status and code', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ error: 'Not found', code: 'NOT_FOUND' }),
    });
    try {
      await client.get('/api/v1/missing');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(404);
      expect((e as ApiError).code).toBe('NOT_FOUND');
    }
  });

  test('handles no token gracefully', async () => {
    const noAuthClient = new ApiClient({
      baseUrl: 'https://api.bhapi.ai',
      getToken: async () => null,
    });
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });
    await noAuthClient.get('/api/v1/public');
    const callHeaders = mockFetch.mock.calls[0][1].headers;
    expect(callHeaders.Authorization).toBeUndefined();
  });
});
