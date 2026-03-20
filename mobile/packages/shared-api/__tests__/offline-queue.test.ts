import { OfflineQueue, ReplayClient } from '../src/offline-queue';

describe('OfflineQueue', () => {
  let queue: OfflineQueue;

  beforeEach(() => {
    queue = new OfflineQueue({ maxSize: 5, maxAgeMs: 60000 });
  });

  test('starts empty', () => {
    expect(queue.getSize()).toBe(0);
    expect(queue.getQueue()).toEqual([]);
  });

  test('enqueue adds a request', () => {
    queue.enqueue({ method: 'POST', path: '/api/v1/test', body: { data: 1 } });
    expect(queue.getSize()).toBe(1);
  });

  test('enqueue returns an ID', () => {
    const id = queue.enqueue({ method: 'POST', path: '/api/v1/test' });
    expect(id).toBeTruthy();
    expect(typeof id).toBe('string');
  });

  test('enqueue respects maxSize by evicting oldest', () => {
    for (let i = 0; i < 7; i++) {
      queue.enqueue({ method: 'POST', path: `/api/v1/item/${i}` });
    }
    expect(queue.getSize()).toBe(5);
    // Oldest entries (0, 1) should be evicted
    const paths = queue.getQueue().map(r => r.path);
    expect(paths).not.toContain('/api/v1/item/0');
    expect(paths).not.toContain('/api/v1/item/1');
    expect(paths).toContain('/api/v1/item/6');
  });

  test('clear empties the queue', () => {
    queue.enqueue({ method: 'POST', path: '/test' });
    queue.enqueue({ method: 'PUT', path: '/test' });
    queue.clear();
    expect(queue.getSize()).toBe(0);
  });

  test('remove deletes a specific request by ID', () => {
    const id = queue.enqueue({ method: 'POST', path: '/test' });
    expect(queue.remove(id)).toBe(true);
    expect(queue.getSize()).toBe(0);
  });

  test('remove returns false for unknown ID', () => {
    expect(queue.remove('nonexistent')).toBe(false);
  });

  test('getQueue returns a copy', () => {
    queue.enqueue({ method: 'POST', path: '/test' });
    const q1 = queue.getQueue();
    const q2 = queue.getQueue();
    expect(q1).not.toBe(q2);
    expect(q1).toEqual(q2);
  });

  test('queued request has timestamp', () => {
    const before = Date.now();
    queue.enqueue({ method: 'POST', path: '/test' });
    const after = Date.now();
    const request = queue.getQueue()[0];
    expect(request.timestamp).toBeGreaterThanOrEqual(before);
    expect(request.timestamp).toBeLessThanOrEqual(after);
  });

  test('isReplaying is false initially', () => {
    expect(queue.isReplaying).toBe(false);
  });
});

describe('OfflineQueue.replay', () => {
  let queue: OfflineQueue;
  let mockClient: ReplayClient;

  beforeEach(() => {
    queue = new OfflineQueue({ maxSize: 100, maxAgeMs: 60000 });
    mockClient = {
      request: jest.fn().mockResolvedValue({}),
    };
  });

  test('replay sends all queued requests', async () => {
    queue.enqueue({ method: 'POST', path: '/api/v1/a', body: { x: 1 } });
    queue.enqueue({ method: 'PUT', path: '/api/v1/b', body: { x: 2 } });

    const result = await queue.replay(mockClient);
    expect(result.succeeded).toBe(2);
    expect(result.failed).toBe(0);
    expect(mockClient.request).toHaveBeenCalledTimes(2);
    expect(queue.getSize()).toBe(0);
  });

  test('replay keeps failed requests in queue', async () => {
    queue.enqueue({ method: 'POST', path: '/api/v1/a' });
    queue.enqueue({ method: 'POST', path: '/api/v1/b' });

    (mockClient.request as jest.Mock)
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error('Server error'));

    const result = await queue.replay(mockClient);
    expect(result.succeeded).toBe(1);
    expect(result.failed).toBe(1);
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0].error).toBe('Server error');
    expect(queue.getSize()).toBe(1);
  });

  test('replay with empty queue succeeds', async () => {
    const result = await queue.replay(mockClient);
    expect(result.succeeded).toBe(0);
    expect(result.failed).toBe(0);
  });

  test('replay drops stale requests', async () => {
    // Create queue with very short maxAge
    queue = new OfflineQueue({ maxSize: 100, maxAgeMs: 1 });
    queue.enqueue({ method: 'POST', path: '/api/v1/old' });

    // Wait for request to become stale
    await new Promise(resolve => setTimeout(resolve, 10));

    const result = await queue.replay(mockClient);
    expect(result.failed).toBe(1);
    expect(mockClient.request).not.toHaveBeenCalled();
    expect(queue.getSize()).toBe(0);
  });

  test('replay passes correct method, path, body to client', async () => {
    queue.enqueue({ method: 'POST', path: '/api/v1/data', body: { key: 'value' } });

    await queue.replay(mockClient);

    expect(mockClient.request).toHaveBeenCalledWith('POST', '/api/v1/data', { key: 'value' });
  });
});
