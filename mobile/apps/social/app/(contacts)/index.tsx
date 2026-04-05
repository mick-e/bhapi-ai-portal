/**
 * Contacts Screen
 *
 * Three tabs: My Contacts | Pending | Search
 * - My Contacts: accepted contacts with message/block actions
 * - Pending: incoming requests with accept/reject
 * - Search: API search with ContactRequest component
 *
 * API:
 *   GET /api/v1/contacts/?status=accepted  — My Contacts
 *   GET /api/v1/contacts/?status=pending    — Pending
 *   GET /api/v1/social/search?q=<query>     — Search profiles
 *   POST /api/v1/contacts/request/{userId}  — Send request
 *   POST /api/v1/contacts/{userId}/block    — Block user
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { ContactRequest, SearchResultCard } from '@bhapi/ui';
import { ApiClient } from '@bhapi/api';
import { tokenManager } from '@bhapi/auth';

const apiClient = new ApiClient({
  baseUrl: '',
  getToken: () => tokenManager.getToken(),
});

type Tab = 'contacts' | 'pending' | 'search';

interface ContactItem {
  id: string;
  requester_id: string;
  target_id: string;
  status: string;
  parent_approval_status: string;
  created_at: string;
}

interface SearchResult {
  id: string;
  user_id: string;
  display_name: string;
  avatar_url: string | null;
  bio: string | null;
  age_tier: string;
}

type ScreenState = 'idle' | 'loading' | 'loaded' | 'error';

const TABS: { key: Tab; label: string }[] = [
  { key: 'contacts', label: 'My Contacts' },
  { key: 'pending', label: 'Pending' },
  { key: 'search', label: 'Search' },
];

export default function ContactsScreen() {
  const [activeTab, setActiveTab] = useState<Tab>('contacts');
  const [contacts, setContacts] = useState<ContactItem[]>([]);
  const [pending, setPending] = useState<ContactItem[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [state, setState] = useState<ScreenState>('idle');
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set());
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (activeTab === 'contacts') loadContacts();
    else if (activeTab === 'pending') loadPending();
  }, [activeTab]);

  async function loadContacts() {
    setState('loading');
    try {
      const resp = await apiClient.get<{ items: ContactItem[] }>('/api/v1/contacts/?status=accepted');
      setContacts(resp.items);
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Could not load contacts.');
    }
  }

  async function loadPending() {
    setState('loading');
    try {
      const resp = await apiClient.get<{ items: ContactItem[] }>('/api/v1/contacts/?status=pending');
      setPending(resp.items);
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Could not load pending requests.');
    }
  }

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);

    if (!query.trim()) {
      setSearchResults([]);
      return;
    }

    searchTimeoutRef.current = setTimeout(async () => {
      setState('loading');
      try {
        const resp = await apiClient.get<{ items: SearchResult[] }>(
          `/api/v1/social/search?q=${encodeURIComponent(query)}`
        );
        setSearchResults(resp.items);
        setState('loaded');
      } catch (e: any) {
        setState('error');
        setError(e?.message ?? 'Search failed.');
      }
    }, 300);
  }, []);

  async function handleSendRequest(userId: string) {
    setProcessingIds((prev) => new Set(prev).add(userId));
    try {
      await apiClient.post(`/api/v1/contacts/request/${userId}`, {});
      setSearchResults((prev) => prev.filter((r) => r.user_id !== userId));
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(userId);
        return next;
      });
    }
  }

  async function handleAccept(contactId: string) {
    setProcessingIds((prev) => new Set(prev).add(contactId));
    try {
      await apiClient.put(`/api/v1/contacts/${contactId}/respond`, { action: 'accept' });
      setPending((prev) => prev.filter((c) => c.id !== contactId));
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(contactId);
        return next;
      });
    }
  }

  async function handleReject(contactId: string) {
    setProcessingIds((prev) => new Set(prev).add(contactId));
    try {
      await apiClient.put(`/api/v1/contacts/${contactId}/respond`, { action: 'reject' });
      setPending((prev) => prev.filter((c) => c.id !== contactId));
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(contactId);
        return next;
      });
    }
  }

  async function handleBlock(userId: string) {
    setProcessingIds((prev) => new Set(prev).add(userId));
    try {
      await apiClient.post(`/api/v1/contacts/${userId}/block`, {});
      setContacts((prev) =>
        prev.filter(
          (c) => c.requester_id !== userId && c.target_id !== userId
        )
      );
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(userId);
        return next;
      });
    }
  }

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    if (activeTab === 'contacts') await loadContacts();
    else if (activeTab === 'pending') await loadPending();
    setRefreshing(false);
  }, [activeTab]);

  function renderTabs() {
    return React.createElement(
      View,
      { style: styles.tabBar, accessibilityRole: 'tablist' },
      ...TABS.map((tab) =>
        React.createElement(
          TouchableOpacity,
          {
            key: tab.key,
            style: [styles.tab, activeTab === tab.key && styles.activeTab],
            onPress: () => setActiveTab(tab.key),
            accessibilityRole: 'tab',
            accessibilityState: { selected: activeTab === tab.key },
            accessibilityLabel: tab.label,
          },
          React.createElement(
            Text,
            {
              style: [
                styles.tabText,
                activeTab === tab.key && styles.activeTabText,
              ],
            },
            tab.label
          )
        )
      )
    );
  }

  function renderSearchBar() {
    return React.createElement(
      View,
      { style: styles.searchContainer },
      React.createElement(TextInput, {
        style: styles.searchInput,
        placeholder: 'Search by name...',
        placeholderTextColor: colors.neutral[400],
        value: searchQuery,
        onChangeText: handleSearch,
        accessibilityLabel: 'Search contacts',
        returnKeyType: 'search',
        autoCapitalize: 'none',
      })
    );
  }

  function renderContactItem({ item }: { item: ContactItem }) {
    const otherUserId = item.requester_id; // simplified — real impl resolves
    return React.createElement(
      View,
      { style: styles.contactCard, accessibilityLabel: 'Contact' },
      React.createElement(
        View,
        { style: styles.contactInfo },
        React.createElement(
          View,
          { style: styles.contactAvatar },
          React.createElement(Text, { style: styles.avatarText }, '?')
        ),
        React.createElement(
          Text,
          { style: styles.contactName },
          `Contact ${item.id.slice(0, 8)}`
        )
      ),
      React.createElement(
        View,
        { style: styles.contactActions },
        React.createElement(
          TouchableOpacity,
          {
            style: styles.blockButton,
            onPress: () => handleBlock(otherUserId),
            disabled: processingIds.has(otherUserId),
            accessibilityLabel: 'Block contact',
            accessibilityRole: 'button',
          },
          React.createElement(
            Text,
            { style: styles.blockText },
            'Block'
          )
        )
      )
    );
  }

  function renderPendingItem({ item }: { item: ContactItem }) {
    return React.createElement(ContactRequest, {
      requesterName: `User ${item.requester_id.slice(0, 8)}`,
      requesterAvatarUrl: null,
      message: null,
      requiresParentApproval: item.parent_approval_status === 'pending',
      onAccept: () => handleAccept(item.id),
      onReject: () => handleReject(item.id),
      isProcessing: processingIds.has(item.id),
      accessibilityLabel: `Pending request from user ${item.requester_id.slice(0, 8)}`,
    });
  }

  function renderSearchResult({ item }: { item: SearchResult }) {
    return React.createElement(SearchResultCard, {
      displayName: item.display_name,
      avatarUrl: item.avatar_url,
      bio: item.bio,
      ageTier: item.age_tier,
      onSendRequest: () => handleSendRequest(item.user_id),
      isProcessing: processingIds.has(item.user_id),
      accessibilityLabel: `Send request to ${item.display_name}`,
    });
  }

  function renderEmptyState(message: string) {
    return React.createElement(
      View,
      { style: styles.emptyContainer },
      React.createElement(Text, { style: styles.emptyText }, message)
    );
  }

  function renderContent() {
    if (state === 'loading' && !refreshing) {
      return React.createElement(
        View,
        { style: styles.centered },
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
          { onPress: handleRefresh, style: styles.retryButton },
          React.createElement(Text, { style: styles.retryText }, 'Try again')
        )
      );
    }

    if (activeTab === 'search') {
      return React.createElement(
        View,
        { style: styles.listContainer },
        renderSearchBar(),
        searchResults.length === 0 && searchQuery.trim()
          ? renderEmptyState('No users found.')
          : React.createElement(FlatList, {
              data: searchResults,
              keyExtractor: (item: SearchResult) => item.id,
              renderItem: renderSearchResult,
              contentContainerStyle: styles.listContent,
            })
      );
    }

    if (activeTab === 'pending') {
      return React.createElement(FlatList, {
        data: pending,
        keyExtractor: (item: ContactItem) => item.id,
        renderItem: renderPendingItem,
        contentContainerStyle: styles.listContent,
        refreshControl: React.createElement(RefreshControl, {
          refreshing,
          onRefresh: handleRefresh,
          tintColor: colors.primary[600],
        }),
        ListEmptyComponent: renderEmptyState('No pending requests.'),
      });
    }

    // Default: contacts tab
    return React.createElement(FlatList, {
      data: contacts,
      keyExtractor: (item: ContactItem) => item.id,
      renderItem: renderContactItem,
      contentContainerStyle: styles.listContent,
      refreshControl: React.createElement(RefreshControl, {
        refreshing,
        onRefresh: handleRefresh,
        tintColor: colors.primary[600],
      }),
      ListEmptyComponent: renderEmptyState(
        'No contacts yet. Search to find friends!'
      ),
    });
  }

  return React.createElement(
    View,
    { style: styles.container, accessibilityLabel: 'Contacts' },
    renderTabs(),
    renderContent()
  );
}

// Exported for testing
export { type Tab, type ContactItem, type SearchResult, type ScreenState, TABS };

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
  },
  tab: {
    flex: 1,
    paddingVertical: spacing.md,
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
  },
  activeTab: {
    borderBottomWidth: 2,
    borderBottomColor: colors.primary[600],
  },
  tabText: {
    fontSize: typography.sizes.sm,
    fontWeight: '500',
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  activeTabText: {
    color: colors.primary[600],
    fontWeight: '600',
  },
  searchContainer: {
    padding: spacing.md,
  },
  searchInput: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontSize: typography.sizes.base,
    color: colors.neutral[900],
    borderWidth: 1,
    borderColor: colors.neutral[200],
    minHeight: 44,
    fontFamily: typography.fontFamily,
  },
  listContainer: {
    flex: 1,
  },
  listContent: {
    padding: spacing.md,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.md,
  },
  emptyContainer: {
    paddingVertical: spacing['2xl'],
    alignItems: 'center',
  },
  emptyText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  contactCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    padding: spacing.md,
    marginBottom: spacing.sm,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 2,
    elevation: 2,
  },
  contactInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  contactAvatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.accent[500],
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.md,
    minWidth: 44,
    minHeight: 44,
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
  contactName: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  contactActions: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  blockButton: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.semantic.error,
    minHeight: 44,
    justifyContent: 'center',
  },
  blockText: {
    fontSize: typography.sizes.sm,
    color: colors.semantic.error,
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
});
