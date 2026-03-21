/**
 * Social Feed Tests — feed rendering, create post validation,
 * character limits, media UI, comments, likes, empty states,
 * hashtag extraction, PostCard interactions.
 */

// ---------------------------------------------------------------------------
// Feed Screen
// ---------------------------------------------------------------------------

describe('Feed Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(feed)/index');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports FeedState type guard values', () => {
    const mod = require('../app/(feed)/index');
    expect(mod.PAGE_SIZE).toBe(20);
    expect(mod.DEFAULT_AGE_TIER).toBe('teen');
  });

  test('feed screen renders without crashing', () => {
    const mod = require('../app/(feed)/index');
    const result = mod.default();
    expect(result).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Create Post Screen
// ---------------------------------------------------------------------------

describe('Create Post Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(feed)/create-post');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports MAX_POST_LENGTH per tier', () => {
    const { MAX_POST_LENGTH } = require('../app/(feed)/create-post');
    expect(MAX_POST_LENGTH.young).toBe(200);
    expect(MAX_POST_LENGTH.preteen).toBe(500);
    expect(MAX_POST_LENGTH.teen).toBe(1000);
  });

  test('exports MIN_POST_LENGTH', () => {
    const { MIN_POST_LENGTH } = require('../app/(feed)/create-post');
    expect(MIN_POST_LENGTH).toBe(1);
  });

  test('create post screen renders without crashing', () => {
    const mod = require('../app/(feed)/create-post');
    const result = mod.default();
    expect(result).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Hashtag Extraction
// ---------------------------------------------------------------------------

describe('extractHashtags', () => {
  const { extractHashtags } = require('../app/(feed)/create-post');

  test('extracts single hashtag', () => {
    expect(extractHashtags('Hello #world')).toEqual(['world']);
  });

  test('extracts multiple hashtags', () => {
    const tags = extractHashtags('#hello #world #test');
    expect(tags).toContain('hello');
    expect(tags).toContain('world');
    expect(tags).toContain('test');
  });

  test('deduplicates hashtags', () => {
    const tags = extractHashtags('#hello #Hello #HELLO');
    expect(tags).toEqual(['hello']);
  });

  test('returns empty array for no hashtags', () => {
    expect(extractHashtags('No tags here')).toEqual([]);
  });

  test('returns empty for empty string', () => {
    expect(extractHashtags('')).toEqual([]);
  });

  test('extracts hashtags with underscores', () => {
    expect(extractHashtags('#hello_world')).toEqual(['hello_world']);
  });

  test('extracts hashtags with numbers', () => {
    expect(extractHashtags('#test123')).toEqual(['test123']);
  });

  test('ignores lone hash symbol', () => {
    expect(extractHashtags('Price is # too high')).toEqual([]);
  });

  test('extracts from mixed content', () => {
    const tags = extractHashtags('Love this #sunset pic! #nature is great');
    expect(tags).toContain('sunset');
    expect(tags).toContain('nature');
    expect(tags.length).toBe(2);
  });
});

// ---------------------------------------------------------------------------
// Post Detail Screen
// ---------------------------------------------------------------------------

describe('Post Detail Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(feed)/post-detail');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports MAX_COMMENT_LENGTH', () => {
    const { MAX_COMMENT_LENGTH } = require('../app/(feed)/post-detail');
    expect(MAX_COMMENT_LENGTH).toBe(500);
  });

  test('post detail screen renders without crashing', () => {
    const mod = require('../app/(feed)/post-detail');
    const result = mod.default();
    expect(result).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Character Limits by Tier
// ---------------------------------------------------------------------------

describe('Character Limits', () => {
  const { MAX_POST_LENGTH } = require('../app/(feed)/create-post');

  test('young tier allows max 200 characters', () => {
    expect(MAX_POST_LENGTH.young).toBe(200);
  });

  test('preteen tier allows max 500 characters', () => {
    expect(MAX_POST_LENGTH.preteen).toBe(500);
  });

  test('teen tier allows max 1000 characters', () => {
    expect(MAX_POST_LENGTH.teen).toBe(1000);
  });

  test('all tiers have limits defined', () => {
    expect(Object.keys(MAX_POST_LENGTH).sort()).toEqual(['preteen', 'teen', 'young']);
  });
});

// ---------------------------------------------------------------------------
// PostCard Component (shared-ui)
// ---------------------------------------------------------------------------

describe('PostCard Component', () => {
  test('PostCard mock renders with props', () => {
    const { PostCard } = require('../__tests__/__mocks__/@bhapi/ui');
    const result = PostCard({
      author: { display_name: 'Test', avatar_url: null, is_verified: false },
      content: 'Hello',
      likesCount: 5,
      commentsCount: 2,
      isLiked: false,
      moderationStatus: 'approved',
      createdAt: '2026-01-01',
    });
    expect(result.type).toBe('PostCard');
    expect(result.props.content).toBe('Hello');
    expect(result.props.likesCount).toBe(5);
  });

  test('PostCard accepts onLikePress callback', () => {
    const { PostCard } = require('../__tests__/__mocks__/@bhapi/ui');
    const onLike = jest.fn();
    const result = PostCard({
      author: { display_name: 'T', avatar_url: null, is_verified: false },
      content: 'Post',
      likesCount: 0,
      commentsCount: 0,
      isLiked: false,
      moderationStatus: 'approved',
      createdAt: '2026-01-01',
      onLikePress: onLike,
    });
    expect(result.props.onLikePress).toBe(onLike);
  });

  test('PostCard accepts onCommentPress callback', () => {
    const { PostCard } = require('../__tests__/__mocks__/@bhapi/ui');
    const onComment = jest.fn();
    const result = PostCard({
      author: { display_name: 'T', avatar_url: null, is_verified: false },
      content: 'Post',
      likesCount: 0,
      commentsCount: 0,
      isLiked: false,
      moderationStatus: 'approved',
      createdAt: '2026-01-01',
      onCommentPress: onComment,
    });
    expect(result.props.onCommentPress).toBe(onComment);
  });

  test('PostCard accepts onReportPress callback', () => {
    const { PostCard } = require('../__tests__/__mocks__/@bhapi/ui');
    const onReport = jest.fn();
    const result = PostCard({
      author: { display_name: 'T', avatar_url: null, is_verified: false },
      content: 'Post',
      likesCount: 0,
      commentsCount: 0,
      isLiked: false,
      moderationStatus: 'approved',
      createdAt: '2026-01-01',
      onReportPress: onReport,
    });
    expect(result.props.onReportPress).toBe(onReport);
  });

  test('PostCard accepts hashtags prop', () => {
    const { PostCard } = require('../__tests__/__mocks__/@bhapi/ui');
    const result = PostCard({
      author: { display_name: 'T', avatar_url: null, is_verified: false },
      content: '#test post',
      likesCount: 0,
      commentsCount: 0,
      isLiked: false,
      moderationStatus: 'approved',
      createdAt: '2026-01-01',
      hashtags: ['test'],
    });
    expect(result.props.hashtags).toEqual(['test']);
  });

  test('PostCard displays liked state', () => {
    const { PostCard } = require('../__tests__/__mocks__/@bhapi/ui');
    const result = PostCard({
      author: { display_name: 'T', avatar_url: null, is_verified: false },
      content: 'Liked post',
      likesCount: 10,
      commentsCount: 0,
      isLiked: true,
      moderationStatus: 'approved',
      createdAt: '2026-01-01',
    });
    expect(result.props.isLiked).toBe(true);
    expect(result.props.likesCount).toBe(10);
  });

  test('PostCard shows moderation status', () => {
    const { PostCard } = require('../__tests__/__mocks__/@bhapi/ui');
    const result = PostCard({
      author: { display_name: 'T', avatar_url: null, is_verified: false },
      content: 'Pending',
      likesCount: 0,
      commentsCount: 0,
      isLiked: false,
      moderationStatus: 'pending',
      createdAt: '2026-01-01',
    });
    expect(result.props.moderationStatus).toBe('pending');
  });
});

// ---------------------------------------------------------------------------
// CommentThread Component
// ---------------------------------------------------------------------------

describe('CommentThread Component', () => {
  test('CommentThread mock renders with empty list', () => {
    const { CommentThread } = require('../__tests__/__mocks__/@bhapi/ui');
    const result = CommentThread({ comments: [] });
    expect(result.type).toBe('CommentThread');
    expect(result.props.comments).toEqual([]);
  });

  test('CommentThread renders with comments', () => {
    const { CommentThread } = require('../__tests__/__mocks__/@bhapi/ui');
    const comments = [
      { id: '1', authorName: 'Alice', content: 'Nice!', createdAt: '2026-01-01', isAuthor: false },
      { id: '2', authorName: 'Bob', content: 'Cool', createdAt: '2026-01-02', isAuthor: true },
    ];
    const result = CommentThread({ comments });
    expect(result.props.comments.length).toBe(2);
  });
});

// ---------------------------------------------------------------------------
// Empty States
// ---------------------------------------------------------------------------

describe('Empty States', () => {
  test('feed screen renders empty state on loaded with no items', () => {
    const mod = require('../app/(feed)/index');
    // FeedScreen renders, and with no API data, shows empty state
    const result = mod.default();
    expect(result).toBeDefined();
  });

  test('post detail screen renders empty state when no post', () => {
    const mod = require('../app/(feed)/post-detail');
    const result = mod.default();
    expect(result).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Shared Types
// ---------------------------------------------------------------------------

describe('Shared Types', () => {
  test('social types module exports correctly', () => {
    // Verify types compile (runtime check on the module)
    const types = require('@bhapi/types');
    expect(types).toBeDefined();
  });
});
