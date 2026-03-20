import { cardStyles } from '../src/Card';
import { spacing } from '@bhapi/config';

describe('Card', () => {
  test('has white background', () => {
    expect(cardStyles.backgroundColor).toBe('#FFFFFF');
  });

  test('has 8px border radius', () => {
    expect(cardStyles.borderRadius).toBe(8);
  });

  test('uses md spacing for padding', () => {
    expect(cardStyles.padding).toBe(spacing.md);
  });
});
