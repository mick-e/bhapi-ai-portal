import { moderationNoticeStyles } from '../src/ModerationNotice';
import { spacing } from '@bhapi/config';

describe('ModerationNotice', () => {
  test('exports ModerationNotice component', () => {
    const mod = require('../src/ModerationNotice');
    expect(mod.ModerationNotice).toBeDefined();
    expect(typeof mod.ModerationNotice).toBe('function');
  });

  test('exports moderationNoticeStyles', () => {
    expect(moderationNoticeStyles).toBeDefined();
    expect(moderationNoticeStyles.borderRadius).toBe(8);
    expect(moderationNoticeStyles.padding).toBe(spacing.md);
  });

  test('returns null for approved status', () => {
    const { ModerationNotice } = require('../src/ModerationNotice');
    const result = ModerationNotice({ status: 'approved' });
    expect(result).toBeNull();
  });

  test('renders pending state with review message', () => {
    const { ModerationNotice } = require('../src/ModerationNotice');
    const element = ModerationNotice({ status: 'pending' });
    expect(element).toBeDefined();
    expect(element.props.accessibilityRole).toBe('alert');
    expect(element.props.accessibilityLabel).toContain('reviewed');
  });

  test('pending state uses yellow background', () => {
    const { ModerationNotice } = require('../src/ModerationNotice');
    const element = ModerationNotice({ status: 'pending' });
    const bgColor = element.props.style.find(
      (s: any) => s && s.backgroundColor
    )?.backgroundColor;
    expect(bgColor).toBe('#FEF3C7');
  });

  test('renders rejected state with message', () => {
    const { ModerationNotice } = require('../src/ModerationNotice');
    const element = ModerationNotice({ status: 'rejected' });
    expect(element).toBeDefined();
    expect(element.props.accessibilityLabel).toContain('not approved');
  });

  test('rejected state uses red background', () => {
    const { ModerationNotice } = require('../src/ModerationNotice');
    const element = ModerationNotice({ status: 'rejected' });
    const bgColor = element.props.style.find(
      (s: any) => s && s.backgroundColor
    )?.backgroundColor;
    expect(bgColor).toBe('#FEE2E2');
  });

  test('renders removed state with message', () => {
    const { ModerationNotice } = require('../src/ModerationNotice');
    const element = ModerationNotice({ status: 'removed' });
    expect(element).toBeDefined();
    expect(element.props.accessibilityLabel).toContain('removed');
  });

  test('removed state uses gray background', () => {
    const { ModerationNotice } = require('../src/ModerationNotice');
    const element = ModerationNotice({ status: 'removed' });
    const bgColor = element.props.style.find(
      (s: any) => s && s.backgroundColor
    )?.backgroundColor;
    expect(bgColor).toBe('#F3F4F6');
  });

  test('displays reason when provided', () => {
    const { ModerationNotice } = require('../src/ModerationNotice');
    const element = ModerationNotice({
      status: 'rejected',
      reason: 'Contains inappropriate language',
    });
    // The element should have children including the reason text
    const children = element.props.children;
    // Find the reason child (non-null text element after headerRow)
    const reasonChild = children.find(
      (c: any) => c && c.props && c.props.accessibilityLabel?.includes('Reason')
    );
    expect(reasonChild).toBeDefined();
  });

  test('shows appeal button for rejected status without prior appeal', () => {
    const onAppeal = jest.fn();
    const { ModerationNotice } = require('../src/ModerationNotice');
    const element = ModerationNotice({
      status: 'rejected',
      hasAppealed: false,
      onAppeal,
    });
    const children = element.props.children;
    const appealButton = children.find(
      (c: any) => c && c.props && c.props.accessibilityLabel === 'Appeal this decision'
    );
    expect(appealButton).toBeDefined();
  });

  test('hides appeal button when hasAppealed is true', () => {
    const onAppeal = jest.fn();
    const { ModerationNotice } = require('../src/ModerationNotice');
    const element = ModerationNotice({
      status: 'rejected',
      hasAppealed: true,
      onAppeal,
    });
    const children = element.props.children;
    const appealButton = children.find(
      (c: any) => c && c.props && c.props.accessibilityLabel === 'Appeal this decision'
    );
    expect(appealButton).toBeFalsy();
  });

  test('shows appealed label when hasAppealed is true', () => {
    const { ModerationNotice } = require('../src/ModerationNotice');
    const element = ModerationNotice({
      status: 'rejected',
      hasAppealed: true,
    });
    const children = element.props.children;
    const appealedLabel = children.find(
      (c: any) => c && c.props && c.props.accessibilityLabel?.includes('appeal has been submitted')
    );
    expect(appealedLabel).toBeDefined();
  });

  test('does not show appeal button for pending status', () => {
    const onAppeal = jest.fn();
    const { ModerationNotice } = require('../src/ModerationNotice');
    const element = ModerationNotice({
      status: 'pending',
      onAppeal,
    });
    const children = element.props.children;
    const appealButton = children.find(
      (c: any) => c && c.props && c.props.accessibilityLabel === 'Appeal this decision'
    );
    expect(appealButton).toBeFalsy();
  });

  test('does not show appeal button for removed status', () => {
    const onAppeal = jest.fn();
    const { ModerationNotice } = require('../src/ModerationNotice');
    const element = ModerationNotice({
      status: 'removed',
      onAppeal,
    });
    const children = element.props.children;
    const appealButton = children.find(
      (c: any) => c && c.props && c.props.accessibilityLabel === 'Appeal this decision'
    );
    expect(appealButton).toBeFalsy();
  });

  test('escalated status renders same as pending', () => {
    const { ModerationNotice } = require('../src/ModerationNotice');
    const element = ModerationNotice({ status: 'escalated' });
    expect(element).toBeDefined();
    const bgColor = element.props.style.find(
      (s: any) => s && s.backgroundColor
    )?.backgroundColor;
    expect(bgColor).toBe('#FEF3C7');
  });

  test('respects custom accessibilityLabel', () => {
    const { ModerationNotice } = require('../src/ModerationNotice');
    const element = ModerationNotice({
      status: 'pending',
      accessibilityLabel: 'Custom label',
    });
    expect(element.props.accessibilityLabel).toBe('Custom label');
  });

  test('respects custom style', () => {
    const { ModerationNotice } = require('../src/ModerationNotice');
    const customStyle = { marginTop: 20 };
    const element = ModerationNotice({
      status: 'pending',
      style: customStyle,
    });
    const styleArray = element.props.style;
    expect(styleArray).toContainEqual(customStyle);
  });

  test('does not show reason when not provided', () => {
    const { ModerationNotice } = require('../src/ModerationNotice');
    const element = ModerationNotice({ status: 'rejected' });
    const children = element.props.children;
    const reasonChild = children.find(
      (c: any) => c && c.props && c.props.accessibilityLabel?.includes('Reason')
    );
    expect(reasonChild).toBeFalsy();
  });

  test('exports from index', () => {
    const mod = require('../src/index');
    expect(mod.ModerationNotice).toBeDefined();
    expect(mod.moderationNoticeStyles).toBeDefined();
  });
});
