import { Plugin } from './Plugin';
import type { ChartPlugin } from './ChartPlugin';

export interface PresetConfig {
  name: string;
  description?: string;
  /** Other presets to register before this preset's plugins. */
  presets?: Preset[];
  /** Plugins managed by this preset. */
  plugins?: ChartPlugin[];
}

/**
 * A {@link Preset} groups multiple plugins (and other presets) under a
 * descriptive name. Calling {@link Preset.register} cascades into every
 * dependency.
 */
export class Preset extends Plugin {
  readonly presetName: string;
  readonly description: string;
  readonly presets: Preset[];
  readonly plugins: ChartPlugin[];

  constructor(config: PresetConfig) {
    super();
    this.presetName = config.name;
    this.description = config.description ?? '';
    this.presets = config.presets ?? [];
    this.plugins = config.plugins ?? [];
  }

  register(): this {
    this.presets.forEach((preset) => preset.register());
    this.plugins.forEach((plugin) => plugin.register());
    return this;
  }
}

export default Preset;
