import { UI_VERSION } from '../src';

describe('shared-ui', () => {
  test('exports version', () => {
    expect(UI_VERSION).toBe('0.1.0');
  });
});
