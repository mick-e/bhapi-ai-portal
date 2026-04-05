import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = 'bhapi_dyslexia_font';

interface FontState {
  isDyslexic: boolean;
  fontFamily: string;
  toggleDyslexiaFont: () => void;
}

const FontContext = createContext<FontState>({ isDyslexic: false, fontFamily: 'System', toggleDyslexiaFont: () => {} });
export function useDyslexiaFont(): FontState { return useContext(FontContext); }

export function FontProvider({ children }: { children: React.ReactNode }) {
  const [isDyslexic, setDyslexic] = useState(false);
  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then((val) => { if (val === 'true') setDyslexic(true); });
  }, []);
  const toggleDyslexiaFont = useCallback(() => {
    setDyslexic((prev) => { const next = !prev; AsyncStorage.setItem(STORAGE_KEY, String(next)); return next; });
  }, []);
  const fontFamily = isDyslexic ? 'OpenDyslexic' : 'System';
  return React.createElement(FontContext.Provider, { value: { isDyslexic, fontFamily, toggleDyslexiaFont } }, children);
}
