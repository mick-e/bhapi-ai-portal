import { messageBubbleStyles } from '../src/MessageBubble';
import { colors } from '@bhapi/config';

describe('MessageBubble', () => {
  test('exports MessageBubble component', () => {
    const mod = require('../src/MessageBubble');
    expect(mod.MessageBubble).toBeDefined();
    expect(typeof mod.MessageBubble).toBe('function');
  });

  test('exports messageBubbleStyles', () => {
    expect(messageBubbleStyles).toBeDefined();
    expect(messageBubbleStyles.sentBg).toBe(colors.primary[600]);
    expect(messageBubbleStyles.receivedBg).toBe(colors.neutral[100]);
  });

  test('renders sent message', () => {
    const { MessageBubble } = require('../src/MessageBubble');
    const element = MessageBubble({
      content: 'Hello!',
      timestamp: '10:30',
      isSent: true,
    });
    expect(element).toBeDefined();
    expect(element.props.accessibilityLabel).toBe('You said: Hello!');
  });

  test('renders received message with sender name', () => {
    const { MessageBubble } = require('../src/MessageBubble');
    const element = MessageBubble({
      content: 'Hi there!',
      timestamp: '10:31',
      isSent: false,
      senderName: 'Alice',
    });
    expect(element).toBeDefined();
    expect(element.props.accessibilityLabel).toBe('Alice said: Hi there!');
  });
});
