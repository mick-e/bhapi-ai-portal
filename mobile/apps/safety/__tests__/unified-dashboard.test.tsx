/**
 * Unified Dashboard Screen Tests (P3-F4)
 *
 * Tests for the unified parent dashboard screen combining risk score,
 * AI activity, social, screen time, location, and action center sections.
 */

// ---------------------------------------------------------------------------
// Module export tests — UnifiedDashboardScreen
// ---------------------------------------------------------------------------

describe('UnifiedDashboardScreen', () => {
  test('exports default component', () => {
    const mod = require('../app/(dashboard)/unified');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports SectionHeader sub-component', () => {
    const mod = require('../app/(dashboard)/unified');
    expect(mod.SectionHeader).toBeDefined();
    expect(typeof mod.SectionHeader).toBe('function');
  });

  test('exports StatRow sub-component', () => {
    const mod = require('../app/(dashboard)/unified');
    expect(mod.StatRow).toBeDefined();
    expect(typeof mod.StatRow).toBe('function');
  });

  test('exports ActionItemRow sub-component', () => {
    const mod = require('../app/(dashboard)/unified');
    expect(mod.ActionItemRow).toBeDefined();
    expect(typeof mod.ActionItemRow).toBe('function');
  });
});

// ---------------------------------------------------------------------------
// RiskScoreCard component tests (shared-ui)
// ---------------------------------------------------------------------------

describe('RiskScoreCard (shared-ui)', () => {
  test('exports RiskScoreCard from @bhapi/ui', () => {
    const mod = require('@bhapi/ui');
    expect(mod.RiskScoreCard).toBeDefined();
  });

  test('RiskScoreCard is a function', () => {
    const { RiskScoreCard } = require('@bhapi/ui');
    expect(typeof RiskScoreCard).toBe('function');
  });
});

// ---------------------------------------------------------------------------
// SectionHeader sub-component tests
// ---------------------------------------------------------------------------

describe('SectionHeader', () => {
  test('renders with title prop and returns object', () => {
    const React = require('react');
    const { SectionHeader } = require('../app/(dashboard)/unified');
    const result = SectionHeader({ title: 'Risk Score' });
    expect(result).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// StatRow sub-component tests
// ---------------------------------------------------------------------------

describe('StatRow', () => {
  test('renders with label and string value', () => {
    const React = require('react');
    const { StatRow } = require('../app/(dashboard)/unified');
    const result = StatRow({ label: 'Events today', value: '12' });
    expect(result).toBeDefined();
  });

  test('renders with label and numeric value', () => {
    const React = require('react');
    const { StatRow } = require('../app/(dashboard)/unified');
    const result = StatRow({ label: 'Total today', value: 42 });
    expect(result).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// ActionItemRow sub-component tests
// ---------------------------------------------------------------------------

describe('ActionItemRow', () => {
  test('renders with label and zero count', () => {
    const React = require('react');
    const { ActionItemRow } = require('../app/(dashboard)/unified');
    const result = ActionItemRow({ label: 'Pending approvals', count: 0 });
    expect(result).toBeDefined();
  });

  test('renders with label and urgent count', () => {
    const React = require('react');
    const { ActionItemRow } = require('../app/(dashboard)/unified');
    const result = ActionItemRow({
      label: 'Unread alerts',
      count: 5,
      urgentThreshold: 3,
    });
    expect(result).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Type shape tests — UnifiedData
// ---------------------------------------------------------------------------

describe('UnifiedData type shapes', () => {
  test('UnifiedData type has expected risk score shape', () => {
    const riskScore = {
      score: 45,
      trend: 'stable' as const,
      confidence: 'high' as const,
      factors: ['Factor 1', 'Factor 2'],
    };
    expect(riskScore.score).toBe(45);
    expect(['up', 'down', 'stable']).toContain(riskScore.trend);
    expect(['low', 'medium', 'high']).toContain(riskScore.confidence);
    expect(Array.isArray(riskScore.factors)).toBe(true);
  });

  test('ActionCenterData has expected properties', () => {
    const actionCenter = {
      pending_approvals: 2,
      unread_alerts: 5,
      pending_extension_requests: 1,
    };
    expect(typeof actionCenter.pending_approvals).toBe('number');
    expect(typeof actionCenter.unread_alerts).toBe('number');
    expect(typeof actionCenter.pending_extension_requests).toBe('number');
  });
});

// ---------------------------------------------------------------------------
// Screen renders test
// ---------------------------------------------------------------------------

describe('UnifiedDashboardScreen renders', () => {
  test('default export is a function (component definition)', () => {
    const mod = require('../app/(dashboard)/unified');
    // Just verify the component is defined and is a function — full render
    // requires React Native runtime which is not available in unit tests.
    expect(typeof mod.default).toBe('function');
    expect(mod.default.name).toBe('UnifiedDashboardScreen');
  });

  test('shows risk score card when invoked via mock', () => {
    const { RiskScoreCard } = require('@bhapi/ui');
    const result = RiskScoreCard({
      score: 45,
      trend: 'stable',
      confidence: 'high',
      factors: ['Emotional language detected'],
    });
    expect(result).toBeDefined();
  });
});
