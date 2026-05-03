import { Registry } from './Registry';
import type { ControlPanelConfig } from '../models/ControlPanel';

let instance: Registry<ControlPanelConfig> | null = null;

export default function getChartControlPanelRegistry(): Registry<ControlPanelConfig> {
  if (!instance) {
    instance = new Registry<ControlPanelConfig>('ChartControlPanelRegistry');
  }
  return instance;
}
