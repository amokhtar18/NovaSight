/**
 * MainPreset — the bundle of every NovaSight chart plugin.
 *
 * Faithful to apache/superset's `MainPreset.ts`: a single `Preset` whose
 * `register()` call populates all five registries (metadata, component,
 * controlPanel, transformProps, buildQuery) for every plugin.
 *
 * Calling `new MainPreset().register()` is the canonical way to enable
 * the entire chart catalog. Use {@link setupChartsSuperset} for an
 * idempotent one-shot wrapper.
 */
import { Preset } from '../models/Preset';
import { VizType } from '../types/VizType';

import BigNumberChartPlugin from '../plugins/BigNumber';
import BigNumberTotalChartPlugin from '../plugins/BigNumberTotal';
import TableChartPlugin from '../plugins/Table';
import PieChartPlugin from '../plugins/Pie';
import BarChartPlugin from '../plugins/Bar';
import LineChartPlugin from '../plugins/Line';
import AreaChartPlugin from '../plugins/Area';
import ScatterChartPlugin from '../plugins/Scatter';
import TimeseriesChartPlugin from '../plugins/Timeseries';
import HeatmapChartPlugin from '../plugins/Heatmap';
import SunburstChartPlugin from '../plugins/Sunburst';
import TreemapChartPlugin from '../plugins/Treemap';
import SankeyChartPlugin from '../plugins/Sankey';
import FunnelChartPlugin from '../plugins/Funnel';
import GaugeChartPlugin from '../plugins/Gauge';
import RadarChartPlugin from '../plugins/Radar';
import BoxPlotChartPlugin from '../plugins/BoxPlot';

import { buildCatalogPlugins } from '../plugins/_catalog';

/**
 * Viz types that already have a full implementation registered above and
 * therefore must NOT be re-registered as stubs from the catalog.
 */
const REAL_VIZ_TYPES = new Set<string>([
  VizType.BigNumber,
  VizType.BigNumberTotal,
  VizType.Table,
  VizType.Pie,
  VizType.Bar,
  VizType.Line,
  VizType.Area,
  VizType.Scatter,
  VizType.Timeseries,
  VizType.Heatmap,
  VizType.Sunburst,
  VizType.Treemap,
  VizType.Sankey,
  VizType.Funnel,
  VizType.Gauge,
  VizType.Radar,
  VizType.BoxPlot,
]);

export class MainPreset extends Preset {
  constructor() {
    super({
      name: 'NovaSight charts',
      description:
        'Full chart-plugin catalog: bar, line, area, pie, scatter, table, big number, plus the long tail of categorical, geo, flow, hierarchy and statistical visualisations ported from Apache Superset.',
      plugins: [
        // ── Recharts-backed implementations ──────────────────────
        new BigNumberChartPlugin().configure({ key: VizType.BigNumber }),
        new BigNumberTotalChartPlugin().configure({ key: VizType.BigNumberTotal }),
        new TableChartPlugin().configure({ key: VizType.Table }),
        new PieChartPlugin().configure({ key: VizType.Pie }),
        new BarChartPlugin().configure({ key: VizType.Bar }),
        new LineChartPlugin().configure({ key: VizType.Line }),
        new AreaChartPlugin().configure({ key: VizType.Area }),
        new ScatterChartPlugin().configure({ key: VizType.Scatter }),
        new TimeseriesChartPlugin().configure({ key: VizType.Timeseries }),

        // ── ECharts-backed implementations ───────────────────────
        new HeatmapChartPlugin().configure({ key: VizType.Heatmap }),
        new SunburstChartPlugin().configure({ key: VizType.Sunburst }),
        new TreemapChartPlugin().configure({ key: VizType.Treemap }),
        new SankeyChartPlugin().configure({ key: VizType.Sankey }),
        new FunnelChartPlugin().configure({ key: VizType.Funnel }),
        new GaugeChartPlugin().configure({ key: VizType.Gauge }),
        new RadarChartPlugin().configure({ key: VizType.Radar }),
        new BoxPlotChartPlugin().configure({ key: VizType.BoxPlot }),

        // ── Stub plugins (real metadata, placeholder renderer) ───
        ...buildCatalogPlugins(REAL_VIZ_TYPES),
      ],
    });
  }
}

export default MainPreset;
