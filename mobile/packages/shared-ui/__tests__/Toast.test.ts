import { toastColors, getToastAutoDismissMs } from '../src/Toast';
import { colors } from '@bhapi/config';

describe('Toast', () => {
  test('success variant uses semantic success bg', () => {
    expect(toastColors.success.bg).toBe(colors.semantic.success);
    expect(toastColors.success.text).toBe('#FFFFFF');
  });

  test('error variant uses semantic error bg', () => {
    expect(toastColors.error.bg).toBe(colors.semantic.error);
    expect(toastColors.error.text).toBe('#FFFFFF');
  });

  test('info variant uses semantic info bg', () => {
    expect(toastColors.info.bg).toBe(colors.semantic.info);
    expect(toastColors.info.text).toBe('#FFFFFF');
  });

  test('warning variant uses semantic warning bg', () => {
    expect(toastColors.warning.bg).toBe(colors.semantic.warning);
    expect(toastColors.warning.text).toBe('#000000');
  });

  test('default auto-dismiss is 3000ms', () => {
    expect(getToastAutoDismissMs()).toBe(3000);
  });

  test('custom duration is respected', () => {
    expect(getToastAutoDismissMs(5000)).toBe(5000);
  });

  test('zero duration is valid', () => {
    expect(getToastAutoDismissMs(0)).toBe(0);
  });
});
