import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { AuthProvider } from '@/contexts/AuthContext'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { MainLayout } from '@/components/layout/MainLayout'
import { LoginPage } from '@/pages/auth/LoginPage'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'
import { DagsListPage } from '@/pages/orchestration/DagsListPage'
import { DagBuilderPage } from '@/pages/orchestration/DagBuilderPage'
import { DagMonitorPage } from '@/pages/orchestration/DagMonitorPage'
import { ConnectionsPage } from '@/pages/connections/ConnectionsPage'

function App() {
  return (
    <ThemeProvider defaultTheme="light" storageKey="novasight-theme">
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            
            {/* Data Connections */}
            <Route path="connections" element={<ConnectionsPage />} />
            
            {/* Orchestration - DAGs */}
            <Route path="dags" element={<DagsListPage />} />
            <Route path="dags/new" element={<DagBuilderPage />} />
            <Route path="dags/:dagId/edit" element={<DagBuilderPage />} />
            <Route path="dags/:dagId/monitor" element={<DagMonitorPage />} />
          </Route>

          {/* Catch all */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
        <Toaster />
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App
