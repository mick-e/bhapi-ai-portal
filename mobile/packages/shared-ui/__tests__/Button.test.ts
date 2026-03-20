import { getButtonStyles } from '../src/Button';
import { colors, typography } from '@bhapi/config';

describe('Button', () => {
  describe('getButtonStyles', () => {
    test('primary variant has correct background color', () => {
      const styles = getButtonStyles('primary', 'md', false);
      expect(styles.container.bg).toBe(colors.primary[600]);
    });

    test('primary variant text is white', () => {
      const styles = getButtonStyles('primary', 'md', false);
      expect(styles.text.color).toBe('#FFFFFF');
    });

    test('secondary variant uses accent color', () => {
      const styles = getButtonStyles('secondary', 'md', false);
      expect(styles.container.bg).toBe(colors.accent[500]);
    });

    test('secondary variant text is white', () => {
      const styles = getButtonStyles('secondary', 'md', false);
      expect(styles.text.color).toBe('#FFFFFF');
    });

    test('outline variant has transparent background', () => {
      const styles = getButtonStyles('outline', 'md', false);
      expect(styles.container.bg).toBe('transparent');
    });

    test('outline variant text uses primary-700', () => {
      const styles = getButtonStyles('outline', 'md', false);
      expect(styles.text.color).toBe(colors.primary[700]);
    });

    test('outline variant has border color', () => {
      const styles = getButtonStyles('outline', 'md', false);
      expect(styles.container.border).toBe(colors.primary[600]);
    });

    test('sm size meets WCAG 44pt minimum', () => {
      const styles = getButtonStyles('primary', 'sm', false);
      expect(styles.container.minHeight).toBeGreaterThanOrEqual(44);
    });

    test('md size has 48 height', () => {
      const styles = getButtonStyles('primary', 'md', false);
      expect(styles.container.height).toBe(48);
    });

    test('lg size has 56 height', () => {
      const styles = getButtonStyles('primary', 'lg', false);
      expect(styles.container.height).toBe(56);
    });

    test('sm size uses sm font', () => {
      const styles = getButtonStyles('primary', 'sm', false);
      expect(styles.text.fontSize).toBe(typography.sizes.sm);
    });

    test('md size uses base font', () => {
      const styles = getButtonStyles('primary', 'md', false);
      expect(styles.text.fontSize).toBe(typography.sizes.base);
    });

    test('lg size uses lg font', () => {
      const styles = getButtonStyles('primary', 'lg', false);
      expect(styles.text.fontSize).toBe(typography.sizes.lg);
    });

    test('disabled state has 0.5 opacity', () => {
      const styles = getButtonStyles('primary', 'md', true);
      expect(styles.container.opacity).toBe(0.5);
    });

    test('enabled state has full opacity', () => {
      const styles = getButtonStyles('primary', 'md', false);
      expect(styles.container.opacity).toBe(1);
    });
  });
});
