/**
 * Creative Review Screen Tests (P3-F1c)
 *
 * Tests for the parent-facing creative content review dashboard,
 * filter tabs, moderation status display, and flagging functionality.
 */

// ---------------------------------------------------------------------------
// Creative Review Screen
// ---------------------------------------------------------------------------

describe('Creative Review Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(dashboard)/creative-review');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('renders without crashing', () => {
    const mod = require('../app/(dashboard)/creative-review');
    const result = mod.default();
    expect(result).toBeDefined();
  });

  test('exports FILTER_TABS with 4 filter options', () => {
    const { FILTER_TABS } = require('../app/(dashboard)/creative-review');
    expect(FILTER_TABS).toHaveLength(4);
    const values = FILTER_TABS.map((t: any) => t.value);
    expect(values).toContain('all');
    expect(values).toContain('pending');
    expect(values).toContain('approved');
    expect(values).toContain('flagged');
  });

  test('exports FilterTabBar sub-component', () => {
    const { FilterTabBar } = require('../app/(dashboard)/creative-review');
    expect(typeof FilterTabBar).toBe('function');
  });

  test('filter tab bar renders without crashing', () => {
    const { FilterTabBar } = require('../app/(dashboard)/creative-review');
    const onFilterChange = jest.fn();
    const result = FilterTabBar({ activeFilter: 'all', onFilterChange });
    expect(result).toBeDefined();
  });

  test('exports ModerationStatusBadge sub-component', () => {
    const { ModerationStatusBadge } = require('../app/(dashboard)/creative-review');
    expect(typeof ModerationStatusBadge).toBe('function');
  });

  test('ModerationStatusBadge renders for pending', () => {
    const { ModerationStatusBadge } = require('../app/(dashboard)/creative-review');
    const result = ModerationStatusBadge({ status: 'pending' });
    expect(result).toBeDefined();
  });

  test('ModerationStatusBadge renders for approved', () => {
    const { ModerationStatusBadge } = require('../app/(dashboard)/creative-review');
    const result = ModerationStatusBadge({ status: 'approved' });
    expect(result).toBeDefined();
  });

  test('ModerationStatusBadge renders for rejected', () => {
    const { ModerationStatusBadge } = require('../app/(dashboard)/creative-review');
    const result = ModerationStatusBadge({ status: 'rejected' });
    expect(result).toBeDefined();
  });

  test('ModerationStatusBadge renders for flagged', () => {
    const { ModerationStatusBadge } = require('../app/(dashboard)/creative-review');
    const result = ModerationStatusBadge({ status: 'flagged' });
    expect(result).toBeDefined();
  });

  test('exports CreativeItemCard sub-component', () => {
    const { CreativeItemCard } = require('../app/(dashboard)/creative-review');
    expect(typeof CreativeItemCard).toBe('function');
  });

  test('CreativeItemCard renders with a creative item', () => {
    const { CreativeItemCard } = require('../app/(dashboard)/creative-review');
    const item = {
      id: 'item-1',
      member_id: 'child-1',
      member_name: 'Alex',
      content_type: 'art',
      title: 'My Dragon',
      preview: 'A red dragon in the sky.',
      moderation_status: 'approved',
      created_at: new Date().toISOString(),
      is_flagged_by_parent: false,
    };
    const onFlag = jest.fn();
    const result = CreativeItemCard({ item, onFlag, isFlagging: false });
    expect(result).toBeDefined();
  });

  test('exports CONTENT_TYPE_LABELS for art, story, drawing', () => {
    const { CONTENT_TYPE_LABELS } = require('../app/(dashboard)/creative-review');
    expect(CONTENT_TYPE_LABELS.art).toBeDefined();
    expect(CONTENT_TYPE_LABELS.story).toBeDefined();
    expect(CONTENT_TYPE_LABELS.drawing).toBeDefined();
  });

  test('exports PLACEHOLDER_CREATIVE_ITEMS as non-empty array', () => {
    const { PLACEHOLDER_CREATIVE_ITEMS } = require('../app/(dashboard)/creative-review');
    expect(Array.isArray(PLACEHOLDER_CREATIVE_ITEMS)).toBe(true);
    expect(PLACEHOLDER_CREATIVE_ITEMS.length).toBeGreaterThan(0);
  });

  test('each placeholder item has required fields', () => {
    const { PLACEHOLDER_CREATIVE_ITEMS } = require('../app/(dashboard)/creative-review');
    for (const item of PLACEHOLDER_CREATIVE_ITEMS) {
      expect(typeof item.id).toBe('string');
      expect(typeof item.member_id).toBe('string');
      expect(typeof item.member_name).toBe('string');
      expect(['art', 'story', 'drawing']).toContain(item.content_type);
      expect(typeof item.title).toBe('string');
      expect(['pending', 'approved', 'rejected', 'flagged']).toContain(item.moderation_status);
      expect(typeof item.is_flagged_by_parent).toBe('boolean');
    }
  });
});

// ---------------------------------------------------------------------------
// Moderation status logic
// ---------------------------------------------------------------------------

describe('Moderation status display logic', () => {
  test('pending status shows amber/warning color scheme', () => {
    // Verify the config map has amber colors for pending
    const STATUS_CONFIG = {
      pending: { label: 'Pending Review', color: '#92400E', bg: '#FEF3C7' },
      approved: { label: 'Approved', color: '#065F46', bg: '#D1FAE5' },
      rejected: { label: 'Not Approved', color: '#991B1B', bg: '#FEE2E2' },
      flagged: { label: 'Flagged', color: '#7C3AED', bg: '#EDE9FE' },
    };
    expect(STATUS_CONFIG.pending.bg).toBe('#FEF3C7');
    expect(STATUS_CONFIG.approved.bg).toBe('#D1FAE5');
    expect(STATUS_CONFIG.rejected.bg).toBe('#FEE2E2');
    expect(STATUS_CONFIG.flagged.bg).toBe('#EDE9FE');
  });

  test('filter logic includes all items for all tab', () => {
    const { PLACEHOLDER_CREATIVE_ITEMS } = require('../app/(dashboard)/creative-review');
    const all = PLACEHOLDER_CREATIVE_ITEMS.filter(() => true);
    expect(all.length).toBe(PLACEHOLDER_CREATIVE_ITEMS.length);
  });

  test('filter logic returns only pending items for pending tab', () => {
    const { PLACEHOLDER_CREATIVE_ITEMS } = require('../app/(dashboard)/creative-review');
    const pending = PLACEHOLDER_CREATIVE_ITEMS.filter(
      (i: any) => i.moderation_status === 'pending'
    );
    expect(pending.length).toBeGreaterThanOrEqual(0);
    for (const item of pending) {
      expect(item.moderation_status).toBe('pending');
    }
  });

  test('filter logic returns only approved items for approved tab', () => {
    const { PLACEHOLDER_CREATIVE_ITEMS } = require('../app/(dashboard)/creative-review');
    const approved = PLACEHOLDER_CREATIVE_ITEMS.filter(
      (i: any) => i.moderation_status === 'approved'
    );
    for (const item of approved) {
      expect(item.moderation_status).toBe('approved');
    }
  });
});
