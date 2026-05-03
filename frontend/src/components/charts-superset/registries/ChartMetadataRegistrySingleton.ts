import { Registry } from './Registry';
import { ChartMetadata } from '../models/ChartMetadata';

let instance: Registry<ChartMetadata> | null = null;

export default function getChartMetadataRegistry(): Registry<ChartMetadata> {
  if (!instance) {
    instance = new Registry<ChartMetadata>('ChartMetadataRegistry');
  }
  return instance;
}
