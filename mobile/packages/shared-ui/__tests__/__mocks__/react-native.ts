// Mock React Native for testing without Expo/RN runtime
export const StyleSheet = {
  create: <T extends Record<string, any>>(styles: T): T => styles,
};

export const TouchableOpacity = 'TouchableOpacity';
export const Text = 'Text';
export const View = 'View';
export const TextInput = 'TextInput';
export const Image = 'Image';
export const ActivityIndicator = 'ActivityIndicator';
export const Animated = {
  View: 'AnimatedView',
  timing: jest.fn(),
  Value: jest.fn().mockImplementation((val: number) => ({ _value: val })),
};

export const AccessibilityInfo = {
  isReduceMotionEnabled: jest.fn().mockResolvedValue(false),
  isBoldTextEnabled: jest.fn().mockResolvedValue(false),
  isAccessibilityServiceEnabled: jest.fn().mockResolvedValue(false),
  addEventListener: jest.fn().mockReturnValue({ remove: jest.fn() }),
};

export const Platform = {
  OS: 'ios' as 'ios' | 'android',
  select: jest.fn((obj: Record<string, any>) => obj.ios ?? obj.default),
};

export type ViewStyle = Record<string, any>;
export type TextStyle = Record<string, any>;
export type ImageSourcePropType = any;
export type TextInputProps = Record<string, any>;
