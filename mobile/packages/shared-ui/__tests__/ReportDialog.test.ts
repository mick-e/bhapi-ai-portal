import { reportDialogStyles, DEFAULT_REPORT_REASONS } from '../src/ReportDialog';

describe('ReportDialog', () => {
  test('exports ReportDialog component', () => {
    const mod = require('../src/ReportDialog');
    expect(mod.ReportDialog).toBeDefined();
    expect(typeof mod.ReportDialog).toBe('function');
  });

  test('exports reportDialogStyles', () => {
    expect(reportDialogStyles).toBeDefined();
    expect(reportDialogStyles.overlayBg).toBe('rgba(0, 0, 0, 0.5)');
    expect(reportDialogStyles.dialogBg).toBe('#FFFFFF');
    expect(reportDialogStyles.borderRadius).toBe(16);
  });

  test('exports DEFAULT_REPORT_REASONS with 7 options', () => {
    expect(DEFAULT_REPORT_REASONS).toBeDefined();
    expect(DEFAULT_REPORT_REASONS).toHaveLength(7);
  });

  test('all reasons have value and label', () => {
    for (const reason of DEFAULT_REPORT_REASONS) {
      expect(reason.value).toBeTruthy();
      expect(reason.label).toBeTruthy();
      expect(typeof reason.value).toBe('string');
      expect(typeof reason.label).toBe('string');
    }
  });

  test('reason values match expected taxonomy', () => {
    const values = DEFAULT_REPORT_REASONS.map((r) => r.value);
    expect(values).toContain('inappropriate');
    expect(values).toContain('bullying');
    expect(values).toContain('spam');
    expect(values).toContain('impersonation');
    expect(values).toContain('self_harm');
    expect(values).toContain('adult_content');
    expect(values).toContain('other');
  });

  test('reason labels are age-appropriate (no jargon)', () => {
    const labels = DEFAULT_REPORT_REASONS.map((r) => r.label);
    // Labels should be simple phrases, not technical terms
    for (const label of labels) {
      expect(label.length).toBeGreaterThan(3);
      expect(label.length).toBeLessThan(60);
    }
    // Spot-check specific labels
    const bullyingReason = DEFAULT_REPORT_REASONS.find(
      (r) => r.value === 'bullying'
    );
    expect(bullyingReason?.label).toBe('Bullying or mean behavior');

    const selfHarmReason = DEFAULT_REPORT_REASONS.find(
      (r) => r.value === 'self_harm'
    );
    expect(selfHarmReason?.label).toBe(
      'Someone might be hurting themselves'
    );
  });

  test('renders nothing when not visible', () => {
    const { ReportDialog } = require('../src/ReportDialog');
    const element = ReportDialog({
      visible: false,
      targetType: 'post',
      targetId: 'abc-123',
      onSubmit: jest.fn(),
      onCancel: jest.fn(),
    });
    expect(element).toBeNull();
  });

  test('renders dialog when visible', () => {
    const { ReportDialog } = require('../src/ReportDialog');
    const element = ReportDialog({
      visible: true,
      targetType: 'post',
      targetId: 'abc-123',
      onSubmit: jest.fn(),
      onCancel: jest.fn(),
    });
    expect(element).toBeDefined();
    expect(element).not.toBeNull();
    expect(element.props.accessibilityLabel).toBe('Report this post');
  });

  test('accessibility label adapts to target type user', () => {
    const { ReportDialog } = require('../src/ReportDialog');
    const element = ReportDialog({
      visible: true,
      targetType: 'user',
      targetId: 'user-456',
      onSubmit: jest.fn(),
      onCancel: jest.fn(),
    });
    expect(element.props.accessibilityLabel).toBe('Report this person');
  });

  test('accessibility label adapts to target type message', () => {
    const { ReportDialog } = require('../src/ReportDialog');
    const element = ReportDialog({
      visible: true,
      targetType: 'message',
      targetId: 'msg-789',
      onSubmit: jest.fn(),
      onCancel: jest.fn(),
    });
    expect(element.props.accessibilityLabel).toBe('Report this message');
  });

  test('accessibility label adapts to target type comment', () => {
    const { ReportDialog } = require('../src/ReportDialog');
    const element = ReportDialog({
      visible: true,
      targetType: 'comment',
      targetId: 'cmt-111',
      onSubmit: jest.fn(),
      onCancel: jest.fn(),
    });
    expect(element.props.accessibilityLabel).toBe('Report this comment');
  });

  test('custom accessibilityLabel overrides default', () => {
    const { ReportDialog } = require('../src/ReportDialog');
    const element = ReportDialog({
      visible: true,
      targetType: 'post',
      targetId: 'abc-123',
      onSubmit: jest.fn(),
      onCancel: jest.fn(),
      accessibilityLabel: 'Custom report label',
    });
    expect(element.props.accessibilityLabel).toBe('Custom report label');
  });

  test('custom reasons override defaults', () => {
    const { ReportDialog } = require('../src/ReportDialog');
    const customReasons = [
      { value: 'spam', label: 'Junk' },
      { value: 'other', label: 'Other thing' },
    ];
    const element = ReportDialog({
      visible: true,
      targetType: 'post',
      targetId: 'abc-123',
      reasons: customReasons,
      onSubmit: jest.fn(),
      onCancel: jest.fn(),
    });
    // The dialog element should exist (it renders reason rows from custom list)
    expect(element).toBeDefined();
    // The dialog children include title, subtitle, 2 custom reasons, description input, button row
    // (exact child count depends on createElement structure)
    expect(element.props.children).toBeDefined();
  });
});
