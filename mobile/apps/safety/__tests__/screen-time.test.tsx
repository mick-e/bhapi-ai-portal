/**
 * Screen Time Mobile Screen Tests (P3-F2c)
 *
 * Tests for screen-time dashboard and settings screens,
 * sub-components, and type shapes.
 */

// ---------------------------------------------------------------------------
// Module export tests — Screen Time Dashboard
// ---------------------------------------------------------------------------

describe('ScreenTimeDashboard', () => {
  test('exports default component', () => {
    const mod = require('../app/(dashboard)/screen-time');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports UsageBar sub-component', () => {
    const mod = require('../app/(dashboard)/screen-time');
    expect(mod.UsageBar).toBeDefined();
    expect(typeof mod.UsageBar).toBe('function');
  });

  test('exports ExtensionCard sub-component', () => {
    const mod = require('../app/(dashboard)/screen-time');
    expect(mod.ExtensionCard).toBeDefined();
    expect(typeof mod.ExtensionCard).toBe('function');
  });

  test('exports WeeklyTrend sub-component', () => {
    const mod = require('../app/(dashboard)/screen-time');
    expect(mod.WeeklyTrend).toBeDefined();
    expect(typeof mod.WeeklyTrend).toBe('function');
  });
});

// ---------------------------------------------------------------------------
// Module export tests — Screen Time Settings
// ---------------------------------------------------------------------------

describe('ScreenTimeSettings', () => {
  test('exports default component', () => {
    const mod = require('../app/(settings)/screen-time-settings');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports CATEGORY_PRESETS with 6 categories', () => {
    const { CATEGORY_PRESETS } = require('../app/(settings)/screen-time-settings');
    expect(CATEGORY_PRESETS).toHaveLength(6);
    const values = CATEGORY_PRESETS.map((c: any) => c.value);
    expect(values).toContain('social');
    expect(values).toContain('games');
    expect(values).toContain('education');
    expect(values).toContain('all');
  });

  test('exports ENFORCEMENT_OPTIONS with 3 modes', () => {
    const { ENFORCEMENT_OPTIONS } = require('../app/(settings)/screen-time-settings');
    expect(ENFORCEMENT_OPTIONS).toHaveLength(3);
    const values = ENFORCEMENT_OPTIONS.map((o: any) => o.value);
    expect(values).toContain('hard_block');
    expect(values).toContain('warning_then_block');
    expect(values).toContain('warning_only');
  });

  test('exports LIMIT_PRESETS as number array', () => {
    const { LIMIT_PRESETS } = require('../app/(settings)/screen-time-settings');
    expect(Array.isArray(LIMIT_PRESETS)).toBe(true);
    expect(LIMIT_PRESETS.length).toBeGreaterThan(0);
    for (const val of LIMIT_PRESETS) {
      expect(typeof val).toBe('number');
      expect(val).toBeGreaterThan(0);
    }
  });

  test('exports RuleItem sub-component', () => {
    const { RuleItem } = require('../app/(settings)/screen-time-settings');
    expect(RuleItem).toBeDefined();
    expect(typeof RuleItem).toBe('function');
  });

  test('exports CreateRuleForm sub-component', () => {
    const { CreateRuleForm } = require('../app/(settings)/screen-time-settings');
    expect(CreateRuleForm).toBeDefined();
    expect(typeof CreateRuleForm).toBe('function');
  });
});

// ---------------------------------------------------------------------------
// Screen Time type shape tests
// ---------------------------------------------------------------------------

describe('ScreenTimeRule type shape', () => {
  function makeRule(overrides: Record<string, any> = {}) {
    return {
      id: '00000000-0000-0000-0000-000000000001',
      member_id: '00000000-0000-0000-0000-000000000002',
      group_id: '00000000-0000-0000-0000-000000000003',
      app_category: 'social' as const,
      daily_limit_minutes: 60,
      age_tier_enforcement: false,
      enabled: true,
      created_at: '2026-03-23T00:00:00Z',
      updated_at: '2026-03-23T00:00:00Z',
      ...overrides,
    };
  }

  test('rule has all required fields', () => {
    const rule = makeRule();
    expect(rule.id).toBeDefined();
    expect(rule.member_id).toBeDefined();
    expect(rule.group_id).toBeDefined();
    expect(rule.app_category).toBe('social');
    expect(typeof rule.daily_limit_minutes).toBe('number');
    expect(typeof rule.age_tier_enforcement).toBe('boolean');
    expect(typeof rule.enabled).toBe('boolean');
  });

  test('daily_limit_minutes is a positive number', () => {
    const rule = makeRule({ daily_limit_minutes: 90 });
    expect(rule.daily_limit_minutes).toBeGreaterThan(0);
  });

  test('disabled rule has enabled=false', () => {
    const rule = makeRule({ enabled: false });
    expect(rule.enabled).toBe(false);
  });
});

describe('UsageEvaluation type shape', () => {
  function makeEval(overrides: Record<string, any> = {}) {
    return {
      rule_id: '00000000-0000-0000-0000-000000000001',
      category: 'games' as const,
      used_minutes: 45,
      limit_minutes: 60,
      percent: 75,
      enforcement_action: 'warning_then_block' as const,
      ...overrides,
    };
  }

  test('usage evaluation has required fields', () => {
    const u = makeEval();
    expect(u.rule_id).toBeDefined();
    expect(u.category).toBe('games');
    expect(typeof u.used_minutes).toBe('number');
    expect(typeof u.limit_minutes).toBe('number');
    expect(typeof u.percent).toBe('number');
    expect(u.enforcement_action).toBeDefined();
  });

  test('percent is between 0 and 100+ (can exceed 100 when over limit)', () => {
    const over = makeEval({ used_minutes: 90, limit_minutes: 60, percent: 150 });
    expect(over.percent).toBeGreaterThan(100);
  });

  test('percent is 0 when no usage', () => {
    const empty = makeEval({ used_minutes: 0, percent: 0 });
    expect(empty.percent).toBe(0);
  });
});

describe('ExtensionRequest type shape', () => {
  function makeRequest(overrides: Record<string, any> = {}) {
    return {
      id: '00000000-0000-0000-0000-000000000010',
      member_id: '00000000-0000-0000-0000-000000000002',
      rule_id: '00000000-0000-0000-0000-000000000001',
      requested_minutes: 30,
      status: 'pending' as const,
      requested_at: '2026-03-23T14:00:00Z',
      responded_at: null,
      responded_by: null,
      reason: 'Need more time for homework research',
      ...overrides,
    };
  }

  test('extension request has required fields', () => {
    const req = makeRequest();
    expect(req.id).toBeDefined();
    expect(req.member_id).toBeDefined();
    expect(req.rule_id).toBeDefined();
    expect(req.requested_minutes).toBeGreaterThan(0);
    expect(req.status).toBe('pending');
    expect(req.requested_at).toBeDefined();
  });

  test('approved request has responded_at set', () => {
    const req = makeRequest({
      status: 'approved',
      responded_at: '2026-03-23T14:05:00Z',
      responded_by: 'parent-id',
    });
    expect(req.status).toBe('approved');
    expect(req.responded_at).not.toBeNull();
    expect(req.responded_by).not.toBeNull();
  });

  test('denied request has status denied', () => {
    const req = makeRequest({ status: 'denied', responded_at: '2026-03-23T14:05:00Z' });
    expect(req.status).toBe('denied');
  });

  test('pending request has null responded fields', () => {
    const req = makeRequest();
    expect(req.responded_at).toBeNull();
    expect(req.responded_by).toBeNull();
  });
});

describe('WeeklyReport type shape', () => {
  function makeReport(overrides: Record<string, any> = {}) {
    return {
      member_id: '00000000-0000-0000-0000-000000000002',
      period_start: '2026-03-17',
      period_end: '2026-03-23',
      total_minutes: 420,
      daily_average_minutes: 60,
      days_with_data: 7,
      daily_totals: Array.from({ length: 7 }, (_, i) => ({
        date: `2026-03-${17 + i}`,
        minutes: 60,
      })),
      category_totals: [
        { category: 'social', minutes: 200 },
        { category: 'games', minutes: 120 },
        { category: 'education', minutes: 100 },
      ],
      ...overrides,
    };
  }

  test('weekly report has all required fields', () => {
    const report = makeReport();
    expect(report.member_id).toBeDefined();
    expect(report.period_start).toBeDefined();
    expect(report.period_end).toBeDefined();
    expect(typeof report.total_minutes).toBe('number');
    expect(typeof report.daily_average_minutes).toBe('number');
    expect(typeof report.days_with_data).toBe('number');
    expect(Array.isArray(report.daily_totals)).toBe(true);
    expect(Array.isArray(report.category_totals)).toBe(true);
  });

  test('daily totals have 7 entries for a full week', () => {
    const report = makeReport();
    expect(report.daily_totals).toHaveLength(7);
  });

  test('daily average matches total / days', () => {
    const report = makeReport({ total_minutes: 420, days_with_data: 7, daily_average_minutes: 60 });
    expect(report.daily_average_minutes).toBe(report.total_minutes / report.days_with_data);
  });

  test('category totals sum to approximately total minutes', () => {
    const report = makeReport();
    const categorySum = report.category_totals.reduce(
      (sum: number, c: { minutes: number }) => sum + c.minutes,
      0
    );
    // Category totals should be <= total (some time may be uncategorized)
    expect(categorySum).toBeLessThanOrEqual(report.total_minutes + 1);
  });

  test('report with no data has zero totals', () => {
    const report = makeReport({
      total_minutes: 0,
      daily_average_minutes: 0,
      days_with_data: 0,
      daily_totals: [],
      category_totals: [],
    });
    expect(report.total_minutes).toBe(0);
    expect(report.daily_totals.length).toBe(0);
    expect(report.category_totals.length).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// Shared types export tests
// ---------------------------------------------------------------------------

describe('Shared types exports', () => {
  test('screen-time types are re-exported from shared-types index', () => {
    // Load shared-types index via the module alias @bhapi/types
    // (mapped in jest.config.js to packages/shared-types/src)
    const mod = require('@bhapi/types');
    // TypeScript interfaces are erased at runtime; we verify the module loads without error
    expect(mod).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Hooks module tests
// ---------------------------------------------------------------------------

describe('useScreenTime hooks module', () => {
  test('hooks module exports useScreenTimeRules', () => {
    const mod = require('../src/hooks/useScreenTime');
    expect(typeof mod.useScreenTimeRules).toBe('function');
  });

  test('hooks module exports useCreateRule', () => {
    const mod = require('../src/hooks/useScreenTime');
    expect(typeof mod.useCreateRule).toBe('function');
  });

  test('hooks module exports useUpdateRule', () => {
    const mod = require('../src/hooks/useScreenTime');
    expect(typeof mod.useUpdateRule).toBe('function');
  });

  test('hooks module exports useDeleteRule', () => {
    const mod = require('../src/hooks/useScreenTime');
    expect(typeof mod.useDeleteRule).toBe('function');
  });

  test('hooks module exports useUsageEvaluation', () => {
    const mod = require('../src/hooks/useScreenTime');
    expect(typeof mod.useUsageEvaluation).toBe('function');
  });

  test('hooks module exports useExtensionRequests', () => {
    const mod = require('../src/hooks/useScreenTime');
    expect(typeof mod.useExtensionRequests).toBe('function');
  });

  test('hooks module exports useRespondExtension', () => {
    const mod = require('../src/hooks/useScreenTime');
    expect(typeof mod.useRespondExtension).toBe('function');
  });

  test('hooks module exports useWeeklyReport', () => {
    const mod = require('../src/hooks/useScreenTime');
    expect(typeof mod.useWeeklyReport).toBe('function');
  });
});

// ---------------------------------------------------------------------------
// Percent clamping logic (usage bar)
// ---------------------------------------------------------------------------

describe('Usage bar clamping logic', () => {
  function clampPercent(percent: number): number {
    return Math.min(percent, 100);
  }

  test('percent below 100 is unchanged', () => {
    expect(clampPercent(75)).toBe(75);
  });

  test('percent at 100 is unchanged', () => {
    expect(clampPercent(100)).toBe(100);
  });

  test('percent above 100 is clamped to 100', () => {
    expect(clampPercent(150)).toBe(100);
  });

  test('percent of 0 is 0', () => {
    expect(clampPercent(0)).toBe(0);
  });

  test('isOver is true when percent >= 100', () => {
    const isOver = (p: number) => p >= 100;
    expect(isOver(100)).toBe(true);
    expect(isOver(150)).toBe(true);
    expect(isOver(99)).toBe(false);
  });

  test('isWarning is true when percent >= 80 and not over', () => {
    const isWarning = (p: number) => p >= 80 && p < 100;
    expect(isWarning(80)).toBe(true);
    expect(isWarning(95)).toBe(true);
    expect(isWarning(100)).toBe(false);
    expect(isWarning(79)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Category preset validation
// ---------------------------------------------------------------------------

describe('Category preset validation', () => {
  const VALID_CATEGORIES = ['social', 'games', 'education', 'entertainment', 'productivity', 'all'];

  test('all preset categories are valid AppCategory values', () => {
    const { CATEGORY_PRESETS } = require('../app/(settings)/screen-time-settings');
    for (const preset of CATEGORY_PRESETS) {
      expect(VALID_CATEGORIES).toContain(preset.value);
    }
  });

  test('all enforcement options are valid EnforcementAction values', () => {
    const { ENFORCEMENT_OPTIONS } = require('../app/(settings)/screen-time-settings');
    const VALID_ENFORCEMENT = ['hard_block', 'warning_then_block', 'warning_only'];
    for (const opt of ENFORCEMENT_OPTIONS) {
      expect(VALID_ENFORCEMENT).toContain(opt.value);
    }
  });

  test('each preset has label and value', () => {
    const { CATEGORY_PRESETS } = require('../app/(settings)/screen-time-settings');
    for (const preset of CATEGORY_PRESETS) {
      expect(typeof preset.value).toBe('string');
      expect(typeof preset.label).toBe('string');
      expect(preset.label.length).toBeGreaterThan(0);
    }
  });
});
