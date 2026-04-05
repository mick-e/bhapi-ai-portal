import React, { createContext, useContext, useEffect, useState } from 'react';
import { AccessibilityInfo, Platform } from 'react-native';

interface ContrastState { isHighContrast: boolean; }
const ContrastContext = createContext<ContrastState>({ isHighContrast: false });
export function useHighContrast(): ContrastState { return useContext(ContrastContext); }

export function ContrastProvider({ children }: { children: React.ReactNode }) {
  const [isHighContrast, setHighContrast] = useState(false);
  useEffect(() => {
    if (Platform.OS === 'android') {
      AccessibilityInfo.isAccessibilityServiceEnabled?.().then(setHighContrast);
    } else {
      AccessibilityInfo.isBoldTextEnabled().then(setHighContrast);
      const sub = AccessibilityInfo.addEventListener('boldTextChanged', setHighContrast);
      return () => sub.remove();
    }
  }, []);
  return React.createElement(ContrastContext.Provider, { value: { isHighContrast } }, children);
}
