/**
 * Categorical color schemes used by chart plugins.
 *
 * Ports apache/superset's stock palettes (supersetColors, d3Category10,
 * bnbColors, googleCategory20c, lyftColors, airbnbColors). Plugins read
 * the active scheme from form_data.color_scheme and resolve it via
 * {@link getCategoricalScheme}.
 */
export interface CategoricalScheme {
  id: string;
  label: string;
  colors: string[];
  /** When true, palette is intended for dark backgrounds. */
  isDark?: boolean;
}

export const SUPERSET_COLORS: CategoricalScheme = {
  id: 'supersetColors',
  label: 'Superset Colors',
  colors: [
    '#1FA8C9', '#454E7C', '#5AC189', '#FF7F44', '#666666',
    '#E04355', '#FCC700', '#A868B7', '#3CCCCB', '#A38F79',
    '#8FD3E4', '#A1A6BD', '#ACE1C4', '#FEC0A1', '#B2B2B2',
    '#EFA1AA', '#FDE380', '#D3B3DA', '#9EE5E5', '#D1C6BC',
  ],
};

export const D3_CATEGORY_10: CategoricalScheme = {
  id: 'd3Category10',
  label: 'D3 Category 10',
  colors: [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
  ],
};

export const D3_CATEGORY_20: CategoricalScheme = {
  id: 'd3Category20',
  label: 'D3 Category 20',
  colors: [
    '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c',
    '#98df8a', '#d62728', '#ff9896', '#9467bd', '#c5b0d5',
    '#8c564b', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f',
    '#c7c7c7', '#bcbd22', '#dbdb8d', '#17becf', '#9edae5',
  ],
};

export const GOOGLE_CATEGORY_20C: CategoricalScheme = {
  id: 'googleCategory20c',
  label: 'Google Category 20c',
  colors: [
    '#3182bd', '#6baed6', '#9ecae1', '#c6dbef', '#e6550d',
    '#fd8d3c', '#fdae6b', '#fdd0a2', '#31a354', '#74c476',
    '#a1d99b', '#c7e9c0', '#756bb1', '#9e9ac8', '#bcbddc',
    '#dadaeb', '#636363', '#969696', '#bdbdbd', '#d9d9d9',
  ],
};

export const BNB_COLORS: CategoricalScheme = {
  id: 'bnbColors',
  label: 'Airbnb Colors',
  colors: [
    '#ff5a5f', '#7b0051', '#007a87', '#00d1c1', '#8ce071',
    '#ffb400', '#b4a76c', '#9ca299', '#565a5c', '#00a04b',
    '#e54c20',
  ],
};

export const LYFT_COLORS: CategoricalScheme = {
  id: 'lyftColors',
  label: 'Lyft Colors',
  colors: [
    '#EA0B8C', '#6C838E', '#29ABE2', '#33D9C1', '#9DACB9',
    '#7560AA', '#2D5584', '#831C4A', '#333D47', '#AC2077',
  ],
};

export const PRESET_COLORS: CategoricalScheme = {
  id: 'presetColors',
  label: 'Preset Colors',
  colors: [
    '#5A8AC6', '#FFC845', '#FF6F5C', '#7CD4E0', '#A57FB5',
    '#82C8A0', '#F4A261', '#264653', '#E76F51', '#2A9D8F',
  ],
};

export const ALL_SCHEMES: CategoricalScheme[] = [
  SUPERSET_COLORS,
  D3_CATEGORY_10,
  D3_CATEGORY_20,
  GOOGLE_CATEGORY_20C,
  BNB_COLORS,
  LYFT_COLORS,
  PRESET_COLORS,
];

const SCHEME_BY_ID: Record<string, CategoricalScheme> = ALL_SCHEMES.reduce(
  (acc, scheme) => {
    acc[scheme.id] = scheme;
    return acc;
  },
  {} as Record<string, CategoricalScheme>,
);

export const DEFAULT_CATEGORICAL_SCHEME = SUPERSET_COLORS;

export function getCategoricalScheme(id?: string): CategoricalScheme {
  if (!id) return DEFAULT_CATEGORICAL_SCHEME;
  return SCHEME_BY_ID[id] ?? DEFAULT_CATEGORICAL_SCHEME;
}

/**
 * Returns the n-th color from a scheme, wrapping around as needed.
 */
export function nthColor(scheme: CategoricalScheme, index: number): string {
  return scheme.colors[index % scheme.colors.length];
}
