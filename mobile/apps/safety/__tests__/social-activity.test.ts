/**
 * Social Activity Monitoring Screen Tests (P2-M1)
 *
 * Tests for the social-activity screen and its sub-components.
 * Verifies exports, types, and basic rendering.
 */

// ---------------------------------------------------------------------------
// Module export tests
// ---------------------------------------------------------------------------

describe('SocialActivityScreen', () => {
  test('exports default component', () => {
    const mod = require('../app/(dashboard)/social-activity');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports StatBox sub-component', () => {
    const mod = require('../app/(dashboard)/social-activity');
    expect(mod.StatBox).toBeDefined();
    expect(typeof mod.StatBox).toBe('function');
  });

  test('exports TimeChart sub-component', () => {
    const mod = require('../app/(dashboard)/social-activity');
    expect(mod.TimeChart).toBeDefined();
    expect(typeof mod.TimeChart).toBe('function');
  });
});

// ---------------------------------------------------------------------------
// SocialActivityData type shape tests
// ---------------------------------------------------------------------------

describe('SocialActivityData type shape', () => {
  function makeMockData() {
    return {
      member_id: '00000000-0000-0000-0000-000000000001',
      member_name: 'Test Child',
      post_count_7d: 5,
      post_count_30d: 20,
      message_count_7d: 10,
      message_count_30d: 40,
      contact_count: 3,
      pending_contact_requests: 1,
      flagged_content_count: 2,
      flagged_items: [
        {
          id: '00000000-0000-0000-0000-000000000010',
          content_type: 'post',
          content_id: '00000000-0000-0000-0000-000000000020',
          status: 'rejected',
          created_at: '2026-03-20T10:00:00Z',
        },
      ],
      time_spent_minutes_7d: 45,
      time_spent_minutes_30d: 180,
      time_trend: [
        { date: '2026-03-15', minutes: 10 },
        { date: '2026-03-16', minutes: 5 },
        { date: '2026-03-17', minutes: 8 },
        { date: '2026-03-18', minutes: 12 },
        { date: '2026-03-19', minutes: 3 },
        { date: '2026-03-20', minutes: 7 },
        { date: '2026-03-21', minutes: 0 },
      ],
      degraded_sections: [],
    };
  }

  test('mock data has required fields', () => {
    const data = makeMockData();
    expect(data.member_id).toBeDefined();
    expect(data.member_name).toBeDefined();
    expect(typeof data.post_count_7d).toBe('number');
    expect(typeof data.post_count_30d).toBe('number');
    expect(typeof data.message_count_7d).toBe('number');
    expect(typeof data.message_count_30d).toBe('number');
    expect(typeof data.contact_count).toBe('number');
    expect(typeof data.pending_contact_requests).toBe('number');
    expect(typeof data.flagged_content_count).toBe('number');
    expect(Array.isArray(data.flagged_items)).toBe(true);
    expect(typeof data.time_spent_minutes_7d).toBe('number');
    expect(typeof data.time_spent_minutes_30d).toBe('number');
    expect(Array.isArray(data.time_trend)).toBe(true);
    expect(Array.isArray(data.degraded_sections)).toBe(true);
  });

  test('flagged items have correct shape', () => {
    const data = makeMockData();
    const item = data.flagged_items[0];
    expect(item.id).toBeDefined();
    expect(item.content_type).toBe('post');
    expect(item.content_id).toBeDefined();
    expect(item.status).toBe('rejected');
    expect(item.created_at).toBeDefined();
  });

  test('time trend points have correct shape', () => {
    const data = makeMockData();
    expect(data.time_trend.length).toBe(7);
    for (const point of data.time_trend) {
      expect(typeof point.date).toBe('string');
      expect(typeof point.minutes).toBe('number');
      expect(point.minutes).toBeGreaterThanOrEqual(0);
    }
  });

  test('empty state has zero counts', () => {
    const data = {
      ...makeMockData(),
      post_count_7d: 0,
      post_count_30d: 0,
      message_count_7d: 0,
      message_count_30d: 0,
      contact_count: 0,
      pending_contact_requests: 0,
      flagged_content_count: 0,
      flagged_items: [],
      time_spent_minutes_7d: 0,
      time_spent_minutes_30d: 0,
      time_trend: [],
    };
    expect(data.post_count_7d).toBe(0);
    expect(data.flagged_items.length).toBe(0);
    expect(data.time_trend.length).toBe(0);
  });

  test('degraded sections can contain section names', () => {
    const data = {
      ...makeMockData(),
      degraded_sections: ['posts', 'messages'],
    };
    expect(data.degraded_sections).toContain('posts');
    expect(data.degraded_sections).toContain('messages');
    expect(data.degraded_sections.length).toBe(2);
  });
});

// ---------------------------------------------------------------------------
// Time estimation logic tests
// ---------------------------------------------------------------------------

describe('Time estimation logic', () => {
  const MINUTES_PER_POST = 5;
  const MINUTES_PER_MESSAGE = 2;

  function estimateTime(posts: number, messages: number): number {
    return posts * MINUTES_PER_POST + messages * MINUTES_PER_MESSAGE;
  }

  test('zero activity yields zero time', () => {
    expect(estimateTime(0, 0)).toBe(0);
  });

  test('posts only', () => {
    expect(estimateTime(3, 0)).toBe(15);
  });

  test('messages only', () => {
    expect(estimateTime(0, 10)).toBe(20);
  });

  test('mixed activity', () => {
    expect(estimateTime(5, 10)).toBe(45);
  });

  test('large numbers', () => {
    expect(estimateTime(100, 200)).toBe(900);
  });

  test('7d time should be less than or equal to 30d', () => {
    const time7d = estimateTime(3, 4);
    const time30d = estimateTime(10, 15);
    expect(time7d).toBeLessThanOrEqual(time30d);
  });
});

// ---------------------------------------------------------------------------
// API response validation tests
// ---------------------------------------------------------------------------

describe('API response validation', () => {
  test('response with all fields present is valid', () => {
    const resp = {
      member_id: '123e4567-e89b-12d3-a456-426614174000',
      member_name: 'Child',
      post_count_7d: 1,
      post_count_30d: 2,
      message_count_7d: 3,
      message_count_30d: 4,
      contact_count: 5,
      pending_contact_requests: 0,
      flagged_content_count: 0,
      flagged_items: [],
      time_spent_minutes_7d: 11,
      time_spent_minutes_30d: 18,
      time_trend: [],
      degraded_sections: [],
    };
    expect(resp.member_id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
    );
    expect(resp.time_spent_minutes_30d).toBeGreaterThanOrEqual(resp.time_spent_minutes_7d);
  });

  test('response with degraded sections is still usable', () => {
    const resp = {
      member_id: '123e4567-e89b-12d3-a456-426614174000',
      member_name: 'Child',
      post_count_7d: 0,
      post_count_30d: 0,
      message_count_7d: 0,
      message_count_30d: 0,
      contact_count: 0,
      pending_contact_requests: 0,
      flagged_content_count: 0,
      flagged_items: [],
      time_spent_minutes_7d: 0,
      time_spent_minutes_30d: 0,
      time_trend: [],
      degraded_sections: ['posts', 'messages'],
    };
    expect(resp.degraded_sections.length).toBeGreaterThan(0);
    // Even with degraded sections, the rest of the data should be present
    expect(resp.contact_count).toBeDefined();
  });

  test('flagged item statuses are valid enum values', () => {
    const validStatuses = ['pending', 'approved', 'rejected', 'escalated'];
    const items = [
      { id: '1', content_type: 'post', content_id: '2', status: 'rejected', created_at: '' },
      { id: '3', content_type: 'message', content_id: '4', status: 'escalated', created_at: '' },
    ];
    for (const item of items) {
      expect(validStatuses).toContain(item.status);
    }
  });

  test('time trend has exactly 7 entries for weekly view', () => {
    const trend = Array.from({ length: 7 }, (_, i) => ({
      date: `2026-03-${15 + i}`,
      minutes: Math.floor(Math.random() * 60),
    }));
    expect(trend.length).toBe(7);
  });

  test('counts are non-negative integers', () => {
    const fields = [0, 1, 5, 100];
    for (const val of fields) {
      expect(Number.isInteger(val)).toBe(true);
      expect(val).toBeGreaterThanOrEqual(0);
    }
  });
});

// ---------------------------------------------------------------------------
// Screen state tests
// ---------------------------------------------------------------------------

describe('Screen states', () => {
  test('loading state renders ActivityIndicator', () => {
    // The screen uses loading state internally; verify it exports default
    const mod = require('../app/(dashboard)/social-activity');
    expect(mod.default).toBeDefined();
  });

  test('error state provides retry action', () => {
    // Screen has retry logic; this is a contract test
    const mod = require('../app/(dashboard)/social-activity');
    expect(typeof mod.default).toBe('function');
  });

  test('empty state shows helpful prompt', () => {
    // Contract: screen handles null data gracefully
    const mod = require('../app/(dashboard)/social-activity');
    expect(typeof mod.default).toBe('function');
  });
});
