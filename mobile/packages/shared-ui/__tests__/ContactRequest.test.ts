import { contactRequestStyles } from '../src/ContactRequest';

describe('ContactRequest', () => {
  test('exports ContactRequest component', () => {
    const mod = require('../src/ContactRequest');
    expect(mod.ContactRequest).toBeDefined();
    expect(typeof mod.ContactRequest).toBe('function');
  });

  test('exports contactRequestStyles', () => {
    expect(contactRequestStyles).toBeDefined();
    expect(contactRequestStyles.borderRadius).toBe(8);
    expect(contactRequestStyles.minButtonHeight).toBe(44);
  });

  test('renders with required props', () => {
    const { ContactRequest } = require('../src/ContactRequest');
    const onAccept = jest.fn();
    const onReject = jest.fn();
    const element = ContactRequest({
      requesterName: 'Alice',
      requesterAvatarUrl: null,
      message: null,
      requiresParentApproval: false,
      onAccept,
      onReject,
    });
    expect(element).toBeDefined();
    expect(element.props.accessibilityLabel).toBe('Friend request from Alice');
  });

  test('renders with parent approval required', () => {
    const { ContactRequest } = require('../src/ContactRequest');
    const element = ContactRequest({
      requesterName: 'Bob',
      requesterAvatarUrl: null,
      message: 'Hi, can we be friends?',
      requiresParentApproval: true,
      onAccept: jest.fn(),
      onReject: jest.fn(),
    });
    expect(element).toBeDefined();
  });

  test('renders with custom accessibility label', () => {
    const { ContactRequest } = require('../src/ContactRequest');
    const element = ContactRequest({
      requesterName: 'Charlie',
      requesterAvatarUrl: null,
      message: null,
      requiresParentApproval: false,
      onAccept: jest.fn(),
      onReject: jest.fn(),
      accessibilityLabel: 'Custom request label',
    });
    expect(element.props.accessibilityLabel).toBe('Custom request label');
  });
});
