import { InMemoryStore, createSecureStore, resetSecureStore } from '../src/secure-store';

describe('InMemoryStore', () => {
  let store: InMemoryStore;

  beforeEach(() => {
    store = new InMemoryStore();
  });

  test('getItem returns null for missing key', async () => {
    expect(await store.getItem('nonexistent')).toBeNull();
  });

  test('setItem and getItem round-trip', async () => {
    await store.setItem('key1', 'value1');
    expect(await store.getItem('key1')).toBe('value1');
  });

  test('setItem overwrites existing value', async () => {
    await store.setItem('key1', 'value1');
    await store.setItem('key1', 'value2');
    expect(await store.getItem('key1')).toBe('value2');
  });

  test('deleteItem removes the key', async () => {
    await store.setItem('key1', 'value1');
    await store.deleteItem('key1');
    expect(await store.getItem('key1')).toBeNull();
  });

  test('deleteItem on missing key does not throw', async () => {
    await expect(store.deleteItem('nonexistent')).resolves.toBeUndefined();
  });

  test('setItem with empty key throws', async () => {
    await expect(store.setItem('', 'value')).rejects.toThrow('Key must not be empty');
  });

  test('setItem allows empty string value', async () => {
    await store.setItem('key1', '');
    expect(await store.getItem('key1')).toBe('');
  });

  test('clear removes all items', () => {
    store.setItem('a', '1');
    store.setItem('b', '2');
    store.clear();
    expect(store.size).toBe(0);
  });

  test('size reflects stored item count', async () => {
    expect(store.size).toBe(0);
    await store.setItem('a', '1');
    expect(store.size).toBe(1);
    await store.setItem('b', '2');
    expect(store.size).toBe(2);
    await store.deleteItem('a');
    expect(store.size).toBe(1);
  });
});

describe('createSecureStore', () => {
  beforeEach(() => {
    resetSecureStore();
  });

  test('returns InMemoryStore when expo-secure-store is not available', () => {
    const store = createSecureStore();
    expect(store).toBeInstanceOf(InMemoryStore);
  });

  test('returns same instance on subsequent calls', () => {
    const store1 = createSecureStore();
    const store2 = createSecureStore();
    expect(store1).toBe(store2);
  });

  test('resetSecureStore allows creating a new instance', () => {
    const store1 = createSecureStore();
    resetSecureStore();
    const store2 = createSecureStore();
    expect(store1).not.toBe(store2);
  });
});
