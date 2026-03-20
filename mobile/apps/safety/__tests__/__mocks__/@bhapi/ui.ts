const noop = jest.fn((_props: any) => ({
  type: 'MockComponent',
  props: _props,
}));

export const BhapiLogo = noop;
export const Button = noop;
export const Card = jest.fn((props: any) => ({
  type: 'Card',
  props,
}));
export const Input = noop;
export const Badge = noop;
export const Avatar = noop;
export const Toast = noop;
export const UI_VERSION = '0.3.0';
