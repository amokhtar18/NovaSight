/**
 * Shared ECharts utilities — keep all plugins on a single visual language
 * (typography, axis colors, animations) regardless of chart family.
 */
import type { CSSProperties } from 'react';
import {
  CHART_ANIMATION_DURATION,
  CHART_AXIS_COLOR,
  CHART_AXIS_COLOR_DARK,
  CHART_FONT_FAMILY,
  CHART_GRID_COLOR,
  CHART_GRID_COLOR_DARK,
  CHART_LABEL_COLOR,
  CHART_LABEL_COLOR_DARK,
  CHART_TOOLTIP_BACKGROUND,
  CHART_TOOLTIP_BORDER,
  CHART_TOOLTIP_SHADOW,
} from '../styling/theme';

export interface EChartsThemeTokens {
  textColor: string;
  axisColor: string;
  gridColor: string;
  fontFamily: string;
  tooltipBackground: string;
  tooltipBorder: string;
  tooltipShadow: string;
}

export function getEChartsTokens(isDark = false): EChartsThemeTokens {
  return {
    textColor: isDark ? CHART_LABEL_COLOR_DARK : CHART_LABEL_COLOR,
    axisColor: isDark ? CHART_AXIS_COLOR_DARK : CHART_AXIS_COLOR,
    gridColor: isDark ? CHART_GRID_COLOR_DARK : CHART_GRID_COLOR,
    fontFamily: CHART_FONT_FAMILY,
    tooltipBackground: isDark
      ? 'rgba(20, 20, 26, 0.96)'
      : CHART_TOOLTIP_BACKGROUND,
    tooltipBorder: CHART_TOOLTIP_BORDER,
    tooltipShadow: CHART_TOOLTIP_SHADOW,
  };
}

export function baseTextStyle(isDark = false) {
  const t = getEChartsTokens(isDark);
  return {
    color: t.textColor,
    fontFamily: t.fontFamily,
    fontSize: 12,
  };
}

export function baseAxisStyle(isDark = false) {
  const t = getEChartsTokens(isDark);
  return {
    axisLine: { lineStyle: { color: t.axisColor } },
    axisTick: { lineStyle: { color: t.axisColor } },
    axisLabel: {
      color: t.textColor,
      fontFamily: t.fontFamily,
      fontSize: 11,
    },
    splitLine: { lineStyle: { color: t.gridColor } },
  };
}

export function baseTooltip(isDark = false, formatter?: unknown) {
  const t = getEChartsTokens(isDark);
  return {
    trigger: 'item' as const,
    backgroundColor: t.tooltipBackground,
    borderColor: t.tooltipBorder,
    borderWidth: 1,
    extraCssText: `box-shadow: ${t.tooltipShadow}; border-radius: 6px;`,
    textStyle: {
      color: t.textColor,
      fontFamily: t.fontFamily,
      fontSize: 12,
    },
    ...(formatter ? { formatter } : {}),
  };
}

export function baseLegend(isDark = false) {
  const t = getEChartsTokens(isDark);
  return {
    textStyle: {
      color: t.textColor,
      fontFamily: t.fontFamily,
      fontSize: 11,
    },
    bottom: 0,
  };
}

export const BASE_ANIMATION = {
  animation: true,
  animationDuration: CHART_ANIMATION_DURATION,
  animationEasing: 'cubicOut' as const,
};

export const ECHARTS_STYLE: CSSProperties = {
  width: '100%',
  height: '100%',
};
