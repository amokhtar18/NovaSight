/**
 * Chart styling tokens — typography, spacing, transitions — shared across
 * every plugin so the look-and-feel stays consistent regardless of which
 * underlying library a plugin uses (Recharts, ECharts, deck.gl, ...).
 */
export const CHART_FONT_FAMILY =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
export const CHART_MONO_FONT_FAMILY =
  '"JetBrains Mono", "Fira Code", Consolas, Menlo, monospace';

export const CHART_FONT_SIZES = {
  xs: 10,
  sm: 11,
  base: 12,
  md: 13,
  lg: 16,
  xl: 18,
  '2xl': 22,
  '3xl': 28,
  '4xl': 36,
  '5xl': 48,
} as const;

export const CHART_GRID_COLOR = 'rgba(0, 0, 0, 0.06)';
export const CHART_GRID_COLOR_DARK = 'rgba(255, 255, 255, 0.1)';
export const CHART_AXIS_COLOR = 'rgba(0, 0, 0, 0.45)';
export const CHART_AXIS_COLOR_DARK = 'rgba(255, 255, 255, 0.6)';
export const CHART_LABEL_COLOR = 'rgba(0, 0, 0, 0.85)';
export const CHART_LABEL_COLOR_DARK = 'rgba(255, 255, 255, 0.9)';

export const CHART_TOOLTIP_BACKGROUND = 'rgba(255, 255, 255, 0.96)';
export const CHART_TOOLTIP_BORDER = 'rgba(0, 0, 0, 0.08)';
export const CHART_TOOLTIP_SHADOW = '0 6px 24px rgba(0, 0, 0, 0.12)';

export const CHART_DEFAULT_MARGIN = { top: 16, right: 24, bottom: 36, left: 48 };
export const CHART_COMPACT_MARGIN = { top: 8, right: 12, bottom: 24, left: 36 };

export const CHART_ANIMATION_DURATION = 300;
export const CHART_ANIMATION_EASING = 'cubic-bezier(0.4, 0, 0.2, 1)';

export type ChartTheme = 'light' | 'dark';
