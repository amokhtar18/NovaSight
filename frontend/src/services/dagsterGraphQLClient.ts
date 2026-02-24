/**
 * Dagster GraphQL Client Service
 * Provides methods for interacting with Dagster's GraphQL API
 */

import type {
  DagsterGraphQLResponse,
  DagsterRun,
  DagsterAssetNode,
  DagsterSchedule,
  DagsterSensor,
  DagsterRepository,
  DagsterRunsFilter,
  DagsterRunStatus,
  DagsterAssetKey,
  DagsterAssetGraph,
  DagsterAssetGraphNode,
  DagsterAssetGraphEdge,
  RepositoriesQueryResult,
  RunsQueryResult,
  AssetsQueryResult,
  SchedulesQueryResult,
  SensorsQueryResult,
  LaunchRunMutationResult,
  TerminateRunMutationResult,
  StartScheduleMutationResult,
  StopScheduleMutationResult,
  StartSensorMutationResult,
  StopSensorMutationResult,
} from '@/types/dagster';

// ============= GraphQL Fragments =============

const RUN_FRAGMENT = `
  fragment RunFields on Run {
    id
    runId
    status
    mode
    pipelineName
    pipelineSnapshotId
    startTime
    endTime
    updateTime
    canTerminate
    hasReExecutePermission
    hasTerminatePermission
    hasDeletePermission
    tags {
      key
      value
    }
  }
`;

const ASSET_NODE_FRAGMENT = `
  fragment AssetNodeFields on AssetNode {
    id
    assetKey {
      path
    }
    description
    groupName
    opNames
    graphName
    isSource
    isObservable
    isPartitioned
    computeKind
    hasMaterializePermission
    dependencyKeys {
      path
    }
    dependedByKeys {
      path
    }
    latestMaterialization {
      timestamp
      runId
    }
  }
`;

const SCHEDULE_FRAGMENT = `
  fragment ScheduleFields on Schedule {
    id
    name
    cronSchedule
    pipelineName
    mode
    description
    executionTimezone
    scheduleState {
      id
      status
      runningCount
    }
    futureTicks(limit: 5) {
      results {
        timestamp
      }
    }
  }
`;

const SENSOR_FRAGMENT = `
  fragment SensorFields on Sensor {
    id
    name
    description
    sensorType
    minIntervalSeconds
    targets {
      pipelineName
      mode
    }
    sensorState {
      id
      status
      runningCount
    }
    nextTick {
      timestamp
    }
  }
`;

// ============= Queries =============

const REPOSITORIES_QUERY = `
  query RepositoriesQuery {
    repositoriesOrError {
      __typename
      ... on RepositoryConnection {
        nodes {
          id
          name
          location {
            name
          }
          pipelines {
            id
            name
            description
            isJob
          }
          assetGroups {
            groupName
          }
        }
      }
      ... on PythonError {
        message
        stack
      }
    }
  }
`;

const RUNS_QUERY = `
  ${RUN_FRAGMENT}
  query RunsQuery($filter: RunsFilter, $limit: Int) {
    runsOrError(filter: $filter, limit: $limit) {
      __typename
      ... on Runs {
        results {
          ...RunFields
        }
      }
      ... on InvalidPipelineRunsFilterError {
        message
      }
      ... on PythonError {
        message
      }
    }
  }
`;

const RUN_DETAILS_QUERY = `
  ${RUN_FRAGMENT}
  query RunDetailsQuery($runId: ID!) {
    runOrError(runId: $runId) {
      __typename
      ... on Run {
        ...RunFields
        stats {
          ... on RunStatsSnapshot {
            stepsSucceeded
            stepsFailed
            materializations
            expectations
          }
        }
        stepStats {
          stepKey
          status
          startTime
          endTime
          attempts {
            startTime
            endTime
            status
          }
        }
      }
      ... on RunNotFoundError {
        message
      }
      ... on PythonError {
        message
      }
    }
  }
`;

const RUN_LOGS_QUERY = `
  query RunLogsQuery($runId: ID!, $afterCursor: String) {
    logsForRun(runId: $runId, afterCursor: $afterCursor) {
      __typename
      ... on EventConnection {
        events {
          __typename
          timestamp
          level
          stepKey
          message
          ... on MessageEvent {
            message
          }
          ... on EngineEvent {
            message
          }
          ... on StepWorkerStartedEvent {
            message
          }
        }
        cursor
        hasMore
      }
      ... on PythonError {
        message
      }
    }
  }
`;

const ASSETS_QUERY = `
  ${ASSET_NODE_FRAGMENT}
  query AssetsQuery($groups: [AssetGroupSelector!], $prefix: [String!]) {
    assetsOrError(prefix: $prefix) {
      __typename
      ... on AssetConnection {
        nodes {
          id
          key {
            path
          }
          definition {
            ...AssetNodeFields
          }
        }
      }
      ... on PythonError {
        message
      }
    }
  }
`;

const ASSET_DETAILS_QUERY = `
  query AssetDetailsQuery($assetKey: AssetKeyInput!) {
    assetOrError(assetKey: $assetKey) {
      __typename
      ... on Asset {
        id
        key {
          path
        }
        definition {
          id
          description
          groupName
          computeKind
          isSource
          isObservable
          isPartitioned
          opNames
          hasMaterializePermission
          dependencyKeys {
            path
          }
          dependedByKeys {
            path
          }
        }
        assetMaterializations(limit: 10) {
          timestamp
          runId
          metadataEntries {
            __typename
            label
            description
            ... on TextMetadataEntry {
              text
            }
            ... on UrlMetadataEntry {
              url
            }
            ... on IntMetadataEntry {
              intValue
            }
            ... on FloatMetadataEntry {
              floatValue
            }
            ... on JsonMetadataEntry {
              jsonString
            }
          }
        }
        assetObservations(limit: 10) {
          timestamp
          runId
        }
      }
      ... on AssetNotFoundError {
        message
      }
    }
  }
`;

const SCHEDULES_QUERY = `
  ${SCHEDULE_FRAGMENT}
  query SchedulesQuery($repositorySelector: RepositorySelector!) {
    schedulesOrError(repositorySelector: $repositorySelector) {
      __typename
      ... on Schedules {
        results {
          ...ScheduleFields
        }
      }
      ... on RepositoryNotFoundError {
        message
      }
      ... on PythonError {
        message
      }
    }
  }
`;

const ALL_SCHEDULES_QUERY = `
  ${SCHEDULE_FRAGMENT}
  query AllSchedulesQuery {
    workspaceOrError {
      __typename
      ... on Workspace {
        locationEntries {
          locationOrLoadError {
            __typename
            ... on RepositoryLocation {
              repositories {
                name
                schedules {
                  ...ScheduleFields
                }
              }
            }
          }
        }
      }
    }
  }
`;

const SENSORS_QUERY = `
  ${SENSOR_FRAGMENT}
  query SensorsQuery($repositorySelector: RepositorySelector!) {
    sensorsOrError(repositorySelector: $repositorySelector) {
      __typename
      ... on Sensors {
        results {
          ...SensorFields
        }
      }
      ... on RepositoryNotFoundError {
        message
      }
      ... on PythonError {
        message
      }
    }
  }
`;

const ALL_SENSORS_QUERY = `
  ${SENSOR_FRAGMENT}
  query AllSensorsQuery {
    workspaceOrError {
      __typename
      ... on Workspace {
        locationEntries {
          locationOrLoadError {
            __typename
            ... on RepositoryLocation {
              repositories {
                name
                sensors {
                  ...SensorFields
                }
              }
            }
          }
        }
      }
    }
  }
`;

const INSTANCE_STATUS_QUERY = `
  query InstanceStatusQuery {
    instance {
      daemonHealth {
        id
        allDaemonStatuses {
          id
          daemonType
          required
          healthy
          lastHeartbeatTime
        }
      }
      hasInfo
      runQueuingSupported
      runLauncher {
        name
      }
    }
  }
`;

// ============= Mutations =============

const LAUNCH_RUN_MUTATION = `
  ${RUN_FRAGMENT}
  mutation LaunchRunMutation($executionParams: ExecutionParams!) {
    launchRun(executionParams: $executionParams) {
      __typename
      ... on LaunchRunSuccess {
        run {
          ...RunFields
        }
      }
      ... on PipelineNotFoundError {
        message
      }
      ... on InvalidStepError {
        invalidStepKey
      }
      ... on InvalidOutputError {
        stepKey
        invalidOutputName
      }
      ... on RunConfigValidationInvalid {
        errors {
          message
        }
      }
      ... on PythonError {
        message
        stack
      }
    }
  }
`;

const TERMINATE_RUN_MUTATION = `
  mutation TerminateRunMutation($runId: String!, $terminatePolicy: TerminateRunPolicy) {
    terminateRun(runId: $runId, terminatePolicy: $terminatePolicy) {
      __typename
      ... on TerminateRunSuccess {
        run {
          id
          runId
          status
        }
      }
      ... on TerminateRunFailure {
        message
      }
      ... on RunNotFoundError {
        message
      }
      ... on PythonError {
        message
      }
    }
  }
`;

const START_SCHEDULE_MUTATION = `
  mutation StartScheduleMutation($scheduleSelector: ScheduleSelector!) {
    startSchedule(scheduleSelector: $scheduleSelector) {
      __typename
      ... on ScheduleStateResult {
        scheduleState {
          id
          status
        }
      }
      ... on UnauthorizedError {
        message
      }
      ... on PythonError {
        message
      }
    }
  }
`;

const STOP_SCHEDULE_MUTATION = `
  mutation StopScheduleMutation($scheduleOriginId: String!, $scheduleSelectorId: String!) {
    stopRunningSchedule(scheduleOriginId: $scheduleOriginId, scheduleSelectorId: $scheduleSelectorId) {
      __typename
      ... on ScheduleStateResult {
        scheduleState {
          id
          status
        }
      }
      ... on UnauthorizedError {
        message
      }
      ... on PythonError {
        message
      }
    }
  }
`;

const START_SENSOR_MUTATION = `
  mutation StartSensorMutation($sensorSelector: SensorSelector!) {
    startSensor(sensorSelector: $sensorSelector) {
      __typename
      ... on Sensor {
        sensorState {
          id
          status
        }
      }
      ... on SensorNotFoundError {
        message
      }
      ... on UnauthorizedError {
        message
      }
      ... on PythonError {
        message
      }
    }
  }
`;

const STOP_SENSOR_MUTATION = `
  mutation StopSensorMutation($jobOriginId: String!, $jobSelectorId: String!) {
    stopSensor(jobOriginId: $jobOriginId, jobSelectorId: $jobSelectorId) {
      __typename
      ... on StopSensorMutationResult {
        instigationState {
          id
          status
        }
      }
      ... on UnauthorizedError {
        message
      }
      ... on PythonError {
        message
      }
    }
  }
`;

// ============= Client Class =============

class DagsterGraphQLClient {
  private graphqlUrl: string;
  private useProxy: boolean;

  constructor(baseUrl = 'http://localhost:3000', useProxy = false) {
    this.useProxy = useProxy;
    if (useProxy) {
      // Use backend proxy to avoid CORS issues
      this.graphqlUrl = '/api/v1/dagster/graphql';
    } else {
      // Direct connection to Dagster
      this.graphqlUrl = `${baseUrl}/graphql`;
    }
  }

  setBaseUrl(baseUrl: string): void {
    if (!this.useProxy) {
      this.graphqlUrl = `${baseUrl}/graphql`;
    }
  }

  setUseProxy(useProxy: boolean): void {
    this.useProxy = useProxy;
    if (useProxy) {
      this.graphqlUrl = '/api/v1/dagster/graphql';
    }
  }

  private async query<T>(query: string, variables?: Record<string, unknown>): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Add auth token if using proxy
    if (this.useProxy) {
      const token = localStorage.getItem('novasight_access_token');
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }

    const response = await fetch(this.graphqlUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({ query, variables }),
    });

    if (!response.ok) {
      throw new Error(`GraphQL request failed: ${response.statusText}`);
    }

    const result: DagsterGraphQLResponse<T> = await response.json();

    if (result.errors && result.errors.length > 0) {
      throw new Error(result.errors[0].message);
    }

    if (!result.data) {
      throw new Error('No data returned from GraphQL query');
    }

    return result.data;
  }

  // ============= Repository Methods =============

  async getRepositories(): Promise<DagsterRepository[]> {
    const data = await this.query<RepositoriesQueryResult>(REPOSITORIES_QUERY);
    
    if (data.repositoriesOrError.__typename === 'PythonError') {
      throw new Error(data.repositoriesOrError.message);
    }

    return data.repositoriesOrError.nodes || [];
  }

  // ============= Run Methods =============

  async getRuns(filter?: DagsterRunsFilter, limit = 50): Promise<DagsterRun[]> {
    const graphqlFilter: Record<string, unknown> = {};
    
    if (filter) {
      if (filter.pipelineName) graphqlFilter.pipelineName = filter.pipelineName;
      if (filter.statuses) graphqlFilter.statuses = filter.statuses;
      if (filter.tags) graphqlFilter.tags = filter.tags;
      if (filter.updatedAfter) graphqlFilter.updatedAfter = filter.updatedAfter;
      if (filter.updatedBefore) graphqlFilter.updatedBefore = filter.updatedBefore;
    }

    const data = await this.query<RunsQueryResult>(RUNS_QUERY, { 
      filter: Object.keys(graphqlFilter).length > 0 ? graphqlFilter : undefined,
      limit 
    });
    
    if (data.runsOrError.__typename !== 'Runs') {
      throw new Error(data.runsOrError.message || 'Failed to fetch runs');
    }

    return data.runsOrError.results || [];
  }

  async getRunDetails(runId: string): Promise<DagsterRun | null> {
    interface RunDetailsResult {
      runOrError: {
        __typename: string;
        message?: string;
      } & DagsterRun;
    }

    const data = await this.query<RunDetailsResult>(RUN_DETAILS_QUERY, { runId });
    
    if (data.runOrError.__typename !== 'Run') {
      return null;
    }

    return data.runOrError;
  }

  async getRunLogs(runId: string, afterCursor?: string): Promise<{
    events: Array<{ timestamp: string; level: string; stepKey: string | null; message: string }>;
    cursor: string;
    hasMore: boolean;
  }> {
    interface LogsResult {
      logsForRun: {
        __typename: string;
        events?: Array<{ timestamp: string; level: string; stepKey: string | null; message: string }>;
        cursor?: string;
        hasMore?: boolean;
        message?: string;
      };
    }

    const data = await this.query<LogsResult>(RUN_LOGS_QUERY, { runId, afterCursor });
    
    if (data.logsForRun.__typename !== 'EventConnection') {
      throw new Error(data.logsForRun.message || 'Failed to fetch logs');
    }

    return {
      events: data.logsForRun.events || [],
      cursor: data.logsForRun.cursor || '',
      hasMore: data.logsForRun.hasMore || false,
    };
  }

  async launchRun(
    pipelineName: string,
    repositoryLocationName: string,
    repositoryName: string,
    mode = 'default',
    runConfigData?: Record<string, unknown>,
    tags?: Array<{ key: string; value: string }>
  ): Promise<DagsterRun> {
    const executionParams = {
      selector: {
        repositoryLocationName,
        repositoryName,
        pipelineName,
      },
      mode,
      runConfigData: runConfigData || {},
      executionMetadata: {
        tags: tags || [],
      },
    };

    const data = await this.query<LaunchRunMutationResult>(LAUNCH_RUN_MUTATION, { executionParams });
    
    if (data.launchRun.__typename !== 'LaunchRunSuccess' || !data.launchRun.run) {
      throw new Error(data.launchRun.message || 'Failed to launch run');
    }

    return data.launchRun.run;
  }

  async terminateRun(runId: string, policy: 'SAFE_TERMINATE' | 'MARK_AS_CANCELED_IMMEDIATELY' = 'SAFE_TERMINATE'): Promise<void> {
    const data = await this.query<TerminateRunMutationResult>(TERMINATE_RUN_MUTATION, { 
      runId, 
      terminatePolicy: policy 
    });
    
    if (data.terminateRun.__typename !== 'TerminateRunSuccess') {
      throw new Error(data.terminateRun.message || 'Failed to terminate run');
    }
  }

  // ============= Asset Methods =============

  async getAssets(prefix?: string[]): Promise<DagsterAssetNode[]> {
    const data = await this.query<AssetsQueryResult>(ASSETS_QUERY, { prefix });
    
    if (data.assetsOrError.__typename !== 'AssetConnection') {
      throw new Error(data.assetsOrError.message || 'Failed to fetch assets');
    }

    // Map the response to our expected format
    // The GraphQL response wraps asset data differently than our types
    const nodes = data.assetsOrError.nodes || [];
    return nodes.map((node) => {
      // Type assertion needed since GraphQL response structure differs from our simplified types
      const assetNode = node as unknown as { 
        id: string;
        key: DagsterAssetKey;
        definition?: DagsterAssetNode;
      };
      return {
        ...(assetNode.definition || {} as DagsterAssetNode),
        id: assetNode.id,
        assetKey: assetNode.key || { path: [] },
      } as DagsterAssetNode;
    });
  }

  async getAssetDetails(assetKey: { path: string[] }): Promise<DagsterAssetNode | null> {
    interface AssetDetailsResult {
      assetOrError: {
        __typename: string;
        id?: string;
        key?: DagsterAssetKey;
        definition?: DagsterAssetNode;
        assetMaterializations?: Array<{
          timestamp: string;
          runId: string;
        }>;
        message?: string;
      };
    }

    const data = await this.query<AssetDetailsResult>(ASSET_DETAILS_QUERY, { assetKey });
    
    if (data.assetOrError.__typename !== 'Asset') {
      return null;
    }

    return {
      ...data.assetOrError.definition,
      assetKey: data.assetOrError.key,
      latestMaterialization: data.assetOrError.assetMaterializations?.[0] || null,
    } as DagsterAssetNode;
  }

  async getAssetGraph(): Promise<DagsterAssetGraph> {
    const assets = await this.getAssets();
    
    const nodes: DagsterAssetGraphNode[] = assets.map((asset) => {
      const id = asset.assetKey.path.join('/');
      let status: DagsterAssetGraphNode['status'] = 'never_materialized';
      
      if (asset.latestMaterialization) {
        status = 'fresh';
      }
      if (asset.latestRun?.status === 'STARTED') {
        status = 'materializing';
      }
      if (asset.latestRun?.status === 'FAILURE') {
        status = 'failed';
      }

      return {
        id,
        assetKey: asset.assetKey,
        label: asset.assetKey.path[asset.assetKey.path.length - 1],
        description: asset.description,
        status,
        lastMaterialization: asset.latestMaterialization?.timestamp || null,
        computeKind: asset.computeKind,
        isSource: asset.isSource,
      };
    });

    const edges: DagsterAssetGraphEdge[] = [];
    
    for (const asset of assets) {
      const targetId = asset.assetKey.path.join('/');
      for (const depKey of asset.dependencyKeys || []) {
        const sourceId = depKey.path.join('/');
        edges.push({ source: sourceId, target: targetId });
      }
    }

    return { nodes, edges };
  }

  // ============= Schedule Methods =============

  async getAllSchedules(): Promise<DagsterSchedule[]> {
    interface AllSchedulesResult {
      workspaceOrError: {
        __typename: string;
        locationEntries?: Array<{
          locationOrLoadError: {
            __typename: string;
            repositories?: Array<{
              name: string;
              schedules: DagsterSchedule[];
            }>;
          };
        }>;
      };
    }

    const data = await this.query<AllSchedulesResult>(ALL_SCHEDULES_QUERY);
    
    if (data.workspaceOrError.__typename !== 'Workspace') {
      return [];
    }

    const schedules: DagsterSchedule[] = [];
    
    for (const entry of data.workspaceOrError.locationEntries || []) {
      if (entry.locationOrLoadError.__typename === 'RepositoryLocation') {
        for (const repo of entry.locationOrLoadError.repositories || []) {
          schedules.push(...repo.schedules);
        }
      }
    }

    return schedules;
  }

  async getSchedules(repositoryLocationName: string, repositoryName: string): Promise<DagsterSchedule[]> {
    const data = await this.query<SchedulesQueryResult>(SCHEDULES_QUERY, {
      repositorySelector: { repositoryLocationName, repositoryName },
    });
    
    if (data.schedulesOrError.__typename !== 'Schedules') {
      throw new Error(data.schedulesOrError.message || 'Failed to fetch schedules');
    }

    return data.schedulesOrError.results || [];
  }

  async startSchedule(
    scheduleName: string,
    repositoryLocationName: string,
    repositoryName: string
  ): Promise<void> {
    const data = await this.query<StartScheduleMutationResult>(START_SCHEDULE_MUTATION, {
      scheduleSelector: { scheduleName, repositoryLocationName, repositoryName },
    });
    
    if (data.startSchedule.__typename !== 'ScheduleStateResult') {
      throw new Error(data.startSchedule.message || 'Failed to start schedule');
    }
  }

  async stopSchedule(scheduleOriginId: string, scheduleSelectorId: string): Promise<void> {
    const data = await this.query<StopScheduleMutationResult>(STOP_SCHEDULE_MUTATION, {
      scheduleOriginId,
      scheduleSelectorId,
    });
    
    if (data.stopRunningSchedule.__typename !== 'ScheduleStateResult') {
      throw new Error(data.stopRunningSchedule.message || 'Failed to stop schedule');
    }
  }

  // ============= Sensor Methods =============

  async getAllSensors(): Promise<DagsterSensor[]> {
    interface AllSensorsResult {
      workspaceOrError: {
        __typename: string;
        locationEntries?: Array<{
          locationOrLoadError: {
            __typename: string;
            repositories?: Array<{
              name: string;
              sensors: DagsterSensor[];
            }>;
          };
        }>;
      };
    }

    const data = await this.query<AllSensorsResult>(ALL_SENSORS_QUERY);
    
    if (data.workspaceOrError.__typename !== 'Workspace') {
      return [];
    }

    const sensors: DagsterSensor[] = [];
    
    for (const entry of data.workspaceOrError.locationEntries || []) {
      if (entry.locationOrLoadError.__typename === 'RepositoryLocation') {
        for (const repo of entry.locationOrLoadError.repositories || []) {
          sensors.push(...repo.sensors);
        }
      }
    }

    return sensors;
  }

  async getSensors(repositoryLocationName: string, repositoryName: string): Promise<DagsterSensor[]> {
    const data = await this.query<SensorsQueryResult>(SENSORS_QUERY, {
      repositorySelector: { repositoryLocationName, repositoryName },
    });
    
    if (data.sensorsOrError.__typename !== 'Sensors') {
      throw new Error(data.sensorsOrError.message || 'Failed to fetch sensors');
    }

    return data.sensorsOrError.results || [];
  }

  async startSensor(
    sensorName: string,
    repositoryLocationName: string,
    repositoryName: string
  ): Promise<void> {
    const data = await this.query<StartSensorMutationResult>(START_SENSOR_MUTATION, {
      sensorSelector: { sensorName, repositoryLocationName, repositoryName },
    });
    
    if (data.startSensor.__typename !== 'Sensor') {
      throw new Error(data.startSensor.message || 'Failed to start sensor');
    }
  }

  async stopSensor(jobOriginId: string, jobSelectorId: string): Promise<void> {
    const data = await this.query<StopSensorMutationResult>(STOP_SENSOR_MUTATION, {
      jobOriginId,
      jobSelectorId,
    });
    
    if (data.stopSensor.__typename !== 'StopSensorMutationResult') {
      throw new Error(data.stopSensor.message || 'Failed to stop sensor');
    }
  }

  // ============= Instance Methods =============

  async getInstanceStatus(): Promise<{
    healthy: boolean;
    daemons: Array<{
      daemonType: string;
      required: boolean;
      healthy: boolean;
      lastHeartbeatTime: number | null;
    }>;
    runLauncher: string | null;
    runQueuingSupported: boolean;
  }> {
    interface InstanceStatusResult {
      instance: {
        daemonHealth: {
          allDaemonStatuses: Array<{
            daemonType: string;
            required: boolean;
            healthy: boolean;
            lastHeartbeatTime: number | null;
          }>;
        };
        runLauncher: { name: string } | null;
        runQueuingSupported: boolean;
      };
    }

    const data = await this.query<InstanceStatusResult>(INSTANCE_STATUS_QUERY);
    
    const daemons = data.instance.daemonHealth.allDaemonStatuses;
    const healthy = daemons.filter(d => d.required).every(d => d.healthy);

    return {
      healthy,
      daemons,
      runLauncher: data.instance.runLauncher?.name || null,
      runQueuingSupported: data.instance.runQueuingSupported,
    };
  }

  // ============= Utility Methods =============

  formatRunStatus(status: DagsterRunStatus): {
    label: string;
    color: 'green' | 'red' | 'yellow' | 'blue' | 'gray';
    isRunning: boolean;
  } {
    const statusMap: Record<DagsterRunStatus, { label: string; color: 'green' | 'red' | 'yellow' | 'blue' | 'gray'; isRunning: boolean }> = {
      'QUEUED': { label: 'Queued', color: 'yellow', isRunning: false },
      'NOT_STARTED': { label: 'Not Started', color: 'gray', isRunning: false },
      'STARTING': { label: 'Starting', color: 'blue', isRunning: true },
      'STARTED': { label: 'Running', color: 'blue', isRunning: true },
      'SUCCESS': { label: 'Success', color: 'green', isRunning: false },
      'FAILURE': { label: 'Failed', color: 'red', isRunning: false },
      'CANCELING': { label: 'Canceling', color: 'yellow', isRunning: true },
      'CANCELED': { label: 'Canceled', color: 'gray', isRunning: false },
    };

    return statusMap[status] || { label: status, color: 'gray', isRunning: false };
  }

  formatAssetKey(assetKey: DagsterAssetKey): string {
    return assetKey.path.join(' > ');
  }

  parseAssetKeyString(keyString: string): DagsterAssetKey {
    return { path: keyString.split(' > ') };
  }
}

// Export singleton instance - use proxy by default to handle CORS
// Set to false if connecting directly to Dagster (e.g., for local development)
export const dagsterClient = new DagsterGraphQLClient('http://localhost:3000', true);

// Export class for testing or multiple instances
export { DagsterGraphQLClient };
