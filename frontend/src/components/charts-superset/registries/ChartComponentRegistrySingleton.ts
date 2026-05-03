import { ComponentType } from 'react';
import { RegistryWithLoader } from './Registry';

export type ChartComponent = ComponentType<any>;

let instance: RegistryWithLoader<ChartComponent> | null = null;

export default function getChartComponentRegistry(): RegistryWithLoader<ChartComponent> {
  if (!instance) {
    instance = new RegistryWithLoader<ChartComponent>('ChartComponentRegistry');
  }
  return instance;
}
