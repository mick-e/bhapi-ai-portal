/**
 * Biometric authentication wrapper.
 * Uses expo-local-authentication on native, returns unavailable on web/test.
 */

export interface BiometricResult {
  success: boolean;
  error?: string;
}

export enum BiometricType {
  FINGERPRINT = 'fingerprint',
  FACE = 'face',
  IRIS = 'iris',
}

let _localAuth: any = null;

function getLocalAuth(): any {
  if (_localAuth !== undefined && _localAuth !== null) return _localAuth;
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    _localAuth = require('expo-local-authentication');
    return _localAuth;
  } catch {
    _localAuth = null;
    return null;
  }
}

/**
 * Check if biometric authentication hardware is available.
 */
export async function isBiometricAvailable(): Promise<boolean> {
  const auth = getLocalAuth();
  if (!auth) return false;

  try {
    const hasHardware = await auth.hasHardwareAsync();
    if (!hasHardware) return false;
    const isEnrolled = await auth.isEnrolledAsync();
    return isEnrolled;
  } catch {
    return false;
  }
}

/**
 * Get available biometric types on the device.
 */
export async function getSupportedBiometricTypes(): Promise<BiometricType[]> {
  const auth = getLocalAuth();
  if (!auth) return [];

  try {
    const types = await auth.supportedAuthenticationTypesAsync();
    return types.map((t: number) => {
      switch (t) {
        case 1: return BiometricType.FINGERPRINT;
        case 2: return BiometricType.FACE;
        case 3: return BiometricType.IRIS;
        default: return BiometricType.FINGERPRINT;
      }
    });
  } catch {
    return [];
  }
}

/**
 * Prompt the user for biometric authentication.
 */
export async function authenticateWithBiometric(
  promptMessage = 'Authenticate to access Bhapi',
): Promise<BiometricResult> {
  const auth = getLocalAuth();
  if (!auth) {
    return { success: false, error: 'Biometric authentication not available' };
  }

  try {
    const result = await auth.authenticateAsync({
      promptMessage,
      disableDeviceFallback: false,
    });

    if (result.success) {
      return { success: true };
    }

    return {
      success: false,
      error: result.error || 'Authentication failed',
    };
  } catch (e: any) {
    return {
      success: false,
      error: e?.message || 'Biometric authentication error',
    };
  }
}

/**
 * Reset the local auth module (for testing).
 */
export function resetBiometricModule(): void {
  _localAuth = null;
}
