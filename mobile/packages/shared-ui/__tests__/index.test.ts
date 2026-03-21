import { UI_VERSION } from '../src';

describe('shared-ui', () => {
  test('exports version 0.4.0', () => {
    expect(UI_VERSION).toBe('0.4.0');
  });

  test('exports all social components', () => {
    const mod = require('../src');
    expect(mod.PostCard).toBeDefined();
    expect(mod.CommentThread).toBeDefined();
    expect(mod.MessageBubble).toBeDefined();
    expect(mod.ContactRequest).toBeDefined();
    expect(mod.ReportDialog).toBeDefined();
  });

  test('exports all social style helpers', () => {
    const mod = require('../src');
    expect(mod.postCardStyles).toBeDefined();
    expect(mod.commentThreadStyles).toBeDefined();
    expect(mod.messageBubbleStyles).toBeDefined();
    expect(mod.contactRequestStyles).toBeDefined();
    expect(mod.reportDialogStyles).toBeDefined();
    expect(mod.DEFAULT_REPORT_REASONS).toBeDefined();
  });

  test('exports original components', () => {
    const mod = require('../src');
    expect(mod.Button).toBeDefined();
    expect(mod.Card).toBeDefined();
    expect(mod.Input).toBeDefined();
    expect(mod.Badge).toBeDefined();
    expect(mod.Avatar).toBeDefined();
    expect(mod.Toast).toBeDefined();
    expect(mod.BhapiLogo).toBeDefined();
  });
});
