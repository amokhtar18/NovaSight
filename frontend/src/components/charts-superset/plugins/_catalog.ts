/**
 * Metadata-only catalog for chart types ported from Apache Superset that
 * don't yet have a NovaSight-native renderer. Each entry is a real
 * {@link ChartPlugin} backed by {@link PlaceholderChart} so the chart shows
 * up in the picker with the correct name, category, tags and description.
 *
 * As renderers land, move the entry out of this file and into its own
 * `plugins/<Name>/` folder.
 */
import { ChartPlugin } from '../models/ChartPlugin';
import type { ChartMetadataConfig } from '../models/ChartMetadata';
import { Behavior, ChartCategory } from '../types/Base';
import { VizType } from '../types/VizType';
import { buildStubPlugin } from './_helpers';

interface CatalogEntry {
  vizType: string;
  metadata: ChartMetadataConfig;
}

const CATALOG: CatalogEntry[] = [
  // ─────────────────────────────────────────── Distribution ───
  {
    vizType: VizType.Histogram,
    metadata: {
      name: 'Histogram',
      description: 'Distribution of a numeric variable as bins.',
      category: ChartCategory.Distribution,
      tags: ['Distribution', 'Single Metric', 'Statistical'],
      behaviors: [Behavior.InteractiveChart],
    },
  },
  {
    vizType: VizType.BoxPlot,
    metadata: {
      name: 'Box Plot',
      description: 'Median, quartiles and outliers across categories.',
      category: ChartCategory.Distribution,
      tags: ['Statistical', 'Distribution', 'Comparison'],
      behaviors: [Behavior.InteractiveChart],
    },
  },
  {
    vizType: VizType.WordCloud,
    metadata: {
      name: 'Word Cloud',
      description: 'Visualise text frequency at a glance.',
      category: ChartCategory.Distribution,
      tags: ['Aesthetic', 'Categorical', 'Text', 'Engineering'],
    },
  },
  {
    vizType: VizType.PairedTTest,
    metadata: {
      name: 'Paired t-test Table',
      description: 'Compare metric values across two related samples.',
      category: ChartCategory.Distribution,
      tags: ['Statistical', 'Tabular'],
    },
  },

  // ─────────────────────────────────────────── Correlation ───
  {
    vizType: VizType.Heatmap,
    metadata: {
      name: 'Heatmap',
      description: 'Density across two dimensions encoded by color.',
      category: ChartCategory.Correlation,
      tags: ['Comparison', 'Correlation', 'Density'],
      behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail],
    },
  },
  {
    vizType: VizType.Bubble,
    metadata: {
      name: 'Bubble Chart',
      description: 'Three numeric dimensions encoded as x/y/size.',
      category: ChartCategory.Correlation,
      tags: ['Multi-Variates', 'Scatter', 'Numeric'],
      behaviors: [Behavior.InteractiveChart],
    },
  },
  {
    vizType: VizType.LegacyBubble,
    metadata: {
      name: 'Bubble Chart (legacy)',
      description: 'Legacy NVD3 bubble chart.',
      category: ChartCategory.Correlation,
      tags: ['Multi-Variates', 'Deprecated'],
    },
  },
  {
    vizType: VizType.ParallelCoordinates,
    metadata: {
      name: 'Parallel Coordinates',
      description: 'Compare many numeric dimensions across rows.',
      category: ChartCategory.Correlation,
      tags: ['Multi-Variates', 'Comparison'],
    },
  },

  // ─────────────────────────────────────────── Evolution ───
  {
    vizType: VizType.Waterfall,
    metadata: {
      name: 'Waterfall Chart',
      description:
        'Show the cumulative effect of sequentially introduced positive or negative values.',
      category: ChartCategory.Evolution,
      tags: ['Comparison', 'Sequential', 'Categorical'],
    },
  },
  {
    vizType: VizType.MixedTimeseries,
    metadata: {
      name: 'Mixed Time-series',
      description:
        'Combine bars and lines on a shared time axis with dual Y axes.',
      category: ChartCategory.Trend,
      tags: ['Featured', 'Time-series', 'Multi-Series', 'Dual-Axis'],
      behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail, Behavior.DrillBy],
      canBeAnnotationTypes: ['EVENT', 'INTERVAL', 'TIME_SERIES', 'FORMULA'],
    },
  },
  {
    vizType: VizType.SmoothLine,
    metadata: {
      name: 'Smooth Line Chart',
      description: 'Smoothed-curve time-series.',
      category: ChartCategory.Evolution,
      tags: ['Time-series', 'Trend', 'Aesthetic'],
      behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail],
      canBeAnnotationTypes: ['EVENT', 'INTERVAL', 'TIME_SERIES', 'FORMULA'],
    },
  },
  {
    vizType: VizType.Step,
    metadata: {
      name: 'Stepped Line',
      description: 'Time-series rendered as discrete steps.',
      category: ChartCategory.Evolution,
      tags: ['Time-series', 'Trend', 'Discrete'],
      behaviors: [Behavior.InteractiveChart],
      canBeAnnotationTypes: ['EVENT', 'INTERVAL', 'TIME_SERIES', 'FORMULA'],
    },
  },
  {
    vizType: VizType.Compare,
    metadata: {
      name: 'Time-series Comparison',
      description: 'Compare two time-series side by side.',
      category: ChartCategory.Trend,
      tags: ['Time-series', 'Comparison'],
    },
  },
  {
    vizType: VizType.TimePivot,
    metadata: {
      name: 'Time-series Pivot Table',
      description: 'Pivot a time-series across two dimensions.',
      category: ChartCategory.Trend,
      tags: ['Time-series', 'Tabular', 'Pivot'],
    },
  },
  {
    vizType: VizType.TimeTable,
    metadata: {
      name: 'Time-series Table',
      description: 'Tabular time-series with sparklines.',
      category: ChartCategory.Trend,
      tags: ['Time-series', 'Tabular', 'Sparkline'],
    },
  },
  {
    vizType: VizType.Calendar,
    metadata: {
      name: 'Calendar Heatmap',
      description: 'Daily values laid out as a calendar.',
      category: ChartCategory.Trend,
      tags: ['Time-series', 'Calendar', 'Density'],
    },
  },
  {
    vizType: VizType.Horizon,
    metadata: {
      name: 'Horizon Chart',
      description: 'Compact, layered time-series for many series.',
      category: ChartCategory.Evolution,
      tags: ['Time-series', 'Aesthetic', 'Density'],
    },
  },
  {
    vizType: VizType.Gantt,
    metadata: {
      name: 'Gantt Chart',
      description: 'Timeline of tasks/events across categories.',
      category: ChartCategory.Evolution,
      tags: ['Time-series', 'Sequential', 'Project'],
    },
  },

  // ─────────────────────────────────────────── KPI ───
  {
    vizType: VizType.BigNumberPeriodOverPeriod,
    metadata: {
      name: 'Big Number with Period-over-Period',
      description: 'Single KPI with comparison to the previous period.',
      category: ChartCategory.KPI,
      tags: ['Featured', 'Single Value', 'KPI', 'Trend'],
      behaviors: [Behavior.DrillToDetail],
    },
  },
  {
    vizType: VizType.Gauge,
    metadata: {
      name: 'Gauge Chart',
      description: 'Single value displayed against a range.',
      category: ChartCategory.KPI,
      tags: ['Single Value', 'Aesthetic'],
    },
  },
  {
    vizType: VizType.Bullet,
    metadata: {
      name: 'Bullet Chart',
      description:
        'Single metric with target and qualitative ranges (good/poor).',
      category: ChartCategory.KPI,
      tags: ['Single Value', 'Comparison'],
    },
  },

  // ─────────────────────────────────────────── Part of a whole ───
  {
    vizType: VizType.Sunburst,
    metadata: {
      name: 'Sunburst Chart',
      description: 'Hierarchical contribution as concentric rings.',
      category: ChartCategory.Part,
      tags: ['Hierarchy', 'Aesthetic', 'Categorical'],
      behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail, Behavior.DrillBy],
    },
  },
  {
    vizType: VizType.Treemap,
    metadata: {
      name: 'Treemap',
      description: 'Hierarchical contribution as nested rectangles.',
      category: ChartCategory.Part,
      tags: ['Hierarchy', 'Categorical', 'Density'],
      behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail, Behavior.DrillBy],
    },
  },
  {
    vizType: VizType.Funnel,
    metadata: {
      name: 'Funnel Chart',
      description: 'Show progression through stages.',
      category: ChartCategory.Part,
      tags: ['Sequential', 'Categorical'],
      behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail],
    },
  },
  {
    vizType: VizType.Partition,
    metadata: {
      name: 'Partition Chart',
      description: 'Hierarchical icicle-style breakdown.',
      category: ChartCategory.Part,
      tags: ['Hierarchy'],
    },
  },
  {
    vizType: VizType.Rose,
    metadata: {
      name: 'Nightingale Rose Chart',
      description: 'Polar bar chart often used for cyclic data.',
      category: ChartCategory.Part,
      tags: ['Aesthetic', 'Polar', 'Categorical'],
    },
  },

  // ─────────────────────────────────────────── Flow ───
  {
    vizType: VizType.Sankey,
    metadata: {
      name: 'Sankey Diagram',
      description: 'Visualise flow between nodes via weighted links.',
      category: ChartCategory.Flow,
      tags: ['Relational', 'Multi-Variates'],
      behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail, Behavior.DrillBy],
    },
  },
  {
    vizType: VizType.Chord,
    metadata: {
      name: 'Chord Diagram',
      description: 'Show inter-relationships between entities.',
      category: ChartCategory.Flow,
      tags: ['Relational', 'Aesthetic'],
    },
  },
  {
    vizType: VizType.Tree,
    metadata: {
      name: 'Tree Chart',
      description: 'Hierarchical tree of nodes.',
      category: ChartCategory.Flow,
      tags: ['Hierarchy', 'Relational'],
    },
  },
  {
    vizType: VizType.Graph,
    metadata: {
      name: 'Graph Chart',
      description: 'Force-directed graph of nodes and edges.',
      category: ChartCategory.Flow,
      tags: ['Relational', 'Network'],
      behaviors: [Behavior.InteractiveChart],
    },
  },

  // ─────────────────────────────────────────── Ranking ───
  {
    vizType: VizType.Radar,
    metadata: {
      name: 'Radar Chart',
      description: 'Compare entities across multiple metrics.',
      category: ChartCategory.Ranking,
      tags: ['Multi-Variates', 'Comparison', 'Aesthetic'],
    },
  },

  // ─────────────────────────────────────────── Table ───
  {
    vizType: VizType.PivotTable,
    metadata: {
      name: 'Pivot Table',
      description: 'Pivot rows and columns with subtotals and totals.',
      category: ChartCategory.Table,
      tags: ['Featured', 'Tabular', 'Pivot', 'Report'],
      behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail, Behavior.DrillBy],
    },
  },
  {
    vizType: VizType.TableAgGrid,
    metadata: {
      name: 'Advanced Table',
      description:
        'Power-user table powered by ag-grid: column groups, filters, exports.',
      category: ChartCategory.Table,
      tags: ['Tabular', 'Advanced', 'Report', 'Pagination'],
      behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail, Behavior.DrillBy],
    },
  },
  {
    vizType: VizType.Handlebars,
    metadata: {
      name: 'Handlebars',
      description: 'Render results with a Handlebars template.',
      category: ChartCategory.Other,
      tags: ['Engineering', 'Advanced', 'Custom'],
    },
  },

  // ─────────────────────────────────────────── Map ───
  {
    vizType: VizType.MapBox,
    metadata: {
      name: 'MapBox',
      description: 'Interactive geographic visualisation on Mapbox tiles.',
      category: ChartCategory.Map,
      tags: ['Geo', 'Interactive', 'Streaming'],
    },
  },
  {
    vizType: VizType.WorldMap,
    metadata: {
      name: 'World Map',
      description: 'Choropleth at the country level.',
      category: ChartCategory.Map,
      tags: ['Geo', 'Choropleth'],
    },
  },
  {
    vizType: VizType.CountryMap,
    metadata: {
      name: 'Country Map',
      description: 'Choropleth at the regional/state level.',
      category: ChartCategory.Map,
      tags: ['Geo', 'Choropleth', 'Regional'],
    },
  },
  {
    vizType: VizType.PointClusterMap,
    metadata: {
      name: 'Point Cluster Map',
      description: 'Cluster many geographic points dynamically.',
      category: ChartCategory.Map,
      tags: ['Geo', 'Density', 'Interactive'],
    },
  },
  {
    vizType: VizType.Cartodiagram,
    metadata: {
      name: 'Cartodiagram',
      description: 'Embed a chart per region on a map.',
      category: ChartCategory.Map,
      tags: ['Geo', 'Multi-Variates'],
    },
  },
  {
    vizType: VizType.DeckArc,
    metadata: {
      name: 'deck.gl Arc',
      description: 'Arcs between origin and destination points.',
      category: ChartCategory.Map,
      tags: ['Geo', 'deck.gl', 'Streaming'],
    },
  },
  {
    vizType: VizType.DeckGeoJson,
    metadata: {
      name: 'deck.gl GeoJSON',
      description: 'Render arbitrary GeoJSON features.',
      category: ChartCategory.Map,
      tags: ['Geo', 'deck.gl'],
    },
  },
  {
    vizType: VizType.DeckGrid,
    metadata: {
      name: 'deck.gl Grid',
      description: '3D grid aggregation of points.',
      category: ChartCategory.Map,
      tags: ['Geo', 'deck.gl', '3D', 'Density'],
    },
  },
  {
    vizType: VizType.DeckHex,
    metadata: {
      name: 'deck.gl Hex',
      description: 'Hexagonal binning of points in 3D.',
      category: ChartCategory.Map,
      tags: ['Geo', 'deck.gl', '3D', 'Density'],
    },
  },
  {
    vizType: VizType.DeckHeatmap,
    metadata: {
      name: 'deck.gl Heatmap',
      description: 'Geographic heatmap.',
      category: ChartCategory.Map,
      tags: ['Geo', 'deck.gl', 'Density'],
    },
  },
  {
    vizType: VizType.DeckMulti,
    metadata: {
      name: 'deck.gl Multi-Layer',
      description: 'Compose multiple deck.gl layers.',
      category: ChartCategory.Map,
      tags: ['Geo', 'deck.gl', 'Multi-Variates'],
    },
  },
  {
    vizType: VizType.DeckPath,
    metadata: {
      name: 'deck.gl Path',
      description: 'Render path geometries on a map.',
      category: ChartCategory.Map,
      tags: ['Geo', 'deck.gl'],
    },
  },
  {
    vizType: VizType.DeckPolygon,
    metadata: {
      name: 'deck.gl Polygon',
      description: '3D polygon extrusions.',
      category: ChartCategory.Map,
      tags: ['Geo', 'deck.gl', '3D'],
    },
  },
  {
    vizType: VizType.DeckScatter,
    metadata: {
      name: 'deck.gl Scatter',
      description: 'Scatter points on a map.',
      category: ChartCategory.Map,
      tags: ['Geo', 'deck.gl'],
    },
  },
  {
    vizType: VizType.DeckScreengrid,
    metadata: {
      name: 'deck.gl Screen-Grid',
      description: 'Screen-space grid aggregation.',
      category: ChartCategory.Map,
      tags: ['Geo', 'deck.gl', 'Density'],
    },
  },
  {
    vizType: VizType.DeckContour,
    metadata: {
      name: 'deck.gl Contour',
      description: 'Iso-contour lines from point density.',
      category: ChartCategory.Map,
      tags: ['Geo', 'deck.gl', 'Density'],
    },
  },
];

/**
 * Build the complete list of stub plugins. Each is `.configure({key})`-ed
 * but not yet registered — callers (like `MainPreset`) handle registration.
 *
 * Pass `excludeVizTypes` to drop entries that already have a real
 * implementation in `MainPreset`, so we don't accidentally clobber them.
 */
export function buildCatalogPlugins(
  excludeVizTypes: ReadonlySet<string> = new Set(),
): ChartPlugin[] {
  return CATALOG.filter((entry) => !excludeVizTypes.has(entry.vizType)).map(
    (entry) => buildStubPlugin(entry.metadata).configure({ key: entry.vizType }),
  );
}

export default buildCatalogPlugins;
