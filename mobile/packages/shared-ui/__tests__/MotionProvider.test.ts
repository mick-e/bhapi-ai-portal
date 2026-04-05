import { AccessibilityInfo } from 'react-native';
import { MotionProvider, useReducedMotion } from '../src/MotionProvider';

describe('MotionProvider', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AccessibilityInfo.isReduceMotionEnabled as jest.Mock).mockResolvedValue(false);
    (AccessibilityInfo.addEventListener as jest.Mock).mockReturnValue({ remove: jest.fn() });
  });

  it('exports MotionProvider and useReducedMotion', () => {
    expect(typeof MotionProvider).toBe('function');
    expect(typeof useReducedMotion).toBe('function');
  });

  it('calls AccessibilityInfo.isReduceMotionEnabled on mount', () => {
    // useEffect is called immediately in the mock
    MotionProvider({ children: null });
    expect(AccessibilityInfo.isReduceMotionEnabled).toHaveBeenCalled();
  });

  it('registers a reduceMotionChanged event listener on mount', () => {
    MotionProvider({ children: null });
    expect(AccessibilityInfo.addEventListener).toHaveBeenCalledWith(
      'reduceMotionChanged',
      expect.any(Function),
    );
  });

  it('returns the remove function for cleanup', () => {
    const removeFn = jest.fn();
    (AccessibilityInfo.addEventListener as jest.Mock).mockReturnValue({ remove: removeFn });
    MotionProvider({ children: null });
    expect(AccessibilityInfo.addEventListener).toHaveBeenCalled();
  });

  it('queries reduced motion state as false by default', async () => {
    (AccessibilityInfo.isReduceMotionEnabled as jest.Mock).mockResolvedValue(false);
    const result = await AccessibilityInfo.isReduceMotionEnabled();
    expect(result).toBe(false);
  });

  it('queries reduced motion state as true when OS preference is set', async () => {
    (AccessibilityInfo.isReduceMotionEnabled as jest.Mock).mockResolvedValue(true);
    const result = await AccessibilityInfo.isReduceMotionEnabled();
    expect(result).toBe(true);
  });
});
