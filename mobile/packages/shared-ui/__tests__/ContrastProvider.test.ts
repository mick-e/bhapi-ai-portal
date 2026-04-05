import { AccessibilityInfo, Platform } from 'react-native';
import { ContrastProvider, useHighContrast } from '../src/ContrastProvider';

describe('ContrastProvider', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AccessibilityInfo.isBoldTextEnabled as jest.Mock).mockResolvedValue(false);
    (AccessibilityInfo.isAccessibilityServiceEnabled as jest.Mock).mockResolvedValue(false);
    (AccessibilityInfo.addEventListener as jest.Mock).mockReturnValue({ remove: jest.fn() });
    (Platform as any).OS = 'ios';
  });

  it('exports ContrastProvider and useHighContrast', () => {
    expect(typeof ContrastProvider).toBe('function');
    expect(typeof useHighContrast).toBe('function');
  });

  it('calls isBoldTextEnabled on iOS', () => {
    (Platform as any).OS = 'ios';
    ContrastProvider({ children: null });
    expect(AccessibilityInfo.isBoldTextEnabled).toHaveBeenCalled();
  });

  it('registers boldTextChanged event listener on iOS', () => {
    (Platform as any).OS = 'ios';
    ContrastProvider({ children: null });
    expect(AccessibilityInfo.addEventListener).toHaveBeenCalledWith(
      'boldTextChanged',
      expect.any(Function),
    );
  });

  it('calls isAccessibilityServiceEnabled on Android', () => {
    (Platform as any).OS = 'android';
    ContrastProvider({ children: null });
    expect(AccessibilityInfo.isAccessibilityServiceEnabled).toHaveBeenCalled();
  });

  it('does not register event listener on Android', () => {
    (Platform as any).OS = 'android';
    ContrastProvider({ children: null });
    expect(AccessibilityInfo.addEventListener).not.toHaveBeenCalled();
  });

  it('resolves isBoldTextEnabled as true when OS bold is enabled', async () => {
    (AccessibilityInfo.isBoldTextEnabled as jest.Mock).mockResolvedValue(true);
    const result = await AccessibilityInfo.isBoldTextEnabled();
    expect(result).toBe(true);
  });

  it('resolves isBoldTextEnabled as false by default', async () => {
    const result = await AccessibilityInfo.isBoldTextEnabled();
    expect(result).toBe(false);
  });
});
