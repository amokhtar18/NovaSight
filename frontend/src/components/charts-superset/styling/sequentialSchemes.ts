/**
 * Sequential & diverging schemes for heatmaps, choropleths, and gauge ranges.
 * Ported from apache/superset (sequential / linear palettes).
 */
export interface SequentialScheme {
  id: string;
  label: string;
  colors: string[];
  isDiverging?: boolean;
}

export const BLUES: SequentialScheme = {
  id: 'blues',
  label: 'Blues',
  colors: ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#08519c', '#08306b'],
};

export const REDS: SequentialScheme = {
  id: 'reds',
  label: 'Reds',
  colors: ['#fff5f0', '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a', '#ef3b2c', '#cb181d', '#a50f15', '#67000d'],
};

export const GREENS: SequentialScheme = {
  id: 'greens',
  label: 'Greens',
  colors: ['#f7fcf5', '#e5f5e0', '#c7e9c0', '#a1d99b', '#74c476', '#41ab5d', '#238b45', '#006d2c', '#00441b'],
};

export const ORANGES: SequentialScheme = {
  id: 'oranges',
  label: 'Oranges',
  colors: ['#fff5eb', '#fee6ce', '#fdd0a2', '#fdae6b', '#fd8d3c', '#f16913', '#d94801', '#a63603', '#7f2704'],
};

export const PURPLES: SequentialScheme = {
  id: 'purples',
  label: 'Purples',
  colors: ['#fcfbfd', '#efedf5', '#dadaeb', '#bcbddc', '#9e9ac8', '#807dba', '#6a51a3', '#54278f', '#3f007d'],
};

export const VIRIDIS: SequentialScheme = {
  id: 'viridis',
  label: 'Viridis',
  colors: ['#440154', '#482878', '#3e4a89', '#31688e', '#26828e', '#1f9e89', '#35b779', '#6dcd59', '#b4de2c', '#fde725'],
};

export const PLASMA: SequentialScheme = {
  id: 'plasma',
  label: 'Plasma',
  colors: ['#0d0887', '#41049d', '#6a00a8', '#8f0da4', '#b12a90', '#cc4778', '#e16462', '#f1834b', '#fca636', '#fcce25'],
};

export const RD_BU: SequentialScheme = {
  id: 'rdBu',
  label: 'Red → Blue (Diverging)',
  isDiverging: true,
  colors: ['#67001f', '#b2182b', '#d6604d', '#f4a582', '#fddbc7', '#f7f7f7', '#d1e5f0', '#92c5de', '#4393c3', '#2166ac', '#053061'],
};

export const ALL_SEQUENTIAL_SCHEMES: SequentialScheme[] = [
  BLUES, REDS, GREENS, ORANGES, PURPLES, VIRIDIS, PLASMA, RD_BU,
];

const SEQUENTIAL_BY_ID: Record<string, SequentialScheme> = ALL_SEQUENTIAL_SCHEMES.reduce(
  (acc, scheme) => {
    acc[scheme.id] = scheme;
    return acc;
  },
  {} as Record<string, SequentialScheme>,
);

export const DEFAULT_SEQUENTIAL_SCHEME = BLUES;

export function getSequentialScheme(id?: string): SequentialScheme {
  if (!id) return DEFAULT_SEQUENTIAL_SCHEME;
  return SEQUENTIAL_BY_ID[id] ?? DEFAULT_SEQUENTIAL_SCHEME;
}
