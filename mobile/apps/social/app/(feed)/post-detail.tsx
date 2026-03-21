/**
 * Post Detail Screen
 *
 * Full post view with author info, like button, comment list,
 * add comment input, and report button.
 *
 * API: GET /api/v1/social/posts/{id}
 *      GET /api/v1/social/posts/{id}/comments
 *      POST /api/v1/social/posts/{id}/like
 *      DELETE /api/v1/social/posts/{id}/like
 *      POST /api/v1/social/posts/{id}/comments
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { PostCard, CommentThread } from '@bhapi/ui';
import type { CommentItem } from '@bhapi/ui';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PostDetailData {
  id: string;
  author_id: string;
  content: string;
  media_urls: string[];
  likes_count: number;
  comments_count: number;
  is_liked: boolean;
  moderation_status: 'pending' | 'approved' | 'rejected' | 'flagged';
  created_at: string;
  author: {
    id: string;
    display_name: string;
    avatar_url: string | null;
    is_verified: boolean;
  };
}

interface CommentData {
  id: string;
  author_id: string;
  author_name: string;
  content: string;
  moderation_status: string;
  created_at: string;
}

type ScreenState = 'loading' | 'loaded' | 'error';

export const MAX_COMMENT_LENGTH = 500;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PostDetailScreen() {
  const [post, setPost] = useState<PostDetailData | null>(null);
  const [comments, setComments] = useState<CommentData[]>([]);
  const [state, setState] = useState<ScreenState>('loading');
  const [error, setError] = useState('');
  const [commentText, setCommentText] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);
  const [reportSent, setReportSent] = useState(false);

  // In production, postId comes from route params
  const postId: string | null = null;

  useEffect(() => {
    if (postId) loadPost();
    else setState('loaded'); // No postId means placeholder mode
  }, [postId]);

  async function loadPost() {
    try {
      setState('loading');
      // const postData = await apiClient.get<PostDetailData>(
      //   `/api/v1/social/posts/${postId}`
      // );
      // setPost(postData);
      // const commentData = await apiClient.get<{ items: CommentData[] }>(
      //   `/api/v1/social/posts/${postId}/comments`
      // );
      // setComments(commentData.items);
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Could not load post.');
    }
  }

  async function handleLike() {
    if (!post) return;
    const wasLiked = post.is_liked;

    // Optimistic update
    setPost({
      ...post,
      is_liked: !wasLiked,
      likes_count: wasLiked ? post.likes_count - 1 : post.likes_count + 1,
    });

    // API call:
    // if (wasLiked) await apiClient.delete(`/api/v1/social/posts/${post.id}/like`);
    // else await apiClient.post(`/api/v1/social/posts/${post.id}/like`);
  }

  async function handleSubmitComment() {
    if (!post || !commentText.trim() || submittingComment) return;
    setSubmittingComment(true);

    try {
      // const newComment = await apiClient.post<CommentData>(
      //   `/api/v1/social/posts/${post.id}/comments`,
      //   { content: commentText.trim() }
      // );
      // setComments((prev) => [...prev, newComment]);
      setCommentText('');
      setPost({
        ...post,
        comments_count: post.comments_count + 1,
      });
    } catch (e: any) {
      // Show error toast
    } finally {
      setSubmittingComment(false);
    }
  }

  function handleReport() {
    // API: POST /api/v1/social/posts/{id}/report
    setReportSent(true);
  }

  if (state === 'loading') {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading post' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
  }

  if (state === 'error') {
    return React.createElement(
      View,
      { style: styles.centered },
      React.createElement(
        Text,
        { style: styles.errorText, accessibilityRole: 'alert' },
        error
      ),
      React.createElement(
        TouchableOpacity,
        { onPress: loadPost, style: styles.retryButton },
        React.createElement(Text, { style: styles.retryText }, 'Try again')
      )
    );
  }

  if (!post) {
    return React.createElement(
      View,
      { style: styles.centered },
      React.createElement(
        Text,
        { style: styles.emptyText },
        'No post selected.'
      )
    );
  }

  const commentItems: CommentItem[] = comments.map((c) => ({
    id: c.id,
    authorName: c.author_name,
    content: c.content,
    createdAt: c.created_at,
    isAuthor: false,
  }));

  return React.createElement(
    KeyboardAvoidingView,
    {
      style: styles.container,
      behavior: Platform.OS === 'ios' ? 'padding' : undefined,
    },
    React.createElement(
      ScrollView,
      {
        style: styles.scrollView,
        contentContainerStyle: styles.scrollContent,
        keyboardShouldPersistTaps: 'handled',
      },
      // Post card
      React.createElement(PostCard, {
        author: {
          display_name: post.author.display_name,
          avatar_url: post.author.avatar_url,
          is_verified: post.author.is_verified,
        },
        content: post.content,
        likesCount: post.likes_count,
        commentsCount: post.comments_count,
        isLiked: post.is_liked,
        moderationStatus: post.moderation_status,
        createdAt: post.created_at,
        onLikePress: handleLike,
      }),

      // Report button
      React.createElement(
        TouchableOpacity,
        {
          style: styles.reportButton,
          onPress: handleReport,
          disabled: reportSent,
          accessibilityLabel: reportSent ? 'Report sent' : 'Report post',
          accessibilityRole: 'button',
        },
        React.createElement(
          Text,
          { style: styles.reportButtonText },
          reportSent ? 'Report Sent' : 'Report Post'
        )
      ),

      // Comments section
      React.createElement(
        View,
        { style: styles.commentsSection },
        React.createElement(
          Text,
          { style: styles.sectionTitle },
          `Comments (${post.comments_count})`
        ),
        React.createElement(CommentThread, {
          comments: commentItems,
          accessibilityLabel: `${post.comments_count} comments`,
        })
      ),

      // Add comment input
      React.createElement(
        View,
        { style: styles.addCommentRow },
        React.createElement(TextInput, {
          style: styles.commentInput,
          placeholder: 'Add a comment...',
          placeholderTextColor: colors.neutral[400],
          value: commentText,
          onChangeText: setCommentText,
          maxLength: MAX_COMMENT_LENGTH,
          accessibilityLabel: 'Comment input',
          testID: 'comment-input',
        }),
        React.createElement(
          TouchableOpacity,
          {
            style: [
              styles.sendButton,
              !commentText.trim() ? styles.sendButtonDisabled : null,
            ],
            onPress: handleSubmitComment,
            disabled: !commentText.trim() || submittingComment,
            accessibilityLabel: 'Send comment',
            accessibilityRole: 'button',
          },
          submittingComment
            ? React.createElement(ActivityIndicator, {
                size: 'small',
                color: '#FFFFFF',
              })
            : React.createElement(
                Text,
                { style: styles.sendButtonText },
                'Send'
              )
        )
      )
    )
  );
}

// Exported for testing
export { type ScreenState };

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: spacing.md,
    paddingBottom: spacing['2xl'],
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.neutral[50],
    padding: spacing.md,
  },
  reportButton: {
    alignSelf: 'flex-end',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    minHeight: 36,
    justifyContent: 'center',
  },
  reportButtonText: {
    fontSize: typography.sizes.sm,
    color: colors.semantic.error,
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  commentsSection: {
    marginTop: spacing.md,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.neutral[900],
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  addCommentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: spacing.md,
    gap: spacing.sm,
  },
  commentInput: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    padding: spacing.sm,
    fontSize: typography.sizes.base,
    color: colors.neutral[900],
    minHeight: 44,
    fontFamily: typography.fontFamily,
  },
  sendButton: {
    backgroundColor: colors.primary[600],
    borderRadius: 8,
    paddingHorizontal: spacing.md,
    minHeight: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sendButtonDisabled: {
    opacity: 0.5,
  },
  sendButtonText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.base,
    textAlign: 'center',
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  retryButton: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
  },
  retryText: {
    color: colors.primary[700],
    fontSize: typography.sizes.base,
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  emptyText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
});
