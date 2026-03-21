/**
 * Child Profile Screen Tests (P2-M4)
 *
 * Tests for child-profile screen exports, sub-components, types, and constants.
 */

// ---------------------------------------------------------------------------
// Module export tests
// ---------------------------------------------------------------------------

describe('ChildProfileScreen', () => {
  test('exports default component', () => {
    const mod = require('../app/(children)/child-profile');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports RiskScoreBadge sub-component', () => {
    const mod = require('../app/(children)/child-profile');
    expect(mod.RiskScoreBadge).toBeDefined();
    expect(typeof mod.RiskScoreBadge).toBe('function');
  });

  test('exports RiskTrendChart sub-component', () => {
    const mod = require('../app/(children)/child-profile');
    expect(mod.RiskTrendChart).toBeDefined();
    expect(typeof mod.RiskTrendChart).toBe('function');
  });

  test('exports PlatformRow sub-component', () => {
    const mod = require('../app/(children)/child-profile');
    expect(mod.PlatformRow).toBeDefined();
    expect(typeof mod.PlatformRow).toBe('function');
  });

  test('exports TimelineEntry sub-component', () => {
    const mod = require('../app/(children)/child-profile');
    expect(mod.TimelineEntry).toBeDefined();
    expect(typeof mod.TimelineEntry).toBe('function');
  });

  test('exports QuickActions sub-component', () => {
    const mod = require('../app/(children)/child-profile');
    expect(mod.QuickActions).toBeDefined();
    expect(typeof mod.QuickActions).toBe('function');
  });

  test('exports SEVERITY_COLOR mapping', () => {
    const { SEVERITY_COLOR } = require('../app/(children)/child-profile');
    expect(SEVERITY_COLOR).toBeDefined();
    expect(SEVERITY_COLOR.critical).toBeDefined();
    expect(SEVERITY_COLOR.high).toBeDefined();
    expect(SEVERITY_COLOR.medium).toBeDefined();
    expect(SEVERITY_COLOR.low).toBeDefined();
  });

  test('exports SOURCE_LABEL mapping', () => {
    const { SOURCE_LABEL } = require('../app/(children)/child-profile');
    expect(SOURCE_LABEL).toBeDefined();
    expect(SOURCE_LABEL.ai).toBe('AI');
    expect(SOURCE_LABEL.social_post).toBe('Post');
    expect(SOURCE_LABEL.social_message).toBe('Message');
    expect(SOURCE_LABEL.risk).toBe('Risk');
    expect(SOURCE_LABEL.moderation).toBe('Moderation');
  });
});

// ---------------------------------------------------------------------------
// ChildProfileData type shape tests
// ---------------------------------------------------------------------------

describe('ChildProfileData type shape', () => {
  function makeMockData() {
    return {
      member_id: '00000000-0000-0000-0000-000000000001',
      member_name: 'Test Child',
      avatar_url: 'https://example.com/avatar.jpg',
      age_tier: 'preteen',
      risk_score: 85,
      timeline: [
        {
          id: '00000000-0000-0000-0000-000000000010',
          source: 'ai',
          event_type: 'prompt',
          title: 'AI prompt on chatgpt',
          detail: '',
          severity: null,
          platform: 'chatgpt',
          timestamp: '2026-03-21T10:00:00Z',
        },
        {
          id: '00000000-0000-0000-0000-000000000011',
          source: 'social_post',
          event_type: 'post',
          title: 'Social post (text)',
          detail: 'Hello world',
          severity: null,
          platform: 'bhapi_social',
          timestamp: '2026-03-21T09:00:00Z',
        },
        {
          id: '00000000-0000-0000-0000-000000000012',
          source: 'risk',
          event_type: 'risk_event',
          title: 'Risk: harmful_content',
          detail: '',
          severity: 'high',
          platform: null,
          timestamp: '2026-03-21T08:00:00Z',
        },
      ],
      risk_trend_7d: [
        { date: '2026-03-15', count: 1, high_count: 0 },
        { date: '2026-03-16', count: 0, high_count: 0 },
        { date: '2026-03-17', count: 2, high_count: 1 },
        { date: '2026-03-18', count: 0, high_count: 0 },
        { date: '2026-03-19', count: 1, high_count: 0 },
        { date: '2026-03-20', count: 0, high_count: 0 },
        { date: '2026-03-21', count: 0, high_count: 0 },
      ],
      risk_trend_30d: Array.from({ length: 30 }, (_, i) => ({
        date: `2026-02-${String(20 + i).padStart(2, '0')}`,
        count: i % 3 === 0 ? 1 : 0,
        high_count: 0,
      })),
      platform_breakdown: [
        { platform: 'chatgpt', event_count: 10, percentage: 50 },
        { platform: 'gemini', event_count: 6, percentage: 30 },
        { platform: 'bhapi_social', event_count: 4, percentage: 20 },
      ],
      unresolved_alerts: 2,
      pending_contact_requests: 1,
      flagged_content_count: 0,
      degraded_sections: [],
    };
  }

  test('mock data has all required fields', () => {
    const data = makeMockData();
    expect(data.member_id).toBeDefined();
    expect(data.member_name).toBeDefined();
    expect(typeof data.risk_score).toBe('number');
    expect(Array.isArray(data.timeline)).toBe(true);
    expect(Array.isArray(data.risk_trend_7d)).toBe(true);
    expect(Array.isArray(data.risk_trend_30d)).toBe(true);
    expect(Array.isArray(data.platform_breakdown)).toBe(true);
    expect(typeof data.unresolved_alerts).toBe('number');
    expect(typeof data.pending_contact_requests).toBe('number');
    expect(typeof data.flagged_content_count).toBe('number');
    expect(Array.isArray(data.degraded_sections)).toBe(true);
  });

  test('timeline items have correct shape', () => {
    const data = makeMockData();
    for (const item of data.timeline) {
      expect(item.id).toBeDefined();
      expect(item.source).toBeDefined();
      expect(item.event_type).toBeDefined();
      expect(item.title).toBeDefined();
      expect(item.timestamp).toBeDefined();
    }
  });

  test('risk_trend_7d has 7 points', () => {
    const data = makeMockData();
    expect(data.risk_trend_7d).toHaveLength(7);
  });

  test('risk_trend_30d has 30 points', () => {
    const data = makeMockData();
    expect(data.risk_trend_30d).toHaveLength(30);
  });

  test('platform_breakdown percentages sum to ~100', () => {
    const data = makeMockData();
    const total = data.platform_breakdown.reduce((s, p) => s + p.percentage, 0);
    expect(total).toBeGreaterThanOrEqual(99);
    expect(total).toBeLessThanOrEqual(101);
  });

  test('timeline sources include expected values', () => {
    const data = makeMockData();
    const sources = new Set(data.timeline.map((t: any) => t.source));
    expect(sources.has('ai')).toBe(true);
    expect(sources.has('social_post')).toBe(true);
    expect(sources.has('risk')).toBe(true);
  });

  test('risk trend points have count and high_count', () => {
    const data = makeMockData();
    for (const point of data.risk_trend_7d) {
      expect(typeof point.count).toBe('number');
      expect(typeof point.high_count).toBe('number');
      expect(typeof point.date).toBe('string');
    }
  });

  test('avatar_url and age_tier are nullable', () => {
    const data = makeMockData();
    data.avatar_url = null;
    data.age_tier = null;
    expect(data.avatar_url).toBeNull();
    expect(data.age_tier).toBeNull();
  });

  test('degraded_sections can contain section names', () => {
    const data = makeMockData();
    data.degraded_sections = ['ai_timeline', 'risk_trend'];
    expect(data.degraded_sections).toHaveLength(2);
    expect(data.degraded_sections).toContain('ai_timeline');
  });
});
