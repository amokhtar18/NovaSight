/**
 * Lightweight in-memory registries used by the chart plugin system.
 *
 * Two flavours, mirroring apache/superset:
 *   - {@link Registry} — synchronous values keyed by string.
 *   - {@link RegistryWithLoader} — values OR async loaders. `get` returns the
 *     resolved value (awaiting the loader once and caching the result).
 *
 * Loaders enable code-splitting: a chart plugin's heavy renderer is only
 * imported when the registry is asked to resolve it.
 */
export class Registry<T> {
  protected items = new Map<string, T>();

  protected readonly registryName: string;

  constructor(name: string) {
    this.registryName = name;
  }

  registerValue(key: string, value: T): this {
    this.items.set(key, value);
    return this;
  }

  get(key: string): T | undefined {
    return this.items.get(key);
  }

  has(key: string): boolean {
    return this.items.has(key);
  }

  remove(key: string): this {
    this.items.delete(key);
    return this;
  }

  clear(): this {
    this.items.clear();
    return this;
  }

  keys(): string[] {
    return Array.from(this.items.keys());
  }

  values(): T[] {
    return Array.from(this.items.values());
  }

  entries(): Array<[string, T]> {
    return Array.from(this.items.entries());
  }

  get name(): string {
    return this.registryName;
  }
}

export type Loader<T> = () => T | Promise<T> | { default: T };

interface LoaderEntry<T> {
  loader: Loader<T>;
  resolved?: T;
  pending?: Promise<T>;
}

export class RegistryWithLoader<T> {
  private values = new Map<string, T>();
  private loaders = new Map<string, LoaderEntry<T>>();

  protected readonly registryName: string;

  constructor(name: string) {
    this.registryName = name;
  }

  registerValue(key: string, value: T): this {
    this.values.set(key, value);
    this.loaders.delete(key);
    return this;
  }

  registerLoader(key: string, loader: Loader<T>): this {
    this.loaders.set(key, { loader });
    this.values.delete(key);
    return this;
  }

  has(key: string): boolean {
    return this.values.has(key) || this.loaders.has(key);
  }

  /** Synchronous accessor — only returns a value if it's already loaded. */
  peek(key: string): T | undefined {
    if (this.values.has(key)) return this.values.get(key);
    return this.loaders.get(key)?.resolved;
  }

  /** Asynchronous accessor — awaits the loader and caches the result. */
  async get(key: string): Promise<T | undefined> {
    if (this.values.has(key)) return this.values.get(key);

    const entry = this.loaders.get(key);
    if (!entry) return undefined;
    if (entry.resolved !== undefined) return entry.resolved;
    if (entry.pending) return entry.pending;

    entry.pending = Promise.resolve(entry.loader()).then((result) => {
      const unwrapped =
        result && typeof result === 'object' && 'default' in (result as object)
          ? ((result as { default: T }).default)
          : (result as T);
      entry.resolved = unwrapped;
      entry.pending = undefined;
      return unwrapped;
    });

    return entry.pending;
  }

  remove(key: string): this {
    this.values.delete(key);
    this.loaders.delete(key);
    return this;
  }

  clear(): this {
    this.values.clear();
    this.loaders.clear();
    return this;
  }

  keys(): string[] {
    const out = new Set<string>();
    for (const k of this.values.keys()) out.add(k);
    for (const k of this.loaders.keys()) out.add(k);
    return Array.from(out);
  }

  get name(): string {
    return this.registryName;
  }
}
