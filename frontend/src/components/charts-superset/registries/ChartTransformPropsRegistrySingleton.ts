import { RegistryWithLoader } from './Registry';
import type { TransformProps } from '../models/TransformProps';

let instance: RegistryWithLoader<TransformProps> | null = null;

export default function getChartTransformPropsRegistry(): RegistryWithLoader<TransformProps> {
  if (!instance) {
    instance = new RegistryWithLoader<TransformProps>('ChartTransformPropsRegistry');
  }
  return instance;
}
