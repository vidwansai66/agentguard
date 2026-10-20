import React from 'react';
import { useTheme } from '../../context/ThemeContext';

interface ThemeToggleProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  id?: string;
}

/**
 * Animated Sun/Moon theme toggle switch based on Uiverse.io by JkHuger.
 * Uses em-based CSS metrics for seamless scaling across UI contexts.
 */
export const ThemeToggle: React.FC<ThemeToggleProps> = ({
  size = 'sm',
  className = '',
  id = 'theme-toggle',
}) => {
  const { theme, toggleTheme } = useTheme();

  // Em scale factor for toggle size
  const fontSize = size === 'sm' ? '7.5px' : size === 'md' ? '9.5px' : '11.5px';

  return (
    <label
      htmlFor={id}
      className={`theme cursor-pointer select-none inline-flex items-center ${className}`}
      style={{ fontSize }}
      title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
      aria-label="Toggle dark mode"
    >
      <span className="theme__toggle-wrap">
        <input
          id={id}
          className="theme__toggle"
          type="checkbox"
          role="switch"
          checked={theme === 'dark'}
          onChange={toggleTheme}
        />
        <span className="theme__icon">
          <span className="theme__icon-part" />
          <span className="theme__icon-part" />
          <span className="theme__icon-part" />
          <span className="theme__icon-part" />
          <span className="theme__icon-part" />
          <span className="theme__icon-part" />
          <span className="theme__icon-part" />
          <span className="theme__icon-part" />
          <span className="theme__icon-part" />
        </span>
      </span>
    </label>
  );
};
