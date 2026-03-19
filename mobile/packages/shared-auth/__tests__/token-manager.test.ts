import { tokenManager } from '../src/token-manager';

function makeToken(expSeconds: number): string {
  const header = btoa(JSON.stringify({ alg: 'HS256' }));
  const payload = btoa(JSON.stringify({
    user_id: 'test-123',
    type: 'session',
    exp: Math.floor(Date.now() / 1000) + expSeconds,
  }));
  return `${header}.${payload}.fake-signature`;
}

describe('tokenManager', () => {
  beforeEach(async () => {
    await tokenManager.clearToken();
  });

  test('getToken returns null when no token set', async () => {
    expect(await tokenManager.getToken()).toBeNull();
  });

  test('setToken stores and getToken retrieves', async () => {
    const token = makeToken(3600);
    await tokenManager.setToken(token);
    expect(await tokenManager.getToken()).toBe(token);
  });

  test('clearToken removes stored token', async () => {
    await tokenManager.setToken(makeToken(3600));
    await tokenManager.clearToken();
    expect(await tokenManager.getToken()).toBeNull();
  });

  test('isAuthenticated returns false with no token', async () => {
    expect(await tokenManager.isAuthenticated()).toBe(false);
  });

  test('isAuthenticated returns true with valid unexpired token', async () => {
    await tokenManager.setToken(makeToken(3600));
    expect(await tokenManager.isAuthenticated()).toBe(true);
  });

  test('isAuthenticated returns false with expired token', async () => {
    await tokenManager.setToken(makeToken(-60));
    expect(await tokenManager.isAuthenticated()).toBe(false);
  });
});
