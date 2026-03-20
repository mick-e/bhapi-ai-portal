import { logoSizes } from '../src/BhapiLogo';

describe('BhapiLogo', () => {
  test('sm size is 80x28', () => {
    expect(logoSizes.sm).toEqual({ width: 80, height: 28 });
  });

  test('md size is 120x42', () => {
    expect(logoSizes.md).toEqual({ width: 120, height: 42 });
  });

  test('lg size is 180x63', () => {
    expect(logoSizes.lg).toEqual({ width: 180, height: 63 });
  });

  test('all sizes maintain consistent aspect ratio', () => {
    const smRatio = logoSizes.sm.width / logoSizes.sm.height;
    const mdRatio = logoSizes.md.width / logoSizes.md.height;
    const lgRatio = logoSizes.lg.width / logoSizes.lg.height;
    // All should be approximately 2.857:1
    expect(Math.abs(smRatio - mdRatio)).toBeLessThan(0.01);
    expect(Math.abs(mdRatio - lgRatio)).toBeLessThan(0.01);
  });
});
