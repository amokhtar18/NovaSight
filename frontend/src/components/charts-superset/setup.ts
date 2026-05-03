import MainPreset from './presets/MainPreset';

let registered = false;

/**
 * Idempotent one-shot bootstrap. Call once early in app startup (e.g. in
 * `main.tsx`) to populate every chart registry. Subsequent calls are no-ops.
 *
 * ```ts
 * import { setupChartsSuperset } from '@/components/charts-superset';
 * setupChartsSuperset();
 * ```
 */
export function setupChartsSuperset(): void {
  if (registered) return;
  new MainPreset().register();
  registered = true;
}

/** True once {@link setupChartsSuperset} has run. */
export function isChartsSupersetReady(): boolean {
  return registered;
}
