/**
 * VizType - canonical chart-plugin keys.
 *
 * Mirrors apache/superset's `superset-ui-core/src/chart/types/VizType.ts`.
 * Each value is the wire-level `viz_type` string persisted in form_data /
 * chart records. Do NOT rename values — they are the public identifier of
 * a chart plugin throughout the platform.
 *
 * Source of truth: https://github.com/apache/superset/blob/master/superset-frontend/packages/superset-ui-core/src/chart/types/VizType.ts
 */
export enum VizType {
  Area = 'echarts_area',
  Bar = 'echarts_timeseries_bar',
  BigNumber = 'big_number',
  BigNumberTotal = 'big_number_total',
  BigNumberPeriodOverPeriod = 'pop_kpi',
  BoxPlot = 'box_plot',
  Bubble = 'bubble_v2',
  Bullet = 'bullet',
  Calendar = 'cal_heatmap',
  Cartodiagram = 'cartodiagram',
  Chord = 'chord',
  Compare = 'compare',
  CountryMap = 'country_map',
  Funnel = 'funnel',
  Gantt = 'gantt_chart',
  Gauge = 'gauge_chart',
  Graph = 'graph_chart',
  Handlebars = 'handlebars',
  Heatmap = 'heatmap_v2',
  Histogram = 'histogram_v2',
  Horizon = 'horizon',
  LegacyBubble = 'bubble',
  Line = 'echarts_timeseries_line',
  MapBox = 'mapbox',
  PointClusterMap = 'point_cluster_map',
  MixedTimeseries = 'mixed_timeseries',
  PairedTTest = 'paired_ttest',
  ParallelCoordinates = 'para',
  Partition = 'partition',
  Pie = 'pie',
  PivotTable = 'pivot_table_v2',
  Radar = 'radar',
  Rose = 'rose',
  Sankey = 'sankey_v2',
  Scatter = 'echarts_timeseries_scatter',
  SmoothLine = 'echarts_timeseries_smooth',
  Step = 'echarts_timeseries_step',
  Sunburst = 'sunburst_v2',
  Table = 'table',
  TableAgGrid = 'ag-grid-table',
  TimePivot = 'time_pivot',
  TimeTable = 'time_table',
  Timeseries = 'echarts_timeseries',
  Tree = 'tree_chart',
  Treemap = 'treemap_v2',
  Waterfall = 'waterfall',
  WordCloud = 'word_cloud',
  WorldMap = 'world_map',

  // deck.gl family
  DeckArc = 'deck_arc',
  DeckGeoJson = 'deck_geojson',
  DeckGrid = 'deck_grid',
  DeckHex = 'deck_hex',
  DeckHeatmap = 'deck_heatmap',
  DeckMulti = 'deck_multi',
  DeckPath = 'deck_path',
  DeckPolygon = 'deck_polygon',
  DeckScatter = 'deck_scatter',
  DeckScreengrid = 'deck_screengrid',
  DeckContour = 'deck_contour',
}

export type VizTypeKey = `${VizType}`;
