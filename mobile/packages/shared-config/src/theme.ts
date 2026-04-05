export const colors = {
  primary: {
    50: '#FFF3ED',
    100: '#FFE4D4',
    500: '#FF6B35',
    600: '#E55A2B',
    700: '#CC4A21',
  },
  accent: {
    50: '#F0FDFA',
    100: '#CCFBF1',
    500: '#0D9488',
    600: '#0B7C72',
    700: '#096B5C',
  },
  neutral: {
    50: '#FAFAFA',
    100: '#F5F5F5',
    200: '#E5E5E5',
    500: '#737373',
    700: '#404040',
    900: '#171717',
  },
  semantic: {
    error: '#DC2626',
    warning: '#F59E0B',
    success: '#16A34A',
    info: '#2563EB',
  },
} as const;

export const typography = {
  fontFamily: 'Inter',
  sizes: {
    xs: 12,
    sm: 14,
    base: 16,
    lg: 18,
    xl: 20,
    '2xl': 24,
    '3xl': 30,
  },
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  '2xl': 48,
} as const;

export const highContrastColors = {
  primary: { 600: '#CC4400', 700: '#993300' },
  accent: { 500: '#0A7A70', 600: '#065F58' },
  text: { primary: '#000000', secondary: '#1A1A1A' },
  background: { primary: '#FFFFFF', secondary: '#F5F5F5' },
  border: '#000000',
} as const;
