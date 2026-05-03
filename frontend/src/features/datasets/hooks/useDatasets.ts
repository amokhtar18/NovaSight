/**
 * TanStack Query hooks for the Datasets feature.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from '@tanstack/react-query';
import {
  datasetsApi,
  type ListDatasetsParams,
} from '../services/datasetsApi';
import type {
  Dataset,
  DatasetCreateRequest,
  DatasetListResponse,
  DatasetPreview,
  DatasetUpdateRequest,
  DatasetColumn,
  DatasetMetric,
  DbtSyncResult,
} from '../types';

const KEYS = {
  all: ['datasets'] as const,
  list: (params: ListDatasetsParams) => ['datasets', 'list', params] as const,
  detail: (id: string) => ['datasets', 'detail', id] as const,
  preview: (id: string, limit: number) =>
    ['datasets', 'preview', id, limit] as const,
};

export function useDatasets(
  params: ListDatasetsParams = {},
  options?: Omit<
    UseQueryOptions<DatasetListResponse>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery<DatasetListResponse>({
    queryKey: KEYS.list(params),
    queryFn: () => datasetsApi.list(params),
    ...options,
  });
}

export function useDataset(
  id: string | undefined,
  options?: Omit<UseQueryOptions<Dataset>, 'queryKey' | 'queryFn' | 'enabled'>,
) {
  return useQuery<Dataset>({
    queryKey: KEYS.detail(id ?? ''),
    queryFn: () => datasetsApi.get(id as string),
    enabled: Boolean(id),
    ...options,
  });
}

export function useDatasetPreview(
  id: string | undefined,
  limit = 100,
  enabled = true,
) {
  return useQuery<DatasetPreview>({
    queryKey: KEYS.preview(id ?? '', limit),
    queryFn: () => datasetsApi.preview(id as string, limit),
    enabled: Boolean(id) && enabled,
  });
}

export function useCreateDataset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: DatasetCreateRequest) => datasetsApi.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useUpdateDataset(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: DatasetUpdateRequest) =>
      datasetsApi.update(id, payload),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: KEYS.all });
      qc.setQueryData(KEYS.detail(id), data);
    },
  });
}

export function useDeleteDataset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, hard = false }: { id: string; hard?: boolean }) =>
      datasetsApi.remove(id, hard),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useReplaceDatasetColumns(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (columns: Partial<DatasetColumn>[]) =>
      datasetsApi.replaceColumns(id, columns),
    onSuccess: (data) => qc.setQueryData(KEYS.detail(id), data),
  });
}

export function useReplaceDatasetMetrics(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (metrics: Partial<DatasetMetric>[]) =>
      datasetsApi.replaceMetrics(id, metrics),
    onSuccess: (data) => qc.setQueryData(KEYS.detail(id), data),
  });
}

export function useSyncDatasetsFromDbt() {
  const qc = useQueryClient();
  return useMutation<DbtSyncResult, Error, boolean | void>({
    mutationFn: (deactivateMissing) =>
      datasetsApi.syncFromDbt(deactivateMissing !== false),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}
