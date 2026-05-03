/**
 * Lightweight base class for "plugins" — anything pluggable into the registry
 * system. Subclassed by {@link ChartPlugin} and {@link Preset}.
 */
export class Plugin {
  config: { key?: string } = {};

  configure<T extends { key: string }>(config: T): this {
    this.config = { ...this.config, ...config };
    return this;
  }

  resetConfig(): this {
    this.config = {};
    return this;
  }

  register(): this {
    return this;
  }
}

export default Plugin;
