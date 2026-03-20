import { SessionManager } from '../src/session';
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

describe('SessionManager', () => {
  let session: SessionManager;

  beforeEach(async () => {
    await tokenManager.clearToken();
    session = new SessionManager({
      onRefresh: async () => null,
      checkIntervalSeconds: 60,
    });
  });

  afterEach(async () => {
    await session.endSession();
  });

  test('startSession stores token and activates session', async () => {
    const token = makeToken(3600);
    await session.startSession(token);
    expect(session.isSessionActive()).toBe(true);
    expect(await tokenManager.getToken()).toBe(token);
  });

  test('isSessionActive returns false before start', () => {
    expect(session.isSessionActive()).toBe(false);
  });

  test('isSessionActive returns false with expired token', async () => {
    const token = makeToken(-60);
    await session.startSession(token);
    expect(session.isSessionActive()).toBe(false);
  });

  test('endSession clears token and deactivates', async () => {
    await session.startSession(makeToken(3600));
    await session.endSession();
    expect(session.isSessionActive()).toBe(false);
    expect(await tokenManager.getToken()).toBeNull();
  });

  test('getTimeUntilExpiry returns positive for valid session', async () => {
    await session.startSession(makeToken(3600));
    const remaining = session.getTimeUntilExpiry();
    expect(remaining).toBeGreaterThan(3500);
    expect(remaining).toBeLessThanOrEqual(3600);
  });

  test('getTimeUntilExpiry returns 0 for expired session', async () => {
    await session.startSession(makeToken(-60));
    expect(session.getTimeUntilExpiry()).toBe(0);
  });

  test('getTimeUntilExpiry returns 0 when no session', () => {
    expect(session.getTimeUntilExpiry()).toBe(0);
  });

  test('getExpiry returns token exp timestamp', async () => {
    const token = makeToken(3600);
    await session.startSession(token);
    const expiry = session.getExpiry();
    expect(expiry).not.toBeNull();
    expect(expiry!).toBeGreaterThan(Math.floor(Date.now() / 1000));
  });

  test('getExpiry returns null when no session', () => {
    expect(session.getExpiry()).toBeNull();
  });

  test('refreshSession calls onRefresh and updates token', async () => {
    const newToken = makeToken(7200);
    session = new SessionManager({
      onRefresh: async () => newToken,
      checkIntervalSeconds: 60,
    });

    await session.startSession(makeToken(300));
    const success = await session.refreshSession();
    expect(success).toBe(true);
    expect(await tokenManager.getToken()).toBe(newToken);
  });

  test('refreshSession returns false when onRefresh returns null', async () => {
    session = new SessionManager({
      onRefresh: async () => null,
      checkIntervalSeconds: 60,
    });

    await session.startSession(makeToken(300));
    const success = await session.refreshSession();
    expect(success).toBe(false);
  });

  test('refreshSession returns false when onRefresh throws', async () => {
    session = new SessionManager({
      onRefresh: async () => { throw new Error('Network error'); },
      checkIntervalSeconds: 60,
    });

    await session.startSession(makeToken(300));
    const success = await session.refreshSession();
    expect(success).toBe(false);
  });

  test('multiple startSession calls replace token', async () => {
    const token1 = makeToken(3600);
    const token2 = makeToken(7200);
    await session.startSession(token1);
    await session.startSession(token2);
    expect(await tokenManager.getToken()).toBe(token2);
  });
});
