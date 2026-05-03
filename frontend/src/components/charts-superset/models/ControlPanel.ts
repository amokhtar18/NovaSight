/**
 * Minimal control-panel descriptor used by the chart-config UI.
 *
 * Faithful to upstream's section/row/control hierarchy but strongly
 * simplified — full Superset control types can be added incrementally as
 * we wire each plugin's editor.
 */

export type ControlType =
  | 'TextControl'
  | 'TextAreaControl'
  | 'SelectControl'
  | 'CheckboxControl'
  | 'SliderControl'
  | 'NumberControl'
  | 'ColorPickerControl'
  | 'ColorSchemeControl'
  | 'ColumnSelectControl'
  | 'MetricsControl'
  | 'AdhocFilterControl'
  | 'TimeRangeControl'
  | 'BoundsControl'
  | 'AnnotationLayerControl'
  | 'HiddenControl';

export interface ControlConfig<T = unknown> {
  type: ControlType;
  label?: string;
  description?: string;
  default?: T;
  /** [value, label] tuples for select-style controls. */
  choices?: Array<[string | number | boolean, string]>;
  validators?: Array<(value: unknown) => string | undefined>;
  /** Re-render the chart automatically when this control changes. */
  renderTrigger?: boolean;
  /** When false, an empty value is invalid. */
  clearable?: boolean;
  /** Free-form props forwarded to the control component. */
  [extra: string]: unknown;
}

export interface ControlSetItem {
  name: string;
  config: ControlConfig;
}

/** A row in a section is a list of controls displayed inline. */
export type ControlSetRow = Array<string | ControlSetItem | null>;

export interface ControlPanelSectionConfig {
  label: string;
  description?: string;
  expanded?: boolean;
  /** Hide the entire section based on form-data. */
  visibility?: (formData: Record<string, unknown>) => boolean;
  controlSetRows: ControlSetRow[];
}

export interface ControlPanelConfig {
  /** Common controls shown at the top of the panel. */
  controlPanelSections: ControlPanelSectionConfig[];
  /** Per-control overrides keyed by control name. */
  controlOverrides?: Record<string, Partial<ControlConfig>>;
  /** When true, the chart can fetch results without a datasource. */
  sectionOverrides?: Record<string, Partial<ControlPanelSectionConfig>>;
}
