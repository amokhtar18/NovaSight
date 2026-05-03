/**
 * Datasets feature public surface.
 *
 * Superset-inspired Dataset abstraction used by charts and dashboards.
 */

export { DatasetPicker } from './components/DatasetPicker';
export {
  useDatasets,
  useDataset,
  useDatasetPreview,
  useCreateDataset,
  useUpdateDataset,
  useDeleteDataset,
  useReplaceDatasetColumns,
  useReplaceDatasetMetrics,
  useSyncDatasetsFromDbt,
} from './hooks/useDatasets';
export { datasetsApi } from './services/datasetsApi';
export type {
  Dataset,
  DatasetColumn,
  DatasetMetric,
  DatasetKind,
  DatasetSource,
  DbtMaterialization,
  DatasetCreateRequest,
  DatasetUpdateRequest,
  DatasetListResponse,
  DatasetPreview,
  DbtSyncResult,
} from './types';
export { default as DatasetsListPage } from './pages/DatasetsListPage';
export { default as DatasetDetailPage } from './pages/DatasetDetailPage';
export { default as DatasetCreatePage } from './pages/DatasetCreatePage';
