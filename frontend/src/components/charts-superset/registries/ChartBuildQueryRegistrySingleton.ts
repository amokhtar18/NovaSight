import { RegistryWithLoader } from './Registry';
import type { BuildQuery } from '../models/BuildQuery';

let instance: RegistryWithLoader<BuildQuery> | null = null;

export default function getChartBuildQueryRegistry(): RegistryWithLoader<BuildQuery> {
  if (!instance) {
    instance = new RegistryWithLoader<BuildQuery>('ChartBuildQueryRegistry');
  }
  return instance;
}
