/**
 * ChartMetadata describes a chart plugin to the rest of the application
 * (the viz-picker gallery, the dashboard inspector, the explore panel).
 *
 * Faithful port of apache/superset's
 * `superset-ui-core/src/chart/models/ChartMetadata.ts`, scoped to NovaSight.
 */
import { Behavior, ChartLabel, ExampleImage, ParseMethod } from '../types/Base';

type LookupTable = Record<string, boolean>;

export interface ChartMetadataConfig {
  /** Human-readable display name (e.g. "Bar Chart"). */
  name: string;
  /** AnnotationType keys this chart accepts (EVENT, INTERVAL, FORMULA, ...). */
  canBeAnnotationTypes?: string[];
  /** Acknowledgements for icons, datasets, libraries, etc. */
  credits?: string[];
  /** Long-form description shown in the picker. */
  description?: string;
  /** Number of datasources required by the chart (1 by default). */
  datasourceCount?: number;
  /** Whether the chart can render an empty/no-results state. */
  enableNoResults?: boolean;
  /** AnnotationType keys this chart can render (EVENT, INTERVAL, ...). */
  supportedAnnotationTypes?: string[];
  /** Path to the light-theme thumbnail image. */
  thumbnail?: string;
  /** Optional dark-theme thumbnail image. */
  thumbnailDark?: string;
  /** True for charts still backed by the legacy `/explore_json` API. */
  useLegacyApi?: boolean;
  /** Set of behaviors the chart opts into. */
  behaviors?: Behavior[];
  /** Optional larger preview gallery used in the chart-detail panel. */
  exampleGallery?: ExampleImage[];
  /** Free-form tags used by the gallery for filtering. */
  tags?: string[];
  /** High-level category the chart belongs to. */
  category?: string | null;
  /** When true, hides the chart from all viz picker interactions. */
  deprecated?: boolean;
  /** Highlight label (e.g. FEATURED, DEPRECATED, VERIFIED). */
  label?: ChartLabel | null;
  /** Tooltip shown next to the highlight label. */
  labelExplanation?: string | null;
  /** Number of QueryObject entries the chart issues. */
  queryObjectCount?: number;
  /** True if the chart issues a variable number of queries at runtime. */
  dynamicQueryObjectCount?: boolean;
  /** JSON parsing strategy applied to query responses. */
  parseMethod?: ParseMethod;
  /** When true, suppresses the default right-click context menu. */
  suppressContextMenu?: boolean;
}

export class ChartMetadata {
  name: string;
  canBeAnnotationTypes: string[];
  canBeAnnotationTypesLookup: LookupTable;
  credits: string[];
  description: string;
  supportedAnnotationTypes: string[];
  thumbnail: string;
  thumbnailDark?: string;
  useLegacyApi: boolean;
  behaviors: Behavior[];
  datasourceCount: number;
  enableNoResults: boolean;
  exampleGallery: ExampleImage[];
  tags: string[];
  category: string | null;
  deprecated: boolean;
  label: ChartLabel | null;
  labelExplanation: string | null;
  queryObjectCount: number;
  dynamicQueryObjectCount: boolean;
  parseMethod: ParseMethod;
  suppressContextMenu: boolean;

  constructor(config: ChartMetadataConfig) {
    const {
      name,
      canBeAnnotationTypes = [],
      credits = [],
      description = '',
      supportedAnnotationTypes = [],
      thumbnail = '',
      thumbnailDark,
      useLegacyApi = false,
      behaviors = [],
      datasourceCount = 1,
      enableNoResults = true,
      exampleGallery = [],
      tags = [],
      category = null,
      deprecated = false,
      label = null,
      labelExplanation = null,
      queryObjectCount = 1,
      dynamicQueryObjectCount = false,
      parseMethod = 'json-bigint',
      suppressContextMenu = false,
    } = config;

    this.name = name;
    this.credits = credits;
    this.description = description;
    this.canBeAnnotationTypes = canBeAnnotationTypes;
    this.canBeAnnotationTypesLookup = canBeAnnotationTypes.reduce<LookupTable>(
      (lookup, type) => {
        lookup[type] = true;
        return lookup;
      },
      {},
    );
    this.supportedAnnotationTypes = supportedAnnotationTypes;
    this.thumbnail = thumbnail;
    this.thumbnailDark = thumbnailDark;
    this.useLegacyApi = useLegacyApi;
    this.behaviors = behaviors;
    this.datasourceCount = datasourceCount;
    this.enableNoResults = enableNoResults;
    this.exampleGallery = exampleGallery;
    this.tags = tags;
    this.category = category;
    this.deprecated = deprecated;
    this.label = label;
    this.labelExplanation = labelExplanation;
    this.queryObjectCount = queryObjectCount;
    this.dynamicQueryObjectCount = dynamicQueryObjectCount;
    this.parseMethod = parseMethod;
    this.suppressContextMenu = suppressContextMenu;
  }

  canBeAnnotationType(type: string): boolean {
    return this.canBeAnnotationTypesLookup[type] ?? false;
  }

  clone(): ChartMetadata {
    return new ChartMetadata({
      name: this.name,
      canBeAnnotationTypes: [...this.canBeAnnotationTypes],
      credits: [...this.credits],
      description: this.description,
      supportedAnnotationTypes: [...this.supportedAnnotationTypes],
      thumbnail: this.thumbnail,
      thumbnailDark: this.thumbnailDark,
      useLegacyApi: this.useLegacyApi,
      behaviors: [...this.behaviors],
      datasourceCount: this.datasourceCount,
      enableNoResults: this.enableNoResults,
      exampleGallery: [...this.exampleGallery],
      tags: [...this.tags],
      category: this.category,
      deprecated: this.deprecated,
      label: this.label,
      labelExplanation: this.labelExplanation,
      queryObjectCount: this.queryObjectCount,
      dynamicQueryObjectCount: this.dynamicQueryObjectCount,
      parseMethod: this.parseMethod,
      suppressContextMenu: this.suppressContextMenu,
    });
  }
}

export default ChartMetadata;
