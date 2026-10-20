import React, { createContext, useContext, useEffect, useState } from 'react';

export type Theme = 'dark' | 'light';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

export const resolveInitialTheme = (savedTheme?: string | null): Theme => {
  if (savedTheme === 'dark' || savedTheme === 'light') {
    return savedTheme;
  }
  // Default to dark for cybersecurity platform aesthetic
  return 'dark';
};

export const applyThemeToElement = (
  theme: Theme,
  el: { classList: { add: (cls: string) => void; remove: (cls: string) => void } }
) => {
  if (theme === 'dark') {
    el.classList.add('dark');
    el.classList.remove('light');
  } else {
    el.classList.remove('dark');
    el.classList.add('light');
  }
};

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('agentguard_theme');
      return resolveInitialTheme(saved);
    }
    return 'dark';
  });

  useEffect(() => {
    if (typeof document !== 'undefined') {
      applyThemeToElement(theme, document.documentElement);
    }
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('agentguard_theme', theme);
    }
  }, [theme]);

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
