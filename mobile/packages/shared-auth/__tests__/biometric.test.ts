import {
  isBiometricAvailable,
  authenticateWithBiometric,
  getSupportedBiometricTypes,
  resetBiometricModule,
  BiometricType,
} from '../src/biometric';

// Mock expo-local-authentication
const mockLocalAuth = {
  hasHardwareAsync: jest.fn(),
  isEnrolledAsync: jest.fn(),
  supportedAuthenticationTypesAsync: jest.fn(),
  authenticateAsync: jest.fn(),
};

describe('biometric (no expo module)', () => {
  beforeEach(() => {
    resetBiometricModule();
  });

  test('isBiometricAvailable returns false when module unavailable', async () => {
    expect(await isBiometricAvailable()).toBe(false);
  });

  test('authenticateWithBiometric returns error when module unavailable', async () => {
    const result = await authenticateWithBiometric();
    expect(result.success).toBe(false);
    expect(result.error).toBe('Biometric authentication not available');
  });

  test('getSupportedBiometricTypes returns empty array when module unavailable', async () => {
    expect(await getSupportedBiometricTypes()).toEqual([]);
  });
});

describe('biometric (with expo module)', () => {
  beforeEach(() => {
    resetBiometricModule();
    jest.resetModules();
    mockLocalAuth.hasHardwareAsync.mockReset();
    mockLocalAuth.isEnrolledAsync.mockReset();
    mockLocalAuth.supportedAuthenticationTypesAsync.mockReset();
    mockLocalAuth.authenticateAsync.mockReset();

    // Mock the require call
    jest.mock('expo-local-authentication', () => mockLocalAuth, { virtual: true });
  });

  afterEach(() => {
    jest.unmock('expo-local-authentication');
  });

  test('isBiometricAvailable returns true when hardware present and enrolled', async () => {
    mockLocalAuth.hasHardwareAsync.mockResolvedValue(true);
    mockLocalAuth.isEnrolledAsync.mockResolvedValue(true);

    // Re-import to pick up mock
    const bio = require('../src/biometric');
    bio.resetBiometricModule();
    expect(await bio.isBiometricAvailable()).toBe(true);
  });

  test('isBiometricAvailable returns false when no hardware', async () => {
    mockLocalAuth.hasHardwareAsync.mockResolvedValue(false);

    const bio = require('../src/biometric');
    bio.resetBiometricModule();
    expect(await bio.isBiometricAvailable()).toBe(false);
  });

  test('isBiometricAvailable returns false when not enrolled', async () => {
    mockLocalAuth.hasHardwareAsync.mockResolvedValue(true);
    mockLocalAuth.isEnrolledAsync.mockResolvedValue(false);

    const bio = require('../src/biometric');
    bio.resetBiometricModule();
    expect(await bio.isBiometricAvailable()).toBe(false);
  });

  test('authenticateWithBiometric returns success on successful auth', async () => {
    mockLocalAuth.authenticateAsync.mockResolvedValue({ success: true });

    const bio = require('../src/biometric');
    bio.resetBiometricModule();
    const result = await bio.authenticateWithBiometric('Unlock');
    expect(result.success).toBe(true);
    expect(result.error).toBeUndefined();
  });

  test('authenticateWithBiometric returns error on failed auth', async () => {
    mockLocalAuth.authenticateAsync.mockResolvedValue({
      success: false,
      error: 'user_cancel',
    });

    const bio = require('../src/biometric');
    bio.resetBiometricModule();
    const result = await bio.authenticateWithBiometric();
    expect(result.success).toBe(false);
    expect(result.error).toBe('user_cancel');
  });

  test('authenticateWithBiometric handles exception', async () => {
    mockLocalAuth.authenticateAsync.mockRejectedValue(new Error('Hardware error'));

    const bio = require('../src/biometric');
    bio.resetBiometricModule();
    const result = await bio.authenticateWithBiometric();
    expect(result.success).toBe(false);
    expect(result.error).toBe('Hardware error');
  });
});

describe('BiometricType enum', () => {
  test('has expected values', () => {
    expect(BiometricType.FINGERPRINT).toBe('fingerprint');
    expect(BiometricType.FACE).toBe('face');
    expect(BiometricType.IRIS).toBe('iris');
  });
});
