/**
 * Hook for previewing generated dbt code.
 *
 * Wraps the preview API call with a manual trigger
 * (not auto-fetched on mount).
 */

import { useMutation } from '@tanstack/react-query'
import { visualModelApi } from '../services/visualModelApi'
import type {
  GeneratedCodePreview,
  VisualModelCreatePayload,
} from '../types/visualModel'

/**
 * Preview by model id (for already-saved models).
 */
export function useCodePreviewMutation() {
  return useMutation<GeneratedCodePreview, Error, string>({
    mutationFn: (modelId: string) => visualModelApi.previewCode(modelId),
  })
}

/**
 * Preview from an in-progress builder payload (no save required).
 */
export function useCodePreviewFromPayloadMutation() {
  return useMutation<GeneratedCodePreview, Error, VisualModelCreatePayload>({
    mutationFn: (payload) => visualModelApi.previewCodeFromPayload(payload),
  })
}
