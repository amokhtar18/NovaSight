"""
Dagster GraphQL Proxy Routes

Proxies GraphQL requests from the frontend to the Dagster GraphQL endpoint.
This handles CORS and maintains authentication context.
"""

import requests
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required

dagster_proxy_bp = Blueprint('dagster_proxy', __name__, url_prefix='/dagster')


def get_dagster_url() -> str:
    """Get the Dagster GraphQL URL from configuration."""
    return current_app.config.get('DAGSTER_GRAPHQL_URL', 'http://localhost:3000/graphql')


def get_dagster_timeout() -> int:
    """Get the request timeout for Dagster calls."""
    return current_app.config.get('DAGSTER_REQUEST_TIMEOUT', 30)


@dagster_proxy_bp.route('/graphql', methods=['POST'])
@jwt_required()
def graphql_proxy():
    """
    Proxy GraphQL requests to Dagster.
    
    This endpoint forwards GraphQL queries and mutations from the frontend
    to the Dagster GraphQL endpoint, handling CORS and authentication.
    
    Request Body:
        - query: str - GraphQL query string
        - variables: dict - Optional query variables
        - operationName: str - Optional operation name
    
    Returns:
        Proxied response from Dagster GraphQL endpoint
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'errors': [{'message': 'Request body is required'}]
            }), 400
        
        if 'query' not in data:
            return jsonify({
                'errors': [{'message': 'GraphQL query is required'}]
            }), 400
        
        # Forward request to Dagster
        dagster_url = get_dagster_url()
        timeout = get_dagster_timeout()
        
        response = requests.post(
            dagster_url,
            json=data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            timeout=timeout
        )
        
        # Return the Dagster response
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.ConnectionError:
        return jsonify({
            'errors': [{
                'message': 'Cannot connect to Dagster. Please ensure Dagster is running.',
                'extensions': {'code': 'DAGSTER_UNAVAILABLE'}
            }]
        }), 503
        
    except requests.exceptions.Timeout:
        return jsonify({
            'errors': [{
                'message': 'Request to Dagster timed out.',
                'extensions': {'code': 'DAGSTER_TIMEOUT'}
            }]
        }), 504
        
    except Exception as e:
        current_app.logger.error(f"Dagster proxy error: {str(e)}")
        return jsonify({
            'errors': [{
                'message': f'Internal server error: {str(e)}',
                'extensions': {'code': 'INTERNAL_ERROR'}
            }]
        }), 500


@dagster_proxy_bp.route('/health', methods=['GET'])
def dagster_health():
    """
    Check Dagster instance health.
    
    Returns the health status of the Dagster instance.
    """
    try:
        dagster_url = get_dagster_url()
        timeout = get_dagster_timeout()
        
        # Simple query to check if Dagster is responsive
        query = """
        query HealthCheck {
            instance {
                daemonHealth {
                    id
                    allDaemonStatuses {
                        daemonType
                        healthy
                    }
                }
            }
        }
        """
        
        response = requests.post(
            dagster_url,
            json={'query': query},
            headers={'Content-Type': 'application/json'},
            timeout=timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract daemon health info
            instance = data.get('data', {}).get('instance', {})
            daemon_health = instance.get('daemonHealth', {})
            all_statuses = daemon_health.get('allDaemonStatuses', [])
            
            # Check if all required daemons are healthy
            healthy = all(
                status.get('healthy', False) 
                for status in all_statuses
            ) if all_statuses else False
            
            return jsonify({
                'status': 'healthy' if healthy else 'degraded',
                'dagster_url': dagster_url.replace('/graphql', ''),
                'daemons': all_statuses
            })
        else:
            return jsonify({
                'status': 'unhealthy',
                'error': 'Dagster returned non-200 status'
            }), 503
            
    except requests.exceptions.ConnectionError:
        return jsonify({
            'status': 'offline',
            'error': 'Cannot connect to Dagster'
        }), 503
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@dagster_proxy_bp.route('/runs', methods=['GET'])
@jwt_required()
def list_runs():
    """
    List recent runs from Dagster.
    
    Query Parameters:
        - limit: int - Maximum number of runs to return (default: 25)
        - status: str - Filter by status (optional)
        - job: str - Filter by job name (optional)
    
    Returns:
        List of runs from Dagster
    """
    try:
        limit = request.args.get('limit', 25, type=int)
        status = request.args.get('status')
        job = request.args.get('job')
        
        # Build filter
        filters = {}
        if status:
            filters['statuses'] = [status.upper()]
        if job:
            filters['pipelineName'] = job
        
        query = """
        query RunsQuery($filter: RunsFilter, $limit: Int) {
            runsOrError(filter: $filter, limit: $limit) {
                __typename
                ... on Runs {
                    results {
                        id
                        runId
                        status
                        mode
                        pipelineName
                        startTime
                        endTime
                        canTerminate
                        tags {
                            key
                            value
                        }
                    }
                }
                ... on PythonError {
                    message
                }
            }
        }
        """
        
        dagster_url = get_dagster_url()
        response = requests.post(
            dagster_url,
            json={
                'query': query,
                'variables': {
                    'filter': filters if filters else None,
                    'limit': limit
                }
            },
            headers={'Content-Type': 'application/json'},
            timeout=get_dagster_timeout()
        )
        
        data = response.json()
        
        if 'errors' in data:
            return jsonify({'error': data['errors'][0]['message']}), 400
        
        runs_result = data.get('data', {}).get('runsOrError', {})
        
        if runs_result.get('__typename') == 'PythonError':
            return jsonify({'error': runs_result.get('message')}), 400
        
        runs = runs_result.get('results', [])
        return jsonify({'runs': runs})
        
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Cannot connect to Dagster'}), 503
    except Exception as e:
        current_app.logger.error(f"Error fetching runs: {str(e)}")
        return jsonify({'error': str(e)}), 500


@dagster_proxy_bp.route('/runs/<run_id>', methods=['DELETE'])
@jwt_required()
def terminate_run(run_id: str):
    """
    Terminate a running Dagster run.
    
    Path Parameters:
        - run_id: str - The run ID to terminate
    
    Returns:
        Success or error response
    """
    try:
        mutation = """
        mutation TerminateRun($runId: String!) {
            terminateRun(runId: $runId) {
                __typename
                ... on TerminateRunSuccess {
                    run {
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
        """
        
        dagster_url = get_dagster_url()
        response = requests.post(
            dagster_url,
            json={
                'query': mutation,
                'variables': {'runId': run_id}
            },
            headers={'Content-Type': 'application/json'},
            timeout=get_dagster_timeout()
        )
        
        data = response.json()
        
        if 'errors' in data:
            return jsonify({'error': data['errors'][0]['message']}), 400
        
        result = data.get('data', {}).get('terminateRun', {})
        
        if result.get('__typename') == 'TerminateRunSuccess':
            return jsonify({
                'success': True,
                'run': result.get('run')
            })
        else:
            return jsonify({
                'error': result.get('message', 'Failed to terminate run')
            }), 400
        
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Cannot connect to Dagster'}), 503
    except Exception as e:
        current_app.logger.error(f"Error terminating run: {str(e)}")
        return jsonify({'error': str(e)}), 500


@dagster_proxy_bp.route('/assets', methods=['GET'])
@jwt_required()
def list_assets():
    """
    List assets from Dagster.
    
    Query Parameters:
        - prefix: str - Filter by asset key prefix (optional)
    
    Returns:
        List of assets from Dagster
    """
    try:
        prefix = request.args.get('prefix')
        prefix_list = prefix.split('/') if prefix else None
        
        query = """
        query AssetsQuery($prefix: [String!]) {
            assetsOrError(prefix: $prefix) {
                __typename
                ... on AssetConnection {
                    nodes {
                        id
                        key {
                            path
                        }
                        definition {
                            description
                            groupName
                            computeKind
                            isSource
                            isPartitioned
                            hasMaterializePermission
                            dependencyKeys {
                                path
                            }
                            dependedByKeys {
                                path
                            }
                        }
                    }
                }
                ... on PythonError {
                    message
                }
            }
        }
        """
        
        dagster_url = get_dagster_url()
        response = requests.post(
            dagster_url,
            json={
                'query': query,
                'variables': {'prefix': prefix_list}
            },
            headers={'Content-Type': 'application/json'},
            timeout=get_dagster_timeout()
        )
        
        data = response.json()
        
        if 'errors' in data:
            return jsonify({'error': data['errors'][0]['message']}), 400
        
        assets_result = data.get('data', {}).get('assetsOrError', {})
        
        if assets_result.get('__typename') == 'PythonError':
            return jsonify({'error': assets_result.get('message')}), 400
        
        assets = assets_result.get('nodes', [])
        return jsonify({'assets': assets})
        
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Cannot connect to Dagster'}), 503
    except Exception as e:
        current_app.logger.error(f"Error fetching assets: {str(e)}")
        return jsonify({'error': str(e)}), 500


@dagster_proxy_bp.route('/schedules', methods=['GET'])
@jwt_required()
def list_schedules():
    """
    List schedules from Dagster.
    
    Returns:
        List of schedules from Dagster
    """
    try:
        query = """
        query AllSchedulesQuery {
            workspaceOrError {
                __typename
                ... on Workspace {
                    locationEntries {
                        locationOrLoadError {
                            __typename
                            ... on RepositoryLocation {
                                name
                                repositories {
                                    name
                                    schedules {
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
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        dagster_url = get_dagster_url()
        response = requests.post(
            dagster_url,
            json={'query': query},
            headers={'Content-Type': 'application/json'},
            timeout=get_dagster_timeout()
        )
        
        data = response.json()
        
        if 'errors' in data:
            return jsonify({'error': data['errors'][0]['message']}), 400
        
        # Extract schedules from nested response
        schedules = []
        workspace = data.get('data', {}).get('workspaceOrError', {})
        
        if workspace.get('__typename') == 'Workspace':
            for entry in workspace.get('locationEntries', []):
                loc = entry.get('locationOrLoadError', {})
                if loc.get('__typename') == 'RepositoryLocation':
                    location_name = loc.get('name')
                    for repo in loc.get('repositories', []):
                        repo_name = repo.get('name')
                        for schedule in repo.get('schedules', []):
                            schedule['repositoryLocationName'] = location_name
                            schedule['repositoryName'] = repo_name
                            schedules.append(schedule)
        
        return jsonify({'schedules': schedules})
        
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Cannot connect to Dagster'}), 503
    except Exception as e:
        current_app.logger.error(f"Error fetching schedules: {str(e)}")
        return jsonify({'error': str(e)}), 500


@dagster_proxy_bp.route('/sensors', methods=['GET'])
@jwt_required()
def list_sensors():
    """
    List sensors from Dagster.
    
    Returns:
        List of sensors from Dagster
    """
    try:
        query = """
        query AllSensorsQuery {
            workspaceOrError {
                __typename
                ... on Workspace {
                    locationEntries {
                        locationOrLoadError {
                            __typename
                            ... on RepositoryLocation {
                                name
                                repositories {
                                    name
                                    sensors {
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
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        dagster_url = get_dagster_url()
        response = requests.post(
            dagster_url,
            json={'query': query},
            headers={'Content-Type': 'application/json'},
            timeout=get_dagster_timeout()
        )
        
        data = response.json()
        
        if 'errors' in data:
            return jsonify({'error': data['errors'][0]['message']}), 400
        
        # Extract sensors from nested response
        sensors = []
        workspace = data.get('data', {}).get('workspaceOrError', {})
        
        if workspace.get('__typename') == 'Workspace':
            for entry in workspace.get('locationEntries', []):
                loc = entry.get('locationOrLoadError', {})
                if loc.get('__typename') == 'RepositoryLocation':
                    location_name = loc.get('name')
                    for repo in loc.get('repositories', []):
                        repo_name = repo.get('name')
                        for sensor in repo.get('sensors', []):
                            sensor['repositoryLocationName'] = location_name
                            sensor['repositoryName'] = repo_name
                            sensors.append(sensor)
        
        return jsonify({'sensors': sensors})
        
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Cannot connect to Dagster'}), 503
    except Exception as e:
        current_app.logger.error(f"Error fetching sensors: {str(e)}")
        return jsonify({'error': str(e)}), 500
