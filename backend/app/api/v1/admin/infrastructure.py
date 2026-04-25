"""
NovaSight Admin Infrastructure Configuration API
=================================================

API endpoints for managing infrastructure server configurations.
Allows portal admins to configure ClickHouse, Spark, and Ollama connections.
"""

from flask import request, jsonify
from app.api.v1.admin import admin_bp
from app.platform.auth.decorators import authenticated
from app.platform.auth.identity import get_current_identity


def _get_user_id() -> str:
    """Extract user_id from current identity."""
    return str(get_current_identity().user_id)
from app.domains.tenants.infrastructure.config_service import (
    InfrastructureConfigService,
    InfrastructureConfigError,
    InfrastructureConfigNotFoundError,
)
from app.platform.auth.decorators import require_permission
from app.domains.tenants.schemas.infrastructure_schemas import (
    InfrastructureConfigResponseSchema,
    InfrastructureConfigListSchema,
    InfrastructureConfigUpdateSchema,
    InfrastructureConfigTestSchema,
    InfrastructureConfigTestResultSchema,
    ClickHouseConfigCreateSchema,
    SparkConfigCreateSchema,
    OllamaConfigCreateSchema,
    S3StorageConfigCreateSchema,
)
from app.errors import ValidationError, NotFoundError
from marshmallow import ValidationError as MarshmallowValidationError
import logging

logger = logging.getLogger(__name__)

# Schema mapping for different service types
CREATE_SCHEMAS = {
    'clickhouse': ClickHouseConfigCreateSchema,
    'spark': SparkConfigCreateSchema,
    'ollama': OllamaConfigCreateSchema,
    'object_storage': S3StorageConfigCreateSchema,
}


@admin_bp.route('/infrastructure/configs', methods=['GET'])
@authenticated
@require_permission('admin.infrastructure.view')
def list_infrastructure_configs():
    """
    List all infrastructure configurations.
    
    Query Parameters:
        - service_type: Filter by service type (clickhouse, spark, ollama, object_storage)
        - tenant_id: Filter by tenant ID
        - include_global: Include global configs (default: true)
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
    
    Returns:
        Paginated list of infrastructure configurations
    """
    service_type = request.args.get('service_type')
    tenant_id = request.args.get('tenant_id')
    include_global = request.args.get('include_global', 'true').lower() == 'true'
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    service = InfrastructureConfigService()
    result = service.list_configs(
        service_type=service_type,
        tenant_id=tenant_id,
        include_global=include_global,
        page=page,
        per_page=per_page,
    )
    
    return jsonify(InfrastructureConfigListSchema().dump(result))


@admin_bp.route('/infrastructure/configs/<uuid:config_id>', methods=['GET'])
@authenticated
@require_permission('admin.infrastructure.view')
def get_infrastructure_config(config_id):
    """
    Get infrastructure configuration by ID.
    
    Args:
        config_id: Configuration UUID
    
    Returns:
        Configuration details
    """
    service = InfrastructureConfigService()
    config = service.get_config(str(config_id))
    
    if not config:
        raise NotFoundError('Configuration not found')
    
    return jsonify({
        'config': InfrastructureConfigResponseSchema().dump(config.to_dict())
    })


@admin_bp.route('/infrastructure/configs/active/<service_type>', methods=['GET'])
@authenticated
@require_permission('admin.infrastructure.view')
def get_active_infrastructure_config(service_type):
    """
    Get the active configuration for a service type.
    
    Args:
        service_type: Service type (clickhouse, spark, ollama)
    
    Query Parameters:
        - tenant_id: Optional tenant ID for tenant-specific config
    
    Returns:
        Active configuration or default settings
    """
    if service_type not in ['clickhouse', 'spark', 'ollama']:
        raise ValidationError(f"Invalid service type: {service_type}")
    
    tenant_id = request.args.get('tenant_id')
    
    service = InfrastructureConfigService()
    config = service.get_active_config(service_type, tenant_id)
    
    if config:
        return jsonify({
            'config': InfrastructureConfigResponseSchema().dump(config.to_dict()),
            'source': 'database'
        })
    else:
        # Return default settings from environment
        settings = service.get_effective_settings(service_type, tenant_id)
        return jsonify({
            'config': {
                'service_type': service_type,
                'name': f'Default {service_type.title()}',
                'host': settings.get('host'),
                'port': settings.get('port'),
                'settings': settings,
                'is_system_default': True,
            },
            'source': 'environment'
        })


@admin_bp.route('/infrastructure/configs', methods=['POST'])
@authenticated
@require_permission('admin.infrastructure.create')
def create_infrastructure_config():
    """
    Create a new infrastructure configuration.
    
    Request Body:
        - service_type: Service type (clickhouse, spark, ollama) - required
        - name: Display name - required
        - host: Server hostname - required
        - port: Server port - required
        - settings: Service-specific settings - required
        - tenant_id: Optional tenant ID for tenant-specific config
        - description: Optional description
        - is_active: Whether this config is active (default: true)
    
    Returns:
        Created configuration details
    """
    json_data = request.get_json() or {}
    service_type = json_data.get('service_type')
    
    if not service_type or service_type not in CREATE_SCHEMAS:
        raise ValidationError(
            f"Invalid or missing service_type. Must be one of: {list(CREATE_SCHEMAS.keys())}"
        )
    
    schema = CREATE_SCHEMAS[service_type]()
    
    try:
        data = schema.load(json_data)
    except MarshmallowValidationError as e:
        raise ValidationError(str(e.messages))
    
    current_user_id = _get_user_id()
    service = InfrastructureConfigService()
    
    try:
        config = service.create_config(
            service_type=data['service_type'],
            name=data['name'],
            host=data['host'],
            port=data['port'],
            settings=data['settings'],
            tenant_id=str(data['tenant_id']) if data.get('tenant_id') else None,
            description=data.get('description'),
            is_active=data.get('is_active', True),
            created_by=current_user_id,
        )
    except InfrastructureConfigError as e:
        raise ValidationError(str(e))
    
    logger.info(
        f"Infrastructure config created: {service_type}:{config.name} "
        f"by user {current_user_id}"
    )
    
    return jsonify({
        'config': InfrastructureConfigResponseSchema().dump(config.to_dict()),
        'message': 'Configuration created successfully'
    }), 201


@admin_bp.route('/infrastructure/configs/<uuid:config_id>', methods=['PUT'])
@authenticated
@require_permission('admin.infrastructure.edit')
def update_infrastructure_config(config_id):
    """
    Update an infrastructure configuration.
    
    Args:
        config_id: Configuration UUID
    
    Request Body:
        - name: Display name
        - description: Description
        - host: Server hostname
        - port: Server port
        - is_active: Whether this config is active
        - settings: Service-specific settings (merged with existing)
    
    Returns:
        Updated configuration details
    """
    try:
        data = InfrastructureConfigUpdateSchema().load(request.get_json() or {})
    except MarshmallowValidationError as e:
        raise ValidationError(str(e.messages))
    
    current_user_id = _get_user_id()
    service = InfrastructureConfigService()
    
    try:
        config = service.update_config(
            config_id=str(config_id),
            updated_by=current_user_id,
            **data
        )
    except InfrastructureConfigNotFoundError:
        raise NotFoundError('Configuration not found')
    except InfrastructureConfigError as e:
        raise ValidationError(str(e))
    
    logger.info(f"Infrastructure config updated: {config_id} by user {current_user_id}")
    
    return jsonify({
        'config': InfrastructureConfigResponseSchema().dump(config.to_dict()),
        'message': 'Configuration updated successfully'
    })


@admin_bp.route('/infrastructure/configs/<uuid:config_id>', methods=['DELETE'])
@authenticated
@require_permission('admin.infrastructure.delete')
def delete_infrastructure_config(config_id):
    """
    Delete an infrastructure configuration.
    
    Args:
        config_id: Configuration UUID
    
    Returns:
        Success message
    """
    current_user_id = _get_user_id()
    service = InfrastructureConfigService()
    
    try:
        service.delete_config(str(config_id))
    except InfrastructureConfigNotFoundError:
        raise NotFoundError('Configuration not found')
    except InfrastructureConfigError as e:
        raise ValidationError(str(e))
    
    logger.info(f"Infrastructure config deleted: {config_id} by user {current_user_id}")
    
    return jsonify({
        'message': 'Configuration deleted successfully'
    })


@admin_bp.route('/infrastructure/configs/test', methods=['POST'])
@authenticated
@require_permission('admin.infrastructure.test')
def test_infrastructure_connection():
    """
    Test connection to an infrastructure service.
    
    Request Body:
        Either:
        - config_id: Existing configuration ID to test
        Or:
        - service_type: Service type for inline test
        - host: Server hostname
        - port: Server port
        - settings: Service-specific settings
    
    Returns:
        Connection test result
    """
    try:
        data = InfrastructureConfigTestSchema().load(request.get_json() or {})
    except MarshmallowValidationError as e:
        raise ValidationError(str(e.messages))
    
    service = InfrastructureConfigService()
    
    try:
        result = service.test_connection(
            config_id=str(data['config_id']) if data.get('config_id') else None,
            service_type=data.get('service_type'),
            host=data.get('host'),
            port=data.get('port'),
            settings=data.get('settings'),
        )
    except InfrastructureConfigNotFoundError:
        raise NotFoundError('Configuration not found')
    except InfrastructureConfigError as e:
        result = {
            'success': False,
            'message': str(e),
        }
    except Exception as e:
        result = {
            'success': False,
            'message': f'Test failed: {str(e)}',
        }
    
    return jsonify(InfrastructureConfigTestResultSchema().dump(result))


@admin_bp.route('/infrastructure/configs/<uuid:config_id>/activate', methods=['POST'])
@authenticated
@require_permission('admin.infrastructure.edit')
def activate_infrastructure_config(config_id):
    """
    Activate an infrastructure configuration.
    
    This will deactivate any other configuration of the same type
    within the same scope (global or tenant-specific).
    
    Args:
        config_id: Configuration UUID
    
    Returns:
        Updated configuration details
    """
    current_user_id = _get_user_id()
    service = InfrastructureConfigService()
    
    try:
        config = service.update_config(
            config_id=str(config_id),
            updated_by=current_user_id,
            is_active=True,
        )
    except InfrastructureConfigNotFoundError:
        raise NotFoundError('Configuration not found')
    except InfrastructureConfigError as e:
        raise ValidationError(str(e))
    
    logger.info(f"Infrastructure config activated: {config_id} by user {current_user_id}")
    
    return jsonify({
        'config': InfrastructureConfigResponseSchema().dump(config.to_dict()),
        'message': 'Configuration activated successfully'
    })


@admin_bp.route('/infrastructure/defaults', methods=['POST'])
@authenticated
@require_permission('admin.infrastructure.create')
def initialize_infrastructure_defaults():
    """
    Initialize system default configurations.
    
    Creates default configurations for all infrastructure types
    if they don't already exist. Useful for initial setup.
    
    Returns:
        Success message
    """
    service = InfrastructureConfigService()
    service.initialize_defaults()
    
    logger.info("Infrastructure defaults initialized")
    
    return jsonify({
        'message': 'Default configurations initialized successfully'
    })


# ============================================================================
# Tenant-Specific ClickHouse Configuration
# ============================================================================

@admin_bp.route('/tenants/<uuid:tenant_id>/clickhouse-config', methods=['GET'])
@authenticated
@require_permission('admin.infrastructure.view')
def get_tenant_clickhouse_config(tenant_id):
    """
    Get ClickHouse configuration for a specific tenant.
    
    Args:
        tenant_id: Tenant UUID
    
    Returns:
        Tenant's ClickHouse configuration or error if not configured
    """
    service = InfrastructureConfigService()
    config = service.get_active_config('clickhouse', str(tenant_id))
    
    if config:
        return jsonify({
            'config': InfrastructureConfigResponseSchema().dump(config.to_dict()),
            'source': 'tenant',
            'tenant_id': str(tenant_id),
        })
    
    # No tenant-specific config - return error (no fallback to global)
    raise NotFoundError('No Configured Analytics Platform. Please configure a ClickHouse instance for this tenant.')


@admin_bp.route('/tenants/<uuid:tenant_id>/clickhouse-config', methods=['POST'])
@authenticated
@require_permission('admin.infrastructure.create')
def create_tenant_clickhouse_config(tenant_id):
    """
    Create ClickHouse configuration for a specific tenant.
    
    This allows a tenant to use a different ClickHouse instance
    than the global default.
    
    Args:
        tenant_id: Tenant UUID
    
    Request Body:
        - name: Display name
        - host: ClickHouse server hostname
        - port: ClickHouse HTTP port (default: 8123)
        - settings: ClickHouse settings (database, user, password, etc.)
        - description: Optional description
    
    Returns:
        Created configuration
    """
    json_data = request.get_json() or {}
    
    # Force service_type and tenant_id
    json_data['service_type'] = 'clickhouse'
    json_data['tenant_id'] = str(tenant_id)
    
    schema = ClickHouseConfigCreateSchema()
    
    try:
        data = schema.load(json_data)
    except MarshmallowValidationError as e:
        raise ValidationError(str(e.messages))
    
    # Verify tenant exists
    from app.domains.tenants.application.tenant_service import TenantService
    tenant = TenantService().get_tenant(str(tenant_id))
    if not tenant:
        raise NotFoundError(f'Tenant not found: {tenant_id}')
    
    current_user_id = _get_user_id()
    service = InfrastructureConfigService()
    
    try:
        config = service.create_config(
            service_type='clickhouse',
            name=data['name'],
            host=data['host'],
            port=data['port'],
            settings=data['settings'],
            tenant_id=str(tenant_id),
            description=data.get('description'),
            is_active=data.get('is_active', True),
            created_by=current_user_id,
        )
    except InfrastructureConfigError as e:
        raise ValidationError(str(e))
    
    logger.info(
        f"Tenant ClickHouse config created for {tenant.slug} by user {current_user_id}"
    )
    
    return jsonify({
        'config': InfrastructureConfigResponseSchema().dump(config.to_dict()),
        'message': f'ClickHouse configuration created for tenant {tenant.slug}'
    }), 201


@admin_bp.route('/tenants/<uuid:tenant_id>/clickhouse-config', methods=['PUT'])
@authenticated
@require_permission('admin.infrastructure.edit')
def update_tenant_clickhouse_config(tenant_id):
    """
    Update ClickHouse configuration for a specific tenant.
    
    Args:
        tenant_id: Tenant UUID
    
    Request Body:
        - name: Display name
        - host: Server hostname
        - port: Server port
        - settings: ClickHouse settings
        - is_active: Whether this config is active
    
    Returns:
        Updated configuration
    """
    try:
        data = InfrastructureConfigUpdateSchema().load(request.get_json() or {})
    except MarshmallowValidationError as e:
        raise ValidationError(str(e.messages))
    
    service = InfrastructureConfigService()
    
    # Find tenant's active ClickHouse config
    config = service.get_active_config('clickhouse', str(tenant_id))
    if not config or str(config.tenant_id) != str(tenant_id):
        raise NotFoundError(f'No ClickHouse configuration found for tenant {tenant_id}')
    
    current_user_id = _get_user_id()
    
    try:
        updated_config = service.update_config(
            config_id=str(config.id),
            updated_by=current_user_id,
            **data
        )
    except InfrastructureConfigError as e:
        raise ValidationError(str(e))
    
    logger.info(f"Tenant ClickHouse config updated for tenant {tenant_id}")
    
    return jsonify({
        'config': InfrastructureConfigResponseSchema().dump(updated_config.to_dict()),
        'message': 'ClickHouse configuration updated successfully'
    })


@admin_bp.route('/tenants/<uuid:tenant_id>/clickhouse-config', methods=['DELETE'])
@authenticated
@require_permission('admin.infrastructure.delete')
def delete_tenant_clickhouse_config(tenant_id):
    """
    Delete tenant-specific ClickHouse configuration.
    
    After deletion, the tenant will use the global ClickHouse configuration.
    
    Args:
        tenant_id: Tenant UUID
    
    Returns:
        Success message
    """
    service = InfrastructureConfigService()
    
    # Find tenant's ClickHouse configs
    configs = InfrastructureConfigService().list_configs(
        service_type='clickhouse',
        tenant_id=str(tenant_id),
        include_global=False,
    )
    
    if not configs['items']:
        raise NotFoundError(f'No ClickHouse configuration found for tenant {tenant_id}')
    
    current_user_id = _get_user_id()
    
    # Delete all tenant-specific ClickHouse configs
    from app.domains.tenants.domain.models import InfrastructureConfig
    for config_data in configs['items']:
        try:
            service.delete_config(config_data['id'])
        except InfrastructureConfigError as e:
            logger.warning(f"Failed to delete config {config_data['id']}: {e}")
    
    logger.info(f"Tenant ClickHouse config deleted for tenant {tenant_id} by {current_user_id}")
    
    return jsonify({
        'message': f'ClickHouse configuration deleted. Tenant will now use global configuration.'
    })


@admin_bp.route('/tenants/<uuid:tenant_id>/clickhouse-config/test', methods=['POST'])
@authenticated
@require_permission('admin.infrastructure.test')
def test_tenant_clickhouse_connection(tenant_id):
    """
    Test ClickHouse connection for a tenant.
    
    Tests either the tenant's active config or inline settings.
    
    Args:
        tenant_id: Tenant UUID
    
    Request Body (optional):
        - host: Server hostname (for inline test)
        - port: Server port
        - settings: Connection settings
    
    Returns:
        Connection test result
    """
    json_data = request.get_json() or {}
    service = InfrastructureConfigService()
    
    if json_data.get('host'):
        # Inline test with provided settings
        try:
            result = service.test_connection(
                service_type='clickhouse',
                host=json_data.get('host'),
                port=json_data.get('port', 8123),
                settings=json_data.get('settings', {}),
            )
        except Exception as e:
            result = {'success': False, 'message': str(e)}
    else:
        # Test tenant's active config
        config = service.get_active_config('clickhouse', str(tenant_id))
        if config:
            try:
                result = service.test_connection(config_id=str(config.id))
            except Exception as e:
                result = {'success': False, 'message': str(e)}
        else:
            result = {
                'success': False,
                'message': 'No ClickHouse configuration found for this tenant'
            }
    
    return jsonify(InfrastructureConfigTestResultSchema().dump(result))


# ============================================================================
# Global Spark Configuration (No Tenant Scope)
# ============================================================================

@admin_bp.route('/settings/spark', methods=['GET'])
@authenticated
@require_permission('admin.infrastructure.view')
def get_global_spark_config():
    """
    Get global Spark configuration.
    
    Spark is always global (not per-tenant) as it's a shared compute resource.
    
    Returns:
        Global Spark configuration
    """
    service = InfrastructureConfigService()
    config = service.get_active_config('spark', None)
    
    if config:
        return jsonify({
            'config': InfrastructureConfigResponseSchema().dump(config.to_dict()),
            'source': 'database',
        })
    
    # Return default settings
    settings = service.get_effective_settings('spark', None)
    return jsonify({
        'config': {
            'service_type': 'spark',
            'name': 'Default Spark',
            'host': settings.get('host', 'spark-master'),
            'port': settings.get('port', 7077),
            'settings': settings,
            'is_system_default': True,
        },
        'source': 'environment',
    })


@admin_bp.route('/settings/spark', methods=['POST'])
@authenticated
@require_permission('admin.infrastructure.create')
def create_global_spark_config():
    """
    Create or update global Spark configuration.
    
    Spark is always global. This endpoint creates a new config
    or can be used to set up the initial Spark configuration.
    
    Request Body:
        - name: Display name
        - host: Spark master hostname
        - port: Spark master port (default: 7077)
        - settings: Spark settings (master_url, memory, cores, etc.)
        - description: Optional description
    
    Returns:
        Created/updated configuration
    """
    json_data = request.get_json() or {}
    
    # Force service_type and ensure no tenant_id
    json_data['service_type'] = 'spark'
    json_data['tenant_id'] = None  # Global only
    
    schema = SparkConfigCreateSchema()
    
    try:
        data = schema.load(json_data)
    except MarshmallowValidationError as e:
        raise ValidationError(str(e.messages))
    
    current_user_id = _get_user_id()
    service = InfrastructureConfigService()
    
    try:
        config = service.create_config(
            service_type='spark',
            name=data['name'],
            host=data['host'],
            port=data['port'],
            settings=data['settings'],
            tenant_id=None,  # Global only
            description=data.get('description'),
            is_active=data.get('is_active', True),
            created_by=current_user_id,
        )
    except InfrastructureConfigError as e:
        raise ValidationError(str(e))
    
    logger.info(f"Global Spark config created by user {current_user_id}")
    
    return jsonify({
        'config': InfrastructureConfigResponseSchema().dump(config.to_dict()),
        'message': 'Global Spark configuration created successfully'
    }), 201


@admin_bp.route('/settings/spark', methods=['PUT'])
@authenticated
@require_permission('admin.infrastructure.edit')
def update_global_spark_config():
    """
    Update global Spark configuration.
    
    Args:
        None (always updates the active global Spark config)
    
    Request Body:
        - name: Display name
        - host: Spark master hostname
        - port: Spark master port
        - settings: Spark settings
        - is_active: Whether this config is active
    
    Returns:
        Updated configuration
    """
    try:
        data = InfrastructureConfigUpdateSchema().load(request.get_json() or {})
    except MarshmallowValidationError as e:
        raise ValidationError(str(e.messages))
    
    service = InfrastructureConfigService()
    
    # Find the active global Spark config
    config = service.get_active_config('spark', None)
    if not config:
        raise NotFoundError('No global Spark configuration found. Create one first.')
    
    current_user_id = _get_user_id()
    
    try:
        updated_config = service.update_config(
            config_id=str(config.id),
            updated_by=current_user_id,
            **data
        )
    except InfrastructureConfigError as e:
        raise ValidationError(str(e))
    
    logger.info(f"Global Spark config updated by user {current_user_id}")
    
    return jsonify({
        'config': InfrastructureConfigResponseSchema().dump(updated_config.to_dict()),
        'message': 'Global Spark configuration updated successfully'
    })


@admin_bp.route('/settings/spark/test', methods=['POST'])
@authenticated
@require_permission('admin.infrastructure.test')
def test_global_spark_connection():
    """
    Test global Spark connection.
    
    Tests either the current active config or inline settings.
    
    Request Body (optional):
        - host: Spark master hostname
        - port: Spark master port
        - settings: Spark settings
    
    Returns:
        Connection test result
    """
    json_data = request.get_json() or {}
    service = InfrastructureConfigService()
    
    if json_data.get('host'):
        # Inline test with provided settings
        try:
            result = service.test_connection(
                service_type='spark',
                host=json_data.get('host'),
                port=json_data.get('port', 7077),
                settings=json_data.get('settings', {}),
            )
        except Exception as e:
            result = {'success': False, 'message': str(e)}
    else:
        # Test active global config
        config = service.get_active_config('spark', None)
        if config:
            try:
                result = service.test_connection(config_id=str(config.id))
            except Exception as e:
                result = {'success': False, 'message': str(e)}
        else:
            result = {
                'success': False,
                'message': 'No global Spark configuration found'
            }
    
    return jsonify(InfrastructureConfigTestResultSchema().dump(result))
