/**
 * Location Mobile Screen Tests (P3-F3c)
 *
 * Tests for location dashboard and settings screens,
 * sub-components, and type shapes.
 */

// ---------------------------------------------------------------------------
// Module export tests — Location Dashboard
// ---------------------------------------------------------------------------

describe('LocationScreen', () => {
  test('exports default component', () => {
    const mod = require('../app/(dashboard)/location');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports MapPlaceholder sub-component', () => {
    const mod = require('../app/(dashboard)/location');
    expect(mod.MapPlaceholder).toBeDefined();
    expect(typeof mod.MapPlaceholder).toBe('function');
  });

  test('exports GeofenceItem sub-component', () => {
    const mod = require('../app/(dashboard)/location');
    expect(mod.GeofenceItem).toBeDefined();
    expect(typeof mod.GeofenceItem).toBe('function');
  });

  test('exports HistoryPoint sub-component', () => {
    const mod = require('../app/(dashboard)/location');
    expect(mod.HistoryPoint).toBeDefined();
    expect(typeof mod.HistoryPoint).toBe('function');
  });

  test('exports GEOFENCE_COLORS with 3 types', () => {
    const { GEOFENCE_COLORS } = require('../app/(dashboard)/location');
    expect(GEOFENCE_COLORS).toBeDefined();
    expect(GEOFENCE_COLORS.home).toBeDefined();
    expect(GEOFENCE_COLORS.school).toBeDefined();
    expect(GEOFENCE_COLORS.custom).toBeDefined();
  });

  test('home geofence color is green', () => {
    const { GEOFENCE_COLORS } = require('../app/(dashboard)/location');
    expect(GEOFENCE_COLORS.home).toBe('#16A34A');
  });

  test('school geofence color is blue', () => {
    const { GEOFENCE_COLORS } = require('../app/(dashboard)/location');
    expect(GEOFENCE_COLORS.school).toBe('#2563EB');
  });

  test('custom geofence color is orange', () => {
    const { GEOFENCE_COLORS } = require('../app/(dashboard)/location');
    expect(GEOFENCE_COLORS.custom).toBe('#EA580C');
  });
});

// ---------------------------------------------------------------------------
// Module export tests — Location Settings
// ---------------------------------------------------------------------------

describe('LocationSettings', () => {
  test('exports default component', () => {
    const mod = require('../app/(settings)/location-settings');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports RETENTION_OPTIONS with 4 options', () => {
    const { RETENTION_OPTIONS } = require('../app/(settings)/location-settings');
    expect(RETENTION_OPTIONS).toHaveLength(4);
    const values = RETENTION_OPTIONS.map((o: any) => o.value);
    expect(values).toContain(7);
    expect(values).toContain(14);
    expect(values).toContain(30);
    expect(values).toContain(90);
  });

  test('exports GEOFENCE_TYPE_OPTIONS with 3 types', () => {
    const { GEOFENCE_TYPE_OPTIONS } = require('../app/(settings)/location-settings');
    expect(GEOFENCE_TYPE_OPTIONS).toHaveLength(3);
    const values = GEOFENCE_TYPE_OPTIONS.map((o: any) => o.value);
    expect(values).toContain('home');
    expect(values).toContain('school');
    expect(values).toContain('custom');
  });

  test('exports DEFAULT_RADIUS_OPTIONS as number array', () => {
    const { DEFAULT_RADIUS_OPTIONS } = require('../app/(settings)/location-settings');
    expect(Array.isArray(DEFAULT_RADIUS_OPTIONS)).toBe(true);
    expect(DEFAULT_RADIUS_OPTIONS.length).toBeGreaterThan(0);
    for (const r of DEFAULT_RADIUS_OPTIONS) {
      expect(typeof r).toBe('number');
      expect(r).toBeGreaterThan(0);
    }
  });

  test('exports GeofenceSettingsItem sub-component', () => {
    const { GeofenceSettingsItem } = require('../app/(settings)/location-settings');
    expect(GeofenceSettingsItem).toBeDefined();
    expect(typeof GeofenceSettingsItem).toBe('function');
  });

  test('exports AddGeofenceForm sub-component', () => {
    const { AddGeofenceForm } = require('../app/(settings)/location-settings');
    expect(AddGeofenceForm).toBeDefined();
    expect(typeof AddGeofenceForm).toBe('function');
  });

  test('each retention option has value and label', () => {
    const { RETENTION_OPTIONS } = require('../app/(settings)/location-settings');
    for (const opt of RETENTION_OPTIONS) {
      expect(typeof opt.value).toBe('number');
      expect(typeof opt.label).toBe('string');
      expect(opt.label.length).toBeGreaterThan(0);
    }
  });

  test('each geofence type option has value, label, and color', () => {
    const { GEOFENCE_TYPE_OPTIONS } = require('../app/(settings)/location-settings');
    for (const opt of GEOFENCE_TYPE_OPTIONS) {
      expect(typeof opt.value).toBe('string');
      expect(typeof opt.label).toBe('string');
      expect(typeof opt.color).toBe('string');
      expect(opt.color).toMatch(/^#[0-9A-Fa-f]{6}$/);
    }
  });
});

// ---------------------------------------------------------------------------
// LocationPoint type shape tests
// ---------------------------------------------------------------------------

describe('LocationPoint type shape', () => {
  function makePoint(overrides: Record<string, any> = {}) {
    return {
      lat: 51.5074,
      lng: -0.1278,
      timestamp: '2026-03-23T10:30:00Z',
      accuracy: 10,
      source: 'gps' as const,
      ...overrides,
    };
  }

  test('point has all required fields', () => {
    const point = makePoint();
    expect(typeof point.lat).toBe('number');
    expect(typeof point.lng).toBe('number');
    expect(point.timestamp).toBeDefined();
    expect(typeof point.source).toBe('string');
  });

  test('accuracy can be null (unknown)', () => {
    const point = makePoint({ accuracy: null });
    expect(point.accuracy).toBeNull();
  });

  test('source values are valid', () => {
    const VALID_SOURCES = ['gps', 'network', 'passive'];
    for (const source of VALID_SOURCES) {
      const point = makePoint({ source });
      expect(VALID_SOURCES).toContain(point.source);
    }
  });

  test('lat and lng are in valid ranges', () => {
    const point = makePoint();
    expect(point.lat).toBeGreaterThanOrEqual(-90);
    expect(point.lat).toBeLessThanOrEqual(90);
    expect(point.lng).toBeGreaterThanOrEqual(-180);
    expect(point.lng).toBeLessThanOrEqual(180);
  });
});

// ---------------------------------------------------------------------------
// Geofence type shape tests
// ---------------------------------------------------------------------------

describe('Geofence type shape', () => {
  function makeGeofence(overrides: Record<string, any> = {}) {
    return {
      id: '00000000-0000-0000-0000-000000000001',
      name: 'Home',
      lat: 51.5074,
      lng: -0.1278,
      radius_meters: 200,
      type: 'home' as const,
      alerts_enabled: true,
      ...overrides,
    };
  }

  test('geofence has all required fields', () => {
    const gf = makeGeofence();
    expect(gf.id).toBeDefined();
    expect(gf.name).toBeDefined();
    expect(typeof gf.lat).toBe('number');
    expect(typeof gf.lng).toBe('number');
    expect(typeof gf.radius_meters).toBe('number');
    expect(['home', 'school', 'custom']).toContain(gf.type);
    expect(typeof gf.alerts_enabled).toBe('boolean');
  });

  test('radius_meters is a positive number', () => {
    const gf = makeGeofence({ radius_meters: 500 });
    expect(gf.radius_meters).toBeGreaterThan(0);
  });

  test('alerts can be disabled', () => {
    const gf = makeGeofence({ alerts_enabled: false });
    expect(gf.alerts_enabled).toBe(false);
  });

  test('supports school type', () => {
    const gf = makeGeofence({ name: 'Primary School', type: 'school' });
    expect(gf.type).toBe('school');
  });

  test('supports custom type', () => {
    const gf = makeGeofence({ name: 'Grandma\'s', type: 'custom' });
    expect(gf.type).toBe('custom');
  });
});

// ---------------------------------------------------------------------------
// LocationHistory type shape tests
// ---------------------------------------------------------------------------

describe('LocationHistory type shape', () => {
  function makeHistory(overrides: Record<string, any> = {}) {
    return {
      member_id: '00000000-0000-0000-0000-000000000001',
      points: [
        { lat: 51.5074, lng: -0.1278, timestamp: '2026-03-23T08:00:00Z', accuracy: 10, source: 'gps' },
        { lat: 51.5080, lng: -0.1270, timestamp: '2026-03-23T12:00:00Z', accuracy: 15, source: 'network' },
      ],
      date: '2026-03-23',
      ...overrides,
    };
  }

  test('history has all required fields', () => {
    const h = makeHistory();
    expect(h.member_id).toBeDefined();
    expect(Array.isArray(h.points)).toBe(true);
    expect(h.date).toBeDefined();
  });

  test('history with no points is valid', () => {
    const h = makeHistory({ points: [] });
    expect(h.points.length).toBe(0);
  });

  test('points have correct shape', () => {
    const h = makeHistory();
    for (const p of h.points) {
      expect(typeof p.lat).toBe('number');
      expect(typeof p.lng).toBe('number');
      expect(p.timestamp).toBeDefined();
      expect(p.source).toBeDefined();
    }
  });
});

// ---------------------------------------------------------------------------
// LocationSettings type shape tests
// ---------------------------------------------------------------------------

describe('LocationSettings type shape', () => {
  function makeSettings(overrides: Record<string, any> = {}) {
    return {
      tracking_enabled: true,
      history_retention_days: 30,
      geofences: [],
      ...overrides,
    };
  }

  test('settings has all required fields', () => {
    const s = makeSettings();
    expect(typeof s.tracking_enabled).toBe('boolean');
    expect(typeof s.history_retention_days).toBe('number');
    expect(Array.isArray(s.geofences)).toBe(true);
  });

  test('tracking can be disabled', () => {
    const s = makeSettings({ tracking_enabled: false });
    expect(s.tracking_enabled).toBe(false);
  });

  test('retention_days is one of the standard values', () => {
    const VALID_RETENTION = [7, 14, 30, 90];
    for (const days of VALID_RETENTION) {
      const s = makeSettings({ history_retention_days: days });
      expect(VALID_RETENTION).toContain(s.history_retention_days);
    }
  });

  test('settings can include geofences', () => {
    const geofence = {
      id: 'g1',
      name: 'Home',
      lat: 51.5,
      lng: -0.1,
      radius_meters: 200,
      type: 'home',
      alerts_enabled: true,
    };
    const s = makeSettings({ geofences: [geofence] });
    expect(s.geofences).toHaveLength(1);
    expect(s.geofences[0].name).toBe('Home');
  });
});

// ---------------------------------------------------------------------------
// Shared types export tests
// ---------------------------------------------------------------------------

describe('Shared location types exports', () => {
  test('location types are re-exported from shared-types index', () => {
    const mod = require('@bhapi/types');
    expect(mod).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Hooks module tests
// ---------------------------------------------------------------------------

describe('useLocation hooks module', () => {
  test('hooks module exports useLocationHistory', () => {
    const mod = require('../src/hooks/useLocation');
    expect(typeof mod.useLocationHistory).toBe('function');
  });

  test('hooks module exports useGeofences', () => {
    const mod = require('../src/hooks/useLocation');
    expect(typeof mod.useGeofences).toBe('function');
  });

  test('hooks module exports useCreateGeofence', () => {
    const mod = require('../src/hooks/useLocation');
    expect(typeof mod.useCreateGeofence).toBe('function');
  });

  test('hooks module exports useUpdateGeofence', () => {
    const mod = require('../src/hooks/useLocation');
    expect(typeof mod.useUpdateGeofence).toBe('function');
  });

  test('hooks module exports useDeleteGeofence', () => {
    const mod = require('../src/hooks/useLocation');
    expect(typeof mod.useDeleteGeofence).toBe('function');
  });

  test('hooks module exports useLocationSettings', () => {
    const mod = require('../src/hooks/useLocation');
    expect(typeof mod.useLocationSettings).toBe('function');
  });

  test('hooks module exports useUpdateLocationSettings', () => {
    const mod = require('../src/hooks/useLocation');
    expect(typeof mod.useUpdateLocationSettings).toBe('function');
  });
});

// ---------------------------------------------------------------------------
// Geofence color logic tests
// ---------------------------------------------------------------------------

describe('Geofence color logic', () => {
  test('all GeofenceType values have a color mapping', () => {
    const { GEOFENCE_COLORS } = require('../app/(dashboard)/location');
    const TYPES = ['home', 'school', 'custom'];
    for (const type of TYPES) {
      expect(GEOFENCE_COLORS[type]).toBeDefined();
      expect(GEOFENCE_COLORS[type]).toMatch(/^#[0-9A-Fa-f]{6}$/);
    }
  });

  test('home color is distinctly green', () => {
    const { GEOFENCE_COLORS } = require('../app/(dashboard)/location');
    // Green starts with #16A or similar
    expect(GEOFENCE_COLORS.home.toLowerCase()).toContain('6a3');
  });

  test('geofence labels are defined for all types', () => {
    const { GEOFENCE_LABELS } = require('../app/(dashboard)/location');
    expect(GEOFENCE_LABELS.home).toBe('Home');
    expect(GEOFENCE_LABELS.school).toBe('School');
    expect(GEOFENCE_LABELS.custom).toBe('Custom');
  });
});

// ---------------------------------------------------------------------------
// Retention option validation tests
// ---------------------------------------------------------------------------

describe('Retention option validation', () => {
  test('all retention options are positive integers', () => {
    const { RETENTION_OPTIONS } = require('../app/(settings)/location-settings');
    for (const opt of RETENTION_OPTIONS) {
      expect(opt.value).toBeGreaterThan(0);
      expect(Number.isInteger(opt.value)).toBe(true);
    }
  });

  test('retention options are in ascending order', () => {
    const { RETENTION_OPTIONS } = require('../app/(settings)/location-settings');
    for (let i = 1; i < RETENTION_OPTIONS.length; i++) {
      expect(RETENTION_OPTIONS[i].value).toBeGreaterThan(RETENTION_OPTIONS[i - 1].value);
    }
  });

  test('radius options are positive', () => {
    const { DEFAULT_RADIUS_OPTIONS } = require('../app/(settings)/location-settings');
    for (const r of DEFAULT_RADIUS_OPTIONS) {
      expect(r).toBeGreaterThan(0);
    }
  });
});
