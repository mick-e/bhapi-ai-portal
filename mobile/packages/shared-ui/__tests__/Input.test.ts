import { inputStyles } from '../src/Input';
import { colors } from '@bhapi/config';

describe('Input', () => {
  test('has 48px height', () => {
    expect(inputStyles.height).toBe(48);
  });

  test('meets WCAG 44pt minimum', () => {
    expect(inputStyles.minHeight).toBeGreaterThanOrEqual(44);
  });

  test('has 8px border radius', () => {
    expect(inputStyles.borderRadius).toBe(8);
  });

  test('error state uses semantic error color', () => {
    expect(inputStyles.errorBorderColor).toBe(colors.semantic.error);
  });
});
