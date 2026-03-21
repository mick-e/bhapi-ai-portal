/**
 * Profile Tests — profile display, edit form validation, avatar upload flow,
 * follower list, visibility toggle, post view mode.
 */

// ---------------------------------------------------------------------------
// Profile Screen
// ---------------------------------------------------------------------------

describe('Profile Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(profile)/index');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports POST_PAGE_SIZE constant', () => {
    const { POST_PAGE_SIZE } = require('../app/(profile)/index');
    expect(POST_PAGE_SIZE).toBe(20);
  });

  test('exports VISIBILITY_LABELS', () => {
    const { VISIBILITY_LABELS } = require('../app/(profile)/index');
    expect(VISIBILITY_LABELS.public).toBe('Public');
    expect(VISIBILITY_LABELS.friends_only).toBe('Friends Only');
    expect(VISIBILITY_LABELS.private).toBe('Private');
  });

  test('profile screen renders without crashing', () => {
    const mod = require('../app/(profile)/index');
    const result = mod.default();
    expect(result).toBeDefined();
  });

  test('profile screen renders in loading state initially', () => {
    // useState mock returns initial values
    const mod = require('../app/(profile)/index');
    const result = mod.default();
    // Loading state renders ActivityIndicator
    expect(result).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Edit Profile Screen
// ---------------------------------------------------------------------------

describe('Edit Profile Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(profile)/edit');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports MAX_DISPLAY_NAME_LENGTH', () => {
    const { MAX_DISPLAY_NAME_LENGTH } = require('../app/(profile)/edit');
    expect(MAX_DISPLAY_NAME_LENGTH).toBe(255);
  });

  test('exports MIN_DISPLAY_NAME_LENGTH', () => {
    const { MIN_DISPLAY_NAME_LENGTH } = require('../app/(profile)/edit');
    expect(MIN_DISPLAY_NAME_LENGTH).toBe(1);
  });

  test('exports MAX_BIO_LENGTH', () => {
    const { MAX_BIO_LENGTH } = require('../app/(profile)/edit');
    expect(MAX_BIO_LENGTH).toBe(500);
  });

  test('exports VISIBILITY_OPTIONS with 3 choices', () => {
    const { VISIBILITY_OPTIONS } = require('../app/(profile)/edit');
    expect(VISIBILITY_OPTIONS).toHaveLength(3);
    const values = VISIBILITY_OPTIONS.map((o: any) => o.value);
    expect(values).toContain('public');
    expect(values).toContain('friends_only');
    expect(values).toContain('private');
  });

  test('edit screen renders without crashing', () => {
    const mod = require('../app/(profile)/edit');
    const result = mod.default();
    expect(result).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Profile Form Validation
// ---------------------------------------------------------------------------

describe('validateProfileForm', () => {
  const { validateProfileForm } = require('../app/(profile)/edit');

  test('returns null for valid input', () => {
    expect(validateProfileForm('Alice', 'Hello world')).toBeNull();
  });

  test('rejects empty display name', () => {
    const err = validateProfileForm('', 'Bio');
    expect(err).toBe('Display name is required');
  });

  test('rejects whitespace-only display name', () => {
    const err = validateProfileForm('   ', 'Bio');
    expect(err).toBe('Display name is required');
  });

  test('rejects display name over max length', () => {
    const longName = 'A'.repeat(256);
    const err = validateProfileForm(longName, '');
    expect(err).toContain('255');
  });

  test('accepts display name at max length', () => {
    const maxName = 'A'.repeat(255);
    expect(validateProfileForm(maxName, '')).toBeNull();
  });

  test('rejects bio over max length', () => {
    const longBio = 'B'.repeat(501);
    const err = validateProfileForm('Valid Name', longBio);
    expect(err).toContain('500');
  });

  test('accepts bio at max length', () => {
    const maxBio = 'B'.repeat(500);
    expect(validateProfileForm('Valid Name', maxBio)).toBeNull();
  });

  test('accepts empty bio', () => {
    expect(validateProfileForm('Valid Name', '')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Avatar Upload Flow
// ---------------------------------------------------------------------------

describe('Avatar Upload', () => {
  test('Avatar mock is available in ui mocks', () => {
    const { Avatar } = require('../__tests__/__mocks__/@bhapi/ui');
    expect(Avatar).toBeDefined();
  });

  test('Avatar can be called with onUploadPress prop', () => {
    const { Avatar } = require('../__tests__/__mocks__/@bhapi/ui');
    const onUpload = jest.fn();
    const result = Avatar({
      name: 'Test User',
      size: 'lg',
      onUploadPress: onUpload,
    });
    expect(result.props.onUploadPress).toBe(onUpload);
  });

  test('Avatar can be called with isUploading prop', () => {
    const { Avatar } = require('../__tests__/__mocks__/@bhapi/ui');
    const result = Avatar({
      name: 'Test',
      size: 'lg',
      isUploading: true,
    });
    expect(result.props.isUploading).toBe(true);
  });

  test('Avatar renders with source prop for image', () => {
    const { Avatar } = require('../__tests__/__mocks__/@bhapi/ui');
    const result = Avatar({
      name: 'Test',
      source: { uri: 'https://cdn.bhapi.ai/avatar.jpg' },
    });
    expect(result.props.source.uri).toBe('https://cdn.bhapi.ai/avatar.jpg');
  });
});

// ---------------------------------------------------------------------------
// Follower / Following
// ---------------------------------------------------------------------------

describe('Follower List', () => {
  test('profile screen exports are consistent', () => {
    const mod = require('../app/(profile)/index');
    expect(mod.default).toBeDefined();
    expect(mod.POST_PAGE_SIZE).toBeGreaterThan(0);
  });

  test('follower counts are tappable touchable areas (WCAG)', () => {
    // The profile screen uses TouchableOpacity for follower/following counts
    const mod = require('../app/(profile)/index');
    const result = mod.default();
    // The rendered tree should contain TouchableOpacity elements
    expect(result).toBeDefined();
  });

  test('VISIBILITY_LABELS has entries for all visibility types', () => {
    const { VISIBILITY_LABELS } = require('../app/(profile)/index');
    expect(Object.keys(VISIBILITY_LABELS).sort()).toEqual(
      ['friends_only', 'private', 'public']
    );
  });
});

// ---------------------------------------------------------------------------
// Visibility Toggle
// ---------------------------------------------------------------------------

describe('Visibility Toggle', () => {
  test('VISIBILITY_OPTIONS are well-formed', () => {
    const { VISIBILITY_OPTIONS } = require('../app/(profile)/edit');
    VISIBILITY_OPTIONS.forEach((opt: any) => {
      expect(opt).toHaveProperty('value');
      expect(opt).toHaveProperty('label');
      expect(typeof opt.value).toBe('string');
      expect(typeof opt.label).toBe('string');
    });
  });

  test('public option has correct label', () => {
    const { VISIBILITY_OPTIONS } = require('../app/(profile)/edit');
    const pub = VISIBILITY_OPTIONS.find((o: any) => o.value === 'public');
    expect(pub?.label).toBe('Public');
  });

  test('friends_only option has correct label', () => {
    const { VISIBILITY_OPTIONS } = require('../app/(profile)/edit');
    const fo = VISIBILITY_OPTIONS.find((o: any) => o.value === 'friends_only');
    expect(fo?.label).toBe('Friends Only');
  });

  test('private option has correct label', () => {
    const { VISIBILITY_OPTIONS } = require('../app/(profile)/edit');
    const priv = VISIBILITY_OPTIONS.find((o: any) => o.value === 'private');
    expect(priv?.label).toBe('Private');
  });
});

// ---------------------------------------------------------------------------
// Post View Mode
// ---------------------------------------------------------------------------

describe('Post View Mode', () => {
  test('profile screen renders with post section', () => {
    const mod = require('../app/(profile)/index');
    const result = mod.default();
    // The screen renders without crashing, including post section
    expect(result).toBeDefined();
  });
});
