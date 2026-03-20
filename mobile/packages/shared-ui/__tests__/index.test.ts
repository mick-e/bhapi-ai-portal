import { UI_VERSION } from '../src';

describe('shared-ui', () => {
  test('exports version 0.2.0', () => {
    expect(UI_VERSION).toBe('0.2.0');
  });
});
