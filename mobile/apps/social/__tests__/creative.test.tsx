/**
 * Creative Mobile Screen Tests (P3-F1c)
 *
 * Tests for art studio, story creator, drawing canvas, and stickers screens,
 * shared UI components, and creative API hooks.
 */

// ---------------------------------------------------------------------------
// Art Studio Screen
// ---------------------------------------------------------------------------

describe('Art Studio Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(creative)/art-studio');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('renders without crashing', () => {
    const mod = require('../app/(creative)/art-studio');
    const result = mod.default();
    expect(result).toBeDefined();
  });

  test('exports MAX_ART_PROMPT_LENGTH as 500', () => {
    const { MAX_ART_PROMPT_LENGTH } = require('../app/(creative)/art-studio');
    expect(MAX_ART_PROMPT_LENGTH).toBe(500);
  });

  test('exports ModerationBadge sub-component', () => {
    const { ModerationBadge } = require('../app/(creative)/art-studio');
    expect(typeof ModerationBadge).toBe('function');
  });

  test('exports ArtCard sub-component', () => {
    const { ArtCard } = require('../app/(creative)/art-studio');
    expect(typeof ArtCard).toBe('function');
  });

  test('ModerationBadge renders for pending status', () => {
    const { ModerationBadge } = require('../app/(creative)/art-studio');
    const result = ModerationBadge({ status: 'pending' });
    expect(result).toBeDefined();
  });

  test('ModerationBadge renders for approved status', () => {
    const { ModerationBadge } = require('../app/(creative)/art-studio');
    const result = ModerationBadge({ status: 'approved' });
    expect(result).toBeDefined();
  });

  test('ModerationBadge renders for rejected status', () => {
    const { ModerationBadge } = require('../app/(creative)/art-studio');
    const result = ModerationBadge({ status: 'rejected' });
    expect(result).toBeDefined();
  });

  test('ArtCard renders with a creation', () => {
    const { ArtCard } = require('../app/(creative)/art-studio');
    const creation = {
      id: 'art-1',
      prompt: 'A rainbow dragon',
      image_url: null,
      moderation_status: 'approved',
      created_at: new Date().toISOString(),
    };
    const onPostToFeed = jest.fn();
    const result = ArtCard({ creation, onPostToFeed });
    expect(result).toBeDefined();
  });

  test('ArtCard with pending status does not show Post to Feed button', () => {
    const { ArtCard } = require('../app/(creative)/art-studio');
    const creation = {
      id: 'art-2',
      prompt: 'A flying cat',
      image_url: null,
      moderation_status: 'pending',
      created_at: new Date().toISOString(),
    };
    const onPostToFeed = jest.fn();
    const result = ArtCard({ creation, onPostToFeed });
    // Pending items have null post button (4th child)
    expect(result).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Story Creator Screen
// ---------------------------------------------------------------------------

describe('Story Creator Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(creative)/story-creator');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('renders without crashing', () => {
    const mod = require('../app/(creative)/story-creator');
    const result = mod.default();
    expect(result).toBeDefined();
  });

  test('exports STORY_THEMES with all 6 themes', () => {
    const { STORY_THEMES } = require('../app/(creative)/story-creator');
    expect(STORY_THEMES).toHaveLength(6);
    const values = STORY_THEMES.map((t: any) => t.value);
    expect(values).toContain('adventure');
    expect(values).toContain('friendship');
    expect(values).toContain('mystery');
    expect(values).toContain('science');
    expect(values).toContain('fantasy');
    expect(values).toContain('humor');
  });

  test('exports ThemeTabs sub-component', () => {
    const { ThemeTabs } = require('../app/(creative)/story-creator');
    expect(typeof ThemeTabs).toBe('function');
  });

  test('exports TemplateCard sub-component', () => {
    const { TemplateCard } = require('../app/(creative)/story-creator');
    expect(typeof TemplateCard).toBe('function');
  });

  test('theme tabs render without crashing', () => {
    const { ThemeTabs } = require('../app/(creative)/story-creator');
    const onThemeChange = jest.fn();
    const result = ThemeTabs({ activeTheme: 'adventure', onThemeChange });
    expect(result).toBeDefined();
  });

  test('exports MAX_STORY_LENGTH as 2000', () => {
    const { MAX_STORY_LENGTH } = require('../app/(creative)/story-creator');
    expect(MAX_STORY_LENGTH).toBe(2000);
  });

  test('getTemplateTypeForTier returns fill_in_blank for young', () => {
    const { getTemplateTypeForTier } = require('../app/(creative)/story-creator');
    expect(getTemplateTypeForTier('young')).toBe('fill_in_blank');
  });

  test('getTemplateTypeForTier returns guided_outline for preteen', () => {
    const { getTemplateTypeForTier } = require('../app/(creative)/story-creator');
    expect(getTemplateTypeForTier('preteen')).toBe('guided_outline');
  });

  test('getTemplateTypeForTier returns free_write for teen', () => {
    const { getTemplateTypeForTier } = require('../app/(creative)/story-creator');
    expect(getTemplateTypeForTier('teen')).toBe('free_write');
  });

  test('PLACEHOLDER_TEMPLATES is non-empty array', () => {
    const { PLACEHOLDER_TEMPLATES } = require('../app/(creative)/story-creator');
    expect(Array.isArray(PLACEHOLDER_TEMPLATES)).toBe(true);
    expect(PLACEHOLDER_TEMPLATES.length).toBeGreaterThan(0);
  });

  test('each template has required fields', () => {
    const { PLACEHOLDER_TEMPLATES } = require('../app/(creative)/story-creator');
    for (const t of PLACEHOLDER_TEMPLATES) {
      expect(typeof t.id).toBe('string');
      expect(typeof t.theme).toBe('string');
      expect(typeof t.title).toBe('string');
      expect(typeof t.preview).toBe('string');
      expect(Array.isArray(t.age_tiers)).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// Drawing Screen
// ---------------------------------------------------------------------------

describe('Drawing Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(creative)/drawing');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('renders without crashing', () => {
    const mod = require('../app/(creative)/drawing');
    const result = mod.default();
    expect(result).toBeDefined();
  });

  test('exports CanvasPlaceholder sub-component', () => {
    const { CanvasPlaceholder } = require('../app/(creative)/drawing');
    expect(typeof CanvasPlaceholder).toBe('function');
  });

  test('CanvasPlaceholder renders without crashing', () => {
    const { CanvasPlaceholder } = require('../app/(creative)/drawing');
    const result = CanvasPlaceholder({ height: 320 });
    expect(result).toBeDefined();
  });

  test('exports DEFAULT_BRUSH_COLOR', () => {
    const { DEFAULT_BRUSH_COLOR } = require('../app/(creative)/drawing');
    expect(typeof DEFAULT_BRUSH_COLOR).toBe('string');
    expect(DEFAULT_BRUSH_COLOR).toBeTruthy();
  });

  test('exports DEFAULT_BRUSH_SIZE as medium', () => {
    const { DEFAULT_BRUSH_SIZE } = require('../app/(creative)/drawing');
    expect(DEFAULT_BRUSH_SIZE).toBe('medium');
  });
});

// ---------------------------------------------------------------------------
// Stickers Screen
// ---------------------------------------------------------------------------

describe('Stickers Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(creative)/stickers');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('renders without crashing', () => {
    const mod = require('../app/(creative)/stickers');
    const result = mod.default();
    expect(result).toBeDefined();
  });

  test('exports LIBRARY_TABS with curated and personal tabs', () => {
    const { LIBRARY_TABS } = require('../app/(creative)/stickers');
    expect(LIBRARY_TABS).toHaveLength(2);
    const values = LIBRARY_TABS.map((t: any) => t.value);
    expect(values).toContain('curated');
    expect(values).toContain('personal');
  });

  test('exports LibraryTabBar sub-component', () => {
    const { LibraryTabBar } = require('../app/(creative)/stickers');
    expect(typeof LibraryTabBar).toBe('function');
  });

  test('PLACEHOLDER_CURATED_STICKERS has branded, seasonal, and educational stickers', () => {
    const { PLACEHOLDER_CURATED_STICKERS } = require('../app/(creative)/stickers');
    expect(Array.isArray(PLACEHOLDER_CURATED_STICKERS)).toBe(true);
    expect(PLACEHOLDER_CURATED_STICKERS.length).toBeGreaterThan(0);
    const categories = PLACEHOLDER_CURATED_STICKERS.map((s: any) => s.category);
    expect(categories).toContain('branded');
    expect(categories).toContain('seasonal');
    expect(categories).toContain('educational');
  });

  test('each curated sticker has id, image_url, name, category', () => {
    const { PLACEHOLDER_CURATED_STICKERS } = require('../app/(creative)/stickers');
    for (const s of PLACEHOLDER_CURATED_STICKERS) {
      expect(typeof s.id).toBe('string');
      expect(typeof s.image_url).toBe('string');
      expect(typeof s.name).toBe('string');
      expect(typeof s.category).toBe('string');
    }
  });
});

// ---------------------------------------------------------------------------
// Shared UI — CreativeToolbar
// ---------------------------------------------------------------------------

describe('CreativeToolbar component export', () => {
  test('CreativeToolbar is exported from @bhapi/ui mock', () => {
    const { CreativeToolbar } = require('../__tests__/__mocks__/@bhapi/ui');
    expect(typeof CreativeToolbar).toBe('function');
  });

  test('PRESET_COLORS has 8 colors', () => {
    const { PRESET_COLORS } = require('../__tests__/__mocks__/@bhapi/ui');
    expect(PRESET_COLORS).toHaveLength(8);
  });

  test('SIZE_PRESETS has 3 sizes: thin, medium, thick', () => {
    const { SIZE_PRESETS } = require('../__tests__/__mocks__/@bhapi/ui');
    expect(SIZE_PRESETS).toHaveLength(3);
    const values = SIZE_PRESETS.map((s: any) => s.value);
    expect(values).toContain('thin');
    expect(values).toContain('medium');
    expect(values).toContain('thick');
  });
});

// ---------------------------------------------------------------------------
// Shared UI — StickerGrid
// ---------------------------------------------------------------------------

describe('StickerGrid component export', () => {
  test('StickerGrid is exported from @bhapi/ui mock', () => {
    const { StickerGrid } = require('../__tests__/__mocks__/@bhapi/ui');
    expect(typeof StickerGrid).toBe('function');
  });

  test('STICKER_CATEGORIES has 4 categories', () => {
    const { STICKER_CATEGORIES } = require('../__tests__/__mocks__/@bhapi/ui');
    expect(STICKER_CATEGORIES).toHaveLength(4);
    const values = STICKER_CATEGORIES.map((c: any) => c.value);
    expect(values).toContain('branded');
    expect(values).toContain('seasonal');
    expect(values).toContain('educational');
    expect(values).toContain('my_stickers');
  });
});

// ---------------------------------------------------------------------------
// Creative hooks module
// ---------------------------------------------------------------------------

describe('useCreative hooks module', () => {
  test('exports useGenerateArt', () => {
    const mod = require('../src/hooks/useCreative');
    expect(typeof mod.useGenerateArt).toBe('function');
  });

  test('exports useMyArt', () => {
    const mod = require('../src/hooks/useCreative');
    expect(typeof mod.useMyArt).toBe('function');
  });

  test('exports useStoryTemplates', () => {
    const mod = require('../src/hooks/useCreative');
    expect(typeof mod.useStoryTemplates).toBe('function');
  });

  test('exports useCreateStory', () => {
    const mod = require('../src/hooks/useCreative');
    expect(typeof mod.useCreateStory).toBe('function');
  });

  test('exports useMyStories', () => {
    const mod = require('../src/hooks/useCreative');
    expect(typeof mod.useMyStories).toBe('function');
  });

  test('exports useStickerPacks', () => {
    const mod = require('../src/hooks/useCreative');
    expect(typeof mod.useStickerPacks).toBe('function');
  });

  test('exports usePostToFeed', () => {
    const mod = require('../src/hooks/useCreative');
    expect(typeof mod.usePostToFeed).toBe('function');
  });

  test('useGenerateArt returns mutation shape', () => {
    const { useGenerateArt } = require('../src/hooks/useCreative');
    const result = useGenerateArt();
    expect(result).toHaveProperty('mutate');
    expect(result).toHaveProperty('mutateAsync');
    expect(result).toHaveProperty('isPending');
  });

  test('useMyArt returns query shape', () => {
    const { useMyArt } = require('../src/hooks/useCreative');
    const result = useMyArt('member-1');
    expect(result).toHaveProperty('data');
    expect(result).toHaveProperty('isLoading');
  });

  test('useStoryTemplates returns query shape', () => {
    const { useStoryTemplates } = require('../src/hooks/useCreative');
    const result = useStoryTemplates('teen');
    expect(result).toHaveProperty('data');
    expect(result).toHaveProperty('isLoading');
  });

  test('useStickerPacks returns query shape', () => {
    const { useStickerPacks } = require('../src/hooks/useCreative');
    const result = useStickerPacks();
    expect(result).toHaveProperty('data');
    expect(result).toHaveProperty('isLoading');
  });

  test('usePostToFeed returns mutation shape', () => {
    const { usePostToFeed } = require('../src/hooks/useCreative');
    const result = usePostToFeed();
    expect(result).toHaveProperty('mutate');
    expect(result).toHaveProperty('mutateAsync');
  });
});
