import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { AuthProvider } from '@/contexts/AuthContext'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { MainLayout } from '@/components/layout/MainLayout'
import { MarketingLayout } from '@/components/marketing/layout'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { RegisterPage } from '@/features/auth/pages/RegisterPage'
import { ForgotPasswordPage } from '@/features/auth/pages/ForgotPasswordPage'
import { ResetPasswordPage } from '@/features/auth/pages/ResetPasswordPage'
import {
  HomePage,
  FeaturesPage,
  SolutionsPage,
  PricingPage,
  AboutPage,
  ContactPage,
  ComingSoonPage,
} from '@/pages/marketing'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'
import { DagsterDashboardPage } from '@/pages/orchestration/DagsterDashboardPage'
import { SchedulingPage } from '@/pages/orchestration/SchedulingPage'
import { JobBuilderPage } from '@/pages/orchestration/JobBuilderPage'
import { JobDetailPage } from '@/pages/orchestration/JobDetailPage'
import { DataSourcesPage, DataSourceDetailPage } from '@/features/datasources'
import { 
  PipelinesListPage, 
  PipelineBuilderPage, 
} from '@/pages/pipelines'
import { EnhancedDbtStudioPage, ModelDetailPage as DbtModelDetailPage } from '@/features/dbt-studio'
import { DashboardsListPage, DashboardBuilderPage } from '@/features/dashboards'
import { AIWorkbenchPage } from '@/features/query'
import { SqlEditorPage } from '@/features/sql-editor'
import { ChartsListPage, ChartBuilderPage, ChartViewPage } from '@/pages/charts'
import { DatasetsListPage, DatasetDetailPage, DatasetCreatePage } from '@/features/datasets'
import { DocumentationPage } from '@/pages/documentation'
import { InfrastructureConfigPage, AuditLogsPage, RolesManagementPage, DbtOperationsPage, BackupManagementPage, TenantUserManagementPage } from '@/pages/admin'
import { SettingsPage } from '@/pages/settings'
import {
  PortalLayout,
  PortalOverviewPage,
  TenantManagementPage,
  TenantDetailPage,
  UserManagementPage,
} from '@/pages/portal'

function App() {
  return (
    <ThemeProvider defaultTheme="light" storageKey="novasight-theme">
      <AuthProvider>
        <Routes>
          {/* Marketing routes - Public */}
          <Route element={<MarketingLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/features" element={<FeaturesPage />} />
            <Route path="/solutions" element={<SolutionsPage />} />
            <Route path="/pricing" element={<PricingPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/contact" element={<ContactPage />} />
            
            {/* Coming Soon marketing pages */}
            <Route path="/integrations" element={<ComingSoonPage />} />
            <Route path="/changelog" element={<ComingSoonPage />} />
            <Route path="/roadmap" element={<ComingSoonPage />} />
            <Route path="/solutions/startups" element={<ComingSoonPage />} />
            <Route path="/solutions/enterprise" element={<ComingSoonPage />} />
            <Route path="/solutions/data-teams" element={<ComingSoonPage />} />
            <Route path="/solutions/analytics" element={<ComingSoonPage />} />
            <Route path="/blog" element={<ComingSoonPage />} />
            <Route path="/careers" element={<ComingSoonPage />} />
            <Route path="/press" element={<ComingSoonPage />} />
            <Route path="/docs/api" element={<ComingSoonPage />} />
            <Route path="/community" element={<ComingSoonPage />} />
            <Route path="/support" element={<ComingSoonPage />} />
            <Route path="/status" element={<ComingSoonPage />} />
            <Route path="/privacy" element={<ComingSoonPage />} />
            <Route path="/terms" element={<ComingSoonPage />} />
          </Route>

          {/* Public routes - Authentication */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />

          {/* Protected routes */}
          <Route
            path="/app"
            element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/app/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            
            {/* Data Sources */}
            <Route path="datasources" element={<DataSourcesPage />} />
            <Route path="datasources/:id" element={<DataSourceDetailPage />} />
            
            {/* Orchestration - Redirect to Scheduling */}
            <Route path="orchestration" element={<Navigate to="/app/jobs" replace />} />
            <Route path="dags" element={<Navigate to="/app/jobs" replace />} />
            <Route path="dags/*" element={<Navigate to="/app/jobs" replace />} />
            
            {/* Scheduling - Unified Job & Run Management */}
            <Route path="jobs" element={<SchedulingPage />} />
            <Route path="jobs/new" element={<JobBuilderPage />} />
            <Route path="jobs/:jobId" element={<JobDetailPage />} />
            <Route path="jobs/:jobId/edit" element={<JobBuilderPage />} />
            <Route path="jobs/:jobId/runs" element={<JobDetailPage />} />
            
            {/* Data Pipelines */}
            <Route path="pipelines" element={<PipelinesListPage />} />
            <Route path="pipelines/new" element={<PipelineBuilderPage />} />
            <Route path="pipelines/:id" element={<PipelinesListPage />} />
            <Route path="pipelines/:id/edit" element={<PipelineBuilderPage />} />
            
            {/* Legacy PySpark redirect */}
            <Route path="pyspark" element={<Navigate to="/app/pipelines" replace />} />
            <Route path="pyspark/*" element={<Navigate to="/app/pipelines" replace />} />
            
            {/* Semantic Layer (removed; redirect retained for old links) */}
            <Route path="semantic" element={<Navigate to="/app/datasets" replace />} />
            <Route path="semantic/*" element={<Navigate to="/app/datasets" replace />} />
            
            {/* dbt Studio - No-code/Low-code dbt Builder */}
            <Route path="dbt-studio" element={<EnhancedDbtStudioPage />} />
            <Route path="dbt-studio/models/:modelName" element={<DbtModelDetailPage />} />
            
            {/* Analytics Dashboards */}
            <Route path="dashboards" element={<DashboardsListPage />} />
            <Route path="dashboards/:dashboardId" element={<DashboardBuilderPage />} />
            
            {/* Charts */}
            <Route path="charts" element={<ChartsListPage />} />
            <Route path="charts/new" element={<ChartBuilderPage />} />
            <Route path="charts/:chartId" element={<ChartViewPage />} />
            <Route path="charts/:chartId/edit" element={<ChartBuilderPage />} />

            {/* Datasets — Superset-inspired reusable data sources */}
            <Route path="datasets" element={<DatasetsListPage />} />
            <Route path="datasets/new" element={<DatasetCreatePage />} />
            <Route path="datasets/:id" element={<DatasetDetailPage />} />
            
            {/* AI Query Interface */}
            <Route path="query" element={<AIWorkbenchPage />} />
            
            {/* SQL Editor */}
            <Route path="sql" element={<SqlEditorPage />} />
            <Route path="sql-editor" element={<SqlEditorPage />} />
            
            {/* Admin Pages */}
            <Route path="admin/infrastructure" element={<InfrastructureConfigPage />} />
            <Route path="admin/users" element={<TenantUserManagementPage />} />
            <Route path="admin/audit" element={<AuditLogsPage />} />
            <Route path="admin/roles" element={<RolesManagementPage />} />
            <Route path="admin/dbt" element={<DbtOperationsPage />} />
            <Route path="admin/backups" element={<BackupManagementPage />} />
            
            {/* Portal Management (Super Admin) */}
            <Route path="portal" element={<PortalLayout />}>
              <Route index element={<PortalOverviewPage />} />
              <Route path="tenants" element={<TenantManagementPage />} />
              <Route path="tenants/:tenantId" element={<TenantDetailPage />} />
              <Route path="users" element={<UserManagementPage />} />
              <Route path="infrastructure" element={<InfrastructureConfigPage />} />
              <Route path="roles" element={<RolesManagementPage />} />
              <Route path="audit" element={<AuditLogsPage />} />
            </Route>
            
            {/* Settings */}
            <Route path="settings" element={<SettingsPage />} />
            
            {/* Documentation */}
            <Route path="docs" element={<DocumentationPage />} />
          </Route>

          {/* Legacy routes - redirect to new /app prefix */}
          <Route path="/dashboard" element={<Navigate to="/app/dashboard" replace />} />
          <Route path="/connections" element={<Navigate to="/app/datasources" replace />} />
          <Route path="/datasources" element={<Navigate to="/app/datasources" replace />} />
          <Route path="/dags" element={<Navigate to="/app/jobs" replace />} />
          <Route path="/jobs" element={<Navigate to="/app/jobs" replace />} />
          <Route path="/pyspark" element={<Navigate to="/app/pipelines" replace />} />
          <Route path="/semantic" element={<Navigate to="/app/datasets" replace />} />
          <Route path="/dashboards" element={<Navigate to="/app/dashboards" replace />} />
          <Route path="/query" element={<Navigate to="/app/query" replace />} />
          <Route path="/settings" element={<Navigate to="/app/settings" replace />} />
          <Route path="/docs" element={<Navigate to="/app/docs" replace />} />
          <Route path="/portal" element={<Navigate to="/app/portal" replace />} />
          
          {/* Catch all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Toaster />
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App
