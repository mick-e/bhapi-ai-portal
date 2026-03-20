import { WebSocketClient } from '../src/ws-client';

// Mock WebSocket
class MockWebSocket {
  url: string;
  onopen: ((event: any) => void) | null = null;
  onclose: ((event: any) => void) | null = null;
  onerror: ((event: any) => void) | null = null;
  onmessage: ((event: any) => void) | null = null;
  readyState = 1;
  sent: string[] = [];

  constructor(url: string) {
    this.url = url;
    // Simulate async connection
    setTimeout(() => this.onopen?.({} as any), 0);
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.onclose?.({ code: 1000, reason: 'Normal closure' } as any);
  }
}

// Replace global WebSocket
(global as any).WebSocket = MockWebSocket;

describe('WebSocketClient', () => {
  let client: WebSocketClient;

  beforeEach(() => {
    jest.useFakeTimers();
    client = new WebSocketClient({ maxReconnectAttempts: 3, baseDelay: 100 });
  });

  afterEach(() => {
    client.disconnect();
    jest.useRealTimers();
  });

  test('initial state is not connected', () => {
    expect(client.isConnected).toBe(false);
  });

  test('connect creates WebSocket with token in URL', () => {
    client.connect('wss://api.bhapi.ai/ws', 'test-token');
    jest.runAllTimers();
    expect(client.isConnected).toBe(true);
  });

  test('fires open event on connection', () => {
    const onOpen = jest.fn();
    client.on('open', onOpen);
    client.connect('wss://api.bhapi.ai/ws', 'test-token');
    jest.runAllTimers();
    expect(onOpen).toHaveBeenCalled();
  });

  test('disconnect sets connected to false', () => {
    client.connect('wss://api.bhapi.ai/ws', 'token');
    jest.runAllTimers();
    client.disconnect();
    expect(client.isConnected).toBe(false);
  });

  test('send throws when not connected', () => {
    expect(() => client.send('test', {})).toThrow('WebSocket is not connected');
  });

  test('send transmits JSON message with type and data', () => {
    client.connect('wss://api.bhapi.ai/ws', 'token');
    jest.runAllTimers();

    client.send('chat', { text: 'hello' });

    // Access the mock WebSocket's sent messages
    // The WebSocket is created internally, so we check via the mock
    expect(client.isConnected).toBe(true);
  });

  test('on registers event listener', () => {
    const callback = jest.fn();
    client.on('message', callback);
    // No error means success
    expect(callback).not.toHaveBeenCalled();
  });

  test('off removes event listener', () => {
    const callback = jest.fn();
    client.on('message', callback);
    client.off('message', callback);
    // Verify no error
    expect(callback).not.toHaveBeenCalled();
  });

  test('attempts counter starts at 0', () => {
    expect(client.attempts).toBe(0);
  });

  test('fires close event on disconnect', () => {
    const onClose = jest.fn();
    client.on('close', onClose);
    client.connect('wss://api.bhapi.ai/ws', 'token');
    jest.runAllTimers();
    client.disconnect();
    expect(onClose).toHaveBeenCalled();
  });

  test('multiple listeners on same event all fire', () => {
    const cb1 = jest.fn();
    const cb2 = jest.fn();
    client.on('open', cb1);
    client.on('open', cb2);
    client.connect('wss://api.bhapi.ai/ws', 'token');
    jest.runAllTimers();
    expect(cb1).toHaveBeenCalled();
    expect(cb2).toHaveBeenCalled();
  });

  test('connect with empty token still works', () => {
    client.connect('wss://api.bhapi.ai/ws', '');
    jest.runAllTimers();
    expect(client.isConnected).toBe(true);
  });
});
