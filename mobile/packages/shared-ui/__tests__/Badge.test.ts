import { badgeColors } from '../src/Badge';
import { colors } from '@bhapi/config';

describe('Badge', () => {
  test('info variant has blue background', () => {
    expect(badgeColors.info.bg).toBe('#DBEAFE');
  });

  test('info variant uses semantic info text', () => {
    expect(badgeColors.info.text).toBe(colors.semantic.info);
  });

  test('success variant has green background', () => {
    expect(badgeColors.success.bg).toBe('#DCFCE7');
  });

  test('success variant uses semantic success text', () => {
    expect(badgeColors.success.text).toBe(colors.semantic.success);
  });

  test('warning variant has amber background', () => {
    expect(badgeColors.warning.bg).toBe('#FEF3C7');
  });

  test('warning variant has dark amber text for contrast', () => {
    expect(badgeColors.warning.text).toBe('#92400E');
  });

  test('error variant has red background', () => {
    expect(badgeColors.error.bg).toBe('#FEE2E2');
  });

  test('error variant uses semantic error text', () => {
    expect(badgeColors.error.text).toBe(colors.semantic.error);
  });
});
