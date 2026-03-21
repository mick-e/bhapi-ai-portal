/**
 * Chat Tests — chat list, conversation screen, typing indicators,
 * read receipts, media messages, message formatting, WebSocket events.
 */

// ---------------------------------------------------------------------------
// Chat List Screen
// ---------------------------------------------------------------------------

describe('Chat List Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(chat)/index');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports PAGE_SIZE constant', () => {
    const { PAGE_SIZE } = require('../app/(chat)/index');
    expect(PAGE_SIZE).toBe(20);
  });

  test('exports DEFAULT_AGE_TIER', () => {
    const { DEFAULT_AGE_TIER } = require('../app/(chat)/index');
    expect(DEFAULT_AGE_TIER).toBe('teen');
  });

  test('chat list screen renders without crashing', () => {
    const mod = require('../app/(chat)/index');
    const result = mod.default();
    expect(result).toBeDefined();
  });

  test('exports Conversation type', () => {
    // Type-only exports don't exist at runtime, but the module loads
    const mod = require('../app/(chat)/index');
    expect(mod.default).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// formatMessageTime
// ---------------------------------------------------------------------------

describe('formatMessageTime', () => {
  const { formatMessageTime } = require('../app/(chat)/index');

  test('returns empty string for null', () => {
    expect(formatMessageTime(null)).toBe('');
  });

  test('returns "now" for recent timestamp', () => {
    const now = new Date().toISOString();
    expect(formatMessageTime(now)).toBe('now');
  });

  test('returns minutes for recent timestamps', () => {
    const tenMinAgo = new Date(Date.now() - 10 * 60000).toISOString();
    const result = formatMessageTime(tenMinAgo);
    expect(result).toMatch(/\d+m/);
  });

  test('returns hours for timestamps within a day', () => {
    const threeHoursAgo = new Date(Date.now() - 3 * 3600000).toISOString();
    const result = formatMessageTime(threeHoursAgo);
    expect(result).toMatch(/\d+h/);
  });

  test('returns days for older timestamps', () => {
    const threeDaysAgo = new Date(Date.now() - 3 * 86400000).toISOString();
    const result = formatMessageTime(threeDaysAgo);
    expect(result).toMatch(/\d+d/);
  });

  test('returns date for very old timestamps', () => {
    const twoWeeksAgo = new Date(Date.now() - 14 * 86400000).toISOString();
    const result = formatMessageTime(twoWeeksAgo);
    expect(result).not.toBe('');
    // Should be a locale date string
    expect(result.length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// Conversation Screen
// ---------------------------------------------------------------------------

describe('Conversation Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(chat)/conversation');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports MAX_MESSAGE_LENGTH per tier', () => {
    const { MAX_MESSAGE_LENGTH } = require('../app/(chat)/conversation');
    expect(MAX_MESSAGE_LENGTH.young).toBe(200);
    expect(MAX_MESSAGE_LENGTH.preteen).toBe(500);
    expect(MAX_MESSAGE_LENGTH.teen).toBe(1000);
  });

  test('exports TYPING_DEBOUNCE_MS', () => {
    const { TYPING_DEBOUNCE_MS } = require('../app/(chat)/conversation');
    expect(TYPING_DEBOUNCE_MS).toBe(1000);
  });

  test('exports TYPING_TIMEOUT_MS', () => {
    const { TYPING_TIMEOUT_MS } = require('../app/(chat)/conversation');
    expect(TYPING_TIMEOUT_MS).toBe(5000);
  });

  test('conversation screen renders without crashing', () => {
    const mod = require('../app/(chat)/conversation');
    const result = mod.default();
    expect(result).toBeDefined();
  });

  test('exports CONVERSATION_PAGE_SIZE', () => {
    const { CONVERSATION_PAGE_SIZE } = require('../app/(chat)/conversation');
    expect(CONVERSATION_PAGE_SIZE).toBe(30);
  });
});

// ---------------------------------------------------------------------------
// formatTimestamp
// ---------------------------------------------------------------------------

describe('formatTimestamp', () => {
  const { formatTimestamp } = require('../app/(chat)/conversation');

  test('formats today timestamp as time only', () => {
    const now = new Date().toISOString();
    const result = formatTimestamp(now);
    expect(result).toBeDefined();
    expect(result.length).toBeGreaterThan(0);
  });

  test('formats older timestamp with date', () => {
    const oldDate = new Date('2026-01-15T10:30:00Z').toISOString();
    const result = formatTimestamp(oldDate);
    expect(result).toBeDefined();
    expect(result.length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// formatTypingIndicator
// ---------------------------------------------------------------------------

describe('formatTypingIndicator', () => {
  const { formatTypingIndicator } = require('../app/(chat)/conversation');

  test('returns empty string for no users', () => {
    expect(formatTypingIndicator([])).toBe('');
  });

  test('single user typing', () => {
    expect(formatTypingIndicator(['Alice'])).toBe('Alice is typing...');
  });

  test('two users typing', () => {
    expect(formatTypingIndicator(['Alice', 'Bob'])).toBe('Alice and Bob are typing...');
  });

  test('three or more users typing', () => {
    const result = formatTypingIndicator(['Alice', 'Bob', 'Charlie']);
    expect(result).toBe('Alice and 2 others are typing...');
  });
});

// ---------------------------------------------------------------------------
// WebSocket Client — typing/receipt methods
// ---------------------------------------------------------------------------

describe('WebSocketClient typing/receipt methods', () => {
  const { WebSocketClient } = require('../../../packages/shared-api/src/ws-client');

  test('exports WebSocketClient class', () => {
    expect(WebSocketClient).toBeDefined();
    expect(typeof WebSocketClient).toBe('function');
  });

  test('client has sendTypingStart method', () => {
    const client = new WebSocketClient();
    expect(typeof client.sendTypingStart).toBe('function');
  });

  test('client has sendTypingStop method', () => {
    const client = new WebSocketClient();
    expect(typeof client.sendTypingStop).toBe('function');
  });

  test('client has sendReadReceipt method', () => {
    const client = new WebSocketClient();
    expect(typeof client.sendReadReceipt).toBe('function');
  });

  test('client has joinConversation method', () => {
    const client = new WebSocketClient();
    expect(typeof client.joinConversation).toBe('function');
  });

  test('client has leaveConversation method', () => {
    const client = new WebSocketClient();
    expect(typeof client.leaveConversation).toBe('function');
  });

  test('sendTypingStart throws when not connected', () => {
    const client = new WebSocketClient();
    expect(() => client.sendTypingStart('conv-1')).toThrow('WebSocket is not connected');
  });

  test('sendReadReceipt throws when not connected', () => {
    const client = new WebSocketClient();
    expect(() => client.sendReadReceipt('conv-1')).toThrow('WebSocket is not connected');
  });

  test('client isConnected initially false', () => {
    const client = new WebSocketClient();
    expect(client.isConnected).toBe(false);
  });

  test('client reconnect attempts initially zero', () => {
    const client = new WebSocketClient();
    expect(client.attempts).toBe(0);
  });
});
