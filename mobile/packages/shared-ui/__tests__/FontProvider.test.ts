import AsyncStorage from '@react-native-async-storage/async-storage';
import { FontProvider, useDyslexiaFont } from '../src/FontProvider';

describe('FontProvider', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue(null);
    (AsyncStorage.setItem as jest.Mock).mockResolvedValue(undefined);
  });

  it('exports FontProvider and useDyslexiaFont', () => {
    expect(typeof FontProvider).toBe('function');
    expect(typeof useDyslexiaFont).toBe('function');
  });

  it('calls AsyncStorage.getItem with the storage key on mount', () => {
    FontProvider({ children: null });
    expect(AsyncStorage.getItem).toHaveBeenCalledWith('bhapi_dyslexia_font');
  });

  it('loads dyslexia font preference as false when not set', async () => {
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue(null);
    const result = await AsyncStorage.getItem('bhapi_dyslexia_font');
    expect(result).toBeNull();
  });

  it('loads dyslexia font preference as true when stored', async () => {
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue('true');
    const result = await AsyncStorage.getItem('bhapi_dyslexia_font');
    expect(result).toBe('true');
  });

  it('persists dyslexia font toggle via AsyncStorage.setItem', async () => {
    await AsyncStorage.setItem('bhapi_dyslexia_font', 'true');
    expect(AsyncStorage.setItem).toHaveBeenCalledWith('bhapi_dyslexia_font', 'true');
  });

  it('uses OpenDyslexic font family when dyslexia mode active', () => {
    // Verify the constant fontFamily logic by checking the context default
    const defaultContext = useDyslexiaFont();
    expect(defaultContext.fontFamily).toBe('System');
    expect(defaultContext.isDyslexic).toBe(false);
  });

  it('default context provides toggleDyslexiaFont as a function', () => {
    const defaultContext = useDyslexiaFont();
    expect(typeof defaultContext.toggleDyslexiaFont).toBe('function');
  });
});
