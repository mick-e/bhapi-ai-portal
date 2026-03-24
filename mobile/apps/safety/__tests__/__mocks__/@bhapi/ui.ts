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
export const RiskScoreCard = noop;
export const ModerationNotice = noop;
export const TrustedAdultButton = noop;
export const ReportDialog = noop;
export const CreativeToolbar = jest.fn((props: any) => ({
  type: 'CreativeToolbar',
  props,
}));
export const StickerGrid = jest.fn((props: any) => ({
  type: 'StickerGrid',
  props,
}));
export const PRESET_COLORS = [
  { label: 'Red', value: '#EF4444' },
  { label: 'Orange', value: '#F97316' },
  { label: 'Yellow', value: '#EAB308' },
  { label: 'Green', value: '#22C55E' },
  { label: 'Blue', value: '#3B82F6' },
  { label: 'Purple', value: '#A855F7' },
  { label: 'Pink', value: '#EC4899' },
  { label: 'Black', value: '#1F2937' },
];
export const SIZE_PRESETS = [
  { label: 'Thin', value: 'thin', diameter: 4 },
  { label: 'Medium', value: 'medium', diameter: 8 },
  { label: 'Thick', value: 'thick', diameter: 14 },
];
export const STICKER_CATEGORIES = [
  { label: 'Bhapi', value: 'branded' },
  { label: 'Seasonal', value: 'seasonal' },
  { label: 'Learn', value: 'educational' },
  { label: 'Mine', value: 'my_stickers' },
];
export const creativeToolbarStyles = { height: 88, borderTopWidth: 1 };
export const stickerGridStyles = { tabHeight: 40, itemSize: 72 };
export const UI_VERSION = '0.5.0';
