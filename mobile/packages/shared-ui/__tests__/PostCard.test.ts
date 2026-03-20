import { postCardStyles } from '../src/PostCard';
import { colors, spacing } from '@bhapi/config';

describe('PostCard', () => {
  test('exports PostCard component', () => {
    const mod = require('../src/PostCard');
    expect(mod.PostCard).toBeDefined();
    expect(typeof mod.PostCard).toBe('function');
  });

  test('exports postCardStyles', () => {
    expect(postCardStyles).toBeDefined();
    expect(postCardStyles.borderRadius).toBe(8);
    expect(postCardStyles.padding).toBe(spacing.md);
  });

  test('PostCard renders with required props', () => {
    const { PostCard } = require('../src/PostCard');
    const element = PostCard({
      author: { display_name: 'Alice', avatar_url: null, is_verified: false },
      content: 'Hello world',
      likesCount: 5,
      commentsCount: 2,
      isLiked: false,
      moderationStatus: 'approved',
      createdAt: '2026-03-20',
    });
    expect(element).toBeDefined();
    expect(element.props.accessibilityLabel).toBe('Post by Alice');
  });

  test('PostCard shows moderation badge when not approved', () => {
    const { PostCard } = require('../src/PostCard');
    const element = PostCard({
      author: { display_name: 'Bob', avatar_url: null, is_verified: true },
      content: 'Test',
      likesCount: 0,
      commentsCount: 0,
      isLiked: false,
      moderationStatus: 'pending',
      createdAt: '2026-03-20',
    });
    expect(element).toBeDefined();
  });

  test('PostCard with custom accessibilityLabel', () => {
    const { PostCard } = require('../src/PostCard');
    const element = PostCard({
      author: { display_name: 'Charlie', avatar_url: null, is_verified: false },
      content: 'Content',
      likesCount: 1,
      commentsCount: 0,
      isLiked: true,
      moderationStatus: 'approved',
      createdAt: '2026-03-20',
      accessibilityLabel: 'Custom label',
    });
    expect(element.props.accessibilityLabel).toBe('Custom label');
  });
});
