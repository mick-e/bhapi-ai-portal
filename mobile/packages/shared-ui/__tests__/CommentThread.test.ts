import { commentThreadStyles } from '../src/CommentThread';
import { spacing } from '@bhapi/config';

describe('CommentThread', () => {
  test('exports CommentThread component', () => {
    const mod = require('../src/CommentThread');
    expect(mod.CommentThread).toBeDefined();
    expect(typeof mod.CommentThread).toBe('function');
  });

  test('exports commentThreadStyles', () => {
    expect(commentThreadStyles).toBeDefined();
    expect(commentThreadStyles.itemSpacing).toBe(spacing.sm);
  });

  test('renders empty state when no comments', () => {
    const { CommentThread } = require('../src/CommentThread');
    const element = CommentThread({ comments: [] });
    expect(element).toBeDefined();
    expect(element.props.accessibilityLabel).toBe('No comments');
  });

  test('renders with comments', () => {
    const { CommentThread } = require('../src/CommentThread');
    const comments = [
      { id: '1', authorName: 'Alice', content: 'Nice!', createdAt: '5m', isAuthor: false },
      { id: '2', authorName: 'Bob', content: 'Thanks', createdAt: '3m', isAuthor: true },
    ];
    const element = CommentThread({ comments });
    expect(element).toBeDefined();
    expect(element.props.accessibilityLabel).toBe('2 comments');
  });
});
