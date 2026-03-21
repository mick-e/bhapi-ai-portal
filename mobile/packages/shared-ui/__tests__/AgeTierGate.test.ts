import { checkTierPermission, getFeatureDescription, ageTierGateStyles } from '../src/AgeTierGate';
import { FEATURE_DESCRIPTIONS } from '@bhapi/config';

describe('AgeTierGate', () => {
  // -----------------------------------------------------------------------
  // checkTierPermission
  // -----------------------------------------------------------------------

  describe('checkTierPermission', () => {
    test('teen can_message returns true', () => {
      expect(checkTierPermission('teen', 'can_message')).toBe(true);
    });

    test('young can_message returns false', () => {
      expect(checkTierPermission('young', 'can_message')).toBe(false);
    });

    test('preteen can_message returns true', () => {
      expect(checkTierPermission('preteen', 'can_message')).toBe(true);
    });

    test('young can_post returns true (allowed for all)', () => {
      expect(checkTierPermission('young', 'can_post')).toBe(true);
    });

    test('young can_upload_video returns false', () => {
      expect(checkTierPermission('young', 'can_upload_video')).toBe(false);
    });

    test('preteen can_upload_video returns false', () => {
      expect(checkTierPermission('preteen', 'can_upload_video')).toBe(false);
    });

    test('teen can_upload_video returns true', () => {
      expect(checkTierPermission('teen', 'can_upload_video')).toBe(true);
    });

    test('young can_search_users returns false', () => {
      expect(checkTierPermission('young', 'can_search_users')).toBe(false);
    });

    test('preteen can_search_users returns true', () => {
      expect(checkTierPermission('preteen', 'can_search_users')).toBe(true);
    });

    test('young can_add_contacts returns false', () => {
      expect(checkTierPermission('young', 'can_add_contacts')).toBe(false);
    });

    test('preteen can_add_contacts returns true', () => {
      expect(checkTierPermission('preteen', 'can_add_contacts')).toBe(true);
    });

    test('young can_create_group_chat returns false', () => {
      expect(checkTierPermission('young', 'can_create_group_chat')).toBe(false);
    });

    test('preteen can_create_group_chat returns false', () => {
      expect(checkTierPermission('preteen', 'can_create_group_chat')).toBe(false);
    });

    test('teen can_create_group_chat returns true', () => {
      expect(checkTierPermission('teen', 'can_create_group_chat')).toBe(true);
    });

    test('can_share_location returns false for all tiers', () => {
      expect(checkTierPermission('young', 'can_share_location')).toBe(false);
      expect(checkTierPermission('preteen', 'can_share_location')).toBe(false);
      expect(checkTierPermission('teen', 'can_share_location')).toBe(false);
    });

    test('unknown permission returns false', () => {
      expect(checkTierPermission('teen', 'can_fly')).toBe(false);
    });
  });

  // -----------------------------------------------------------------------
  // getFeatureDescription
  // -----------------------------------------------------------------------

  describe('getFeatureDescription', () => {
    test('returns description for can_message', () => {
      const desc = getFeatureDescription('can_message');
      expect(desc).toBeDefined();
      expect(desc!.label).toBe('Messaging');
      expect(desc!.unlockAge).toBe(10);
      expect(desc!.parentCanUnlock).toBe(true);
    });

    test('returns description for can_upload_video', () => {
      const desc = getFeatureDescription('can_upload_video');
      expect(desc).toBeDefined();
      expect(desc!.label).toBe('Upload Video');
      expect(desc!.unlockAge).toBe(13);
      expect(desc!.parentCanUnlock).toBe(false);
    });

    test('returns undefined for unknown permission', () => {
      expect(getFeatureDescription('can_fly')).toBeUndefined();
    });

    test('can_search_users has correct unlock age', () => {
      const desc = getFeatureDescription('can_search_users');
      expect(desc!.unlockAge).toBe(10);
    });

    test('can_add_contacts has parentCanUnlock true', () => {
      const desc = getFeatureDescription('can_add_contacts');
      expect(desc!.parentCanUnlock).toBe(true);
    });

    test('can_create_group_chat has parentCanUnlock false', () => {
      const desc = getFeatureDescription('can_create_group_chat');
      expect(desc!.parentCanUnlock).toBe(false);
    });

    test('can_share_location has unlock age 16', () => {
      const desc = getFeatureDescription('can_share_location');
      expect(desc!.unlockAge).toBe(16);
    });
  });

  // -----------------------------------------------------------------------
  // Component rendering
  // -----------------------------------------------------------------------

  describe('AgeTierGate component', () => {
    test('exports AgeTierGate as a function', () => {
      const mod = require('../src/AgeTierGate');
      expect(mod.AgeTierGate).toBeDefined();
      expect(typeof mod.AgeTierGate).toBe('function');
    });

    test('renders children when permission is granted (teen, can_message)', () => {
      const { AgeTierGate } = require('../src/AgeTierGate');
      const child = { type: 'ChildContent', props: {} };
      const element = AgeTierGate({
        permission: 'can_message',
        ageTier: 'teen',
        children: child,
      });
      // When allowed, renders a Fragment wrapping children
      expect(element.props.children).toBe(child);
    });

    test('renders lock explanation when permission denied (young, can_message)', () => {
      const { AgeTierGate } = require('../src/AgeTierGate');
      const element = AgeTierGate({
        permission: 'can_message',
        ageTier: 'young',
        children: 'should not show',
      });
      // Should render a View with lock message, not children
      expect(element.type).toBe('View');
      expect(element.props.accessibilityLabel).toBe('Messaging is locked');
      // Children array should contain lock message text
      const children = Array.isArray(element.props.children) ? element.props.children : [element.props.children];
      const textElements = children.filter((c: any) => c && c.type === 'Text');
      const lockText = textElements.find((t: any) =>
        typeof t.props.children === 'string' && t.props.children.includes('Messaging unlocks at age 10')
      );
      expect(lockText).toBeDefined();
    });

    test('renders unlock request button for parent-unlockable features', () => {
      const { AgeTierGate } = require('../src/AgeTierGate');
      const onUnlock = jest.fn();
      const element = AgeTierGate({
        permission: 'can_message',
        ageTier: 'young',
        children: 'gated content',
        onUnlockRequest: onUnlock,
      });
      expect(element.type).toBe('View');
      const children = Array.isArray(element.props.children) ? element.props.children : [element.props.children];
      const askButton = children.find(
        (c: any) => c && c.type === 'TouchableOpacity' && c.props.accessibilityLabel === 'Ask parent to unlock'
      );
      expect(askButton).toBeDefined();
    });

    test('does not render unlock request button when parentCanUnlock is false', () => {
      const { AgeTierGate } = require('../src/AgeTierGate');
      const onUnlock = jest.fn();
      const element = AgeTierGate({
        permission: 'can_upload_video',
        ageTier: 'young',
        children: 'gated content',
        onUnlockRequest: onUnlock,
      });
      const children = Array.isArray(element.props.children) ? element.props.children : [element.props.children];
      const askButton = children.find(
        (c: any) => c && c.type === 'TouchableOpacity' && c.props?.accessibilityLabel === 'Ask parent to unlock'
      );
      expect(askButton).toBeFalsy();
    });

    test('does not render unlock request button when no onUnlockRequest provided', () => {
      const { AgeTierGate } = require('../src/AgeTierGate');
      const element = AgeTierGate({
        permission: 'can_message',
        ageTier: 'young',
        children: 'gated content',
      });
      const children = Array.isArray(element.props.children) ? element.props.children : [element.props.children];
      const askButton = children.find(
        (c: any) => c && c.type === 'TouchableOpacity' && c.props?.accessibilityLabel === 'Ask parent to unlock'
      );
      expect(askButton).toBeFalsy();
    });

    test('uses custom lockMessage when provided', () => {
      const { AgeTierGate } = require('../src/AgeTierGate');
      const element = AgeTierGate({
        permission: 'can_message',
        ageTier: 'young',
        children: 'gated content',
        lockMessage: 'Custom lock message',
      });
      const children = Array.isArray(element.props.children) ? element.props.children : [element.props.children];
      const customText = children.find(
        (c: any) => c && c.type === 'Text' && c.props.children === 'Custom lock message'
      );
      expect(customText).toBeDefined();
    });

    test('uses custom accessibilityLabel when provided', () => {
      const { AgeTierGate } = require('../src/AgeTierGate');
      const element = AgeTierGate({
        permission: 'can_message',
        ageTier: 'young',
        children: 'gated content',
        accessibilityLabel: 'Custom label',
      });
      expect(element.props.accessibilityLabel).toBe('Custom label');
    });

    test('renders unlock age hint for known features', () => {
      const { AgeTierGate } = require('../src/AgeTierGate');
      const element = AgeTierGate({
        permission: 'can_upload_video',
        ageTier: 'preteen',
        children: 'gated content',
      });
      const children = Array.isArray(element.props.children) ? element.props.children : [element.props.children];
      const unlockHint = children.find(
        (c: any) => c && c.type === 'Text' && typeof c.props.children === 'string' && c.props.children.includes('Unlocks at age 13')
      );
      expect(unlockHint).toBeDefined();
    });

    test('renders children when preteen has can_message permission', () => {
      const { AgeTierGate } = require('../src/AgeTierGate');
      const child = { type: 'Chat', props: {} };
      const element = AgeTierGate({
        permission: 'can_message',
        ageTier: 'preteen',
        children: child,
      });
      expect(element.props.children).toBe(child);
    });
  });

  // -----------------------------------------------------------------------
  // Styles export
  // -----------------------------------------------------------------------

  describe('ageTierGateStyles', () => {
    test('exports ageTierGateStyles', () => {
      expect(ageTierGateStyles).toBeDefined();
      expect(ageTierGateStyles.borderRadius).toBe(12);
    });

    test('has minHeight for WCAG compliance', () => {
      expect(ageTierGateStyles.minHeight).toBeGreaterThanOrEqual(44);
    });
  });

  // -----------------------------------------------------------------------
  // FEATURE_DESCRIPTIONS consistency
  // -----------------------------------------------------------------------

  describe('FEATURE_DESCRIPTIONS consistency', () => {
    test('all described features have lock messages', () => {
      for (const [key, desc] of Object.entries(FEATURE_DESCRIPTIONS)) {
        expect(desc.lockMessage).toBeTruthy();
        expect(desc.lockMessage.length).toBeGreaterThan(10);
      }
    });

    test('all described features have valid unlock ages', () => {
      for (const [key, desc] of Object.entries(FEATURE_DESCRIPTIONS)) {
        expect(desc.unlockAge).toBeGreaterThanOrEqual(10);
        expect(desc.unlockAge).toBeLessThanOrEqual(18);
      }
    });

    test('all described features have labels', () => {
      for (const [key, desc] of Object.entries(FEATURE_DESCRIPTIONS)) {
        expect(desc.label).toBeTruthy();
      }
    });
  });
});
