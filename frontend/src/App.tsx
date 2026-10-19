import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { AgentsPage } from './pages/AgentsPage';
import { ScenariosPage } from './pages/ScenariosPage';
import { RunExecutionPage } from './pages/RunExecutionPage';
import { RunsListPage } from './pages/RunsListPage';
import { RunDetailsPage } from './pages/RunDetailsPage';
import { DiagnosisPage } from './pages/DiagnosisPage';
import { ComparisonPage } from './pages/ComparisonPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="agents" element={<AgentsPage />} />
          <Route path="scenarios" element={<ScenariosPage />} />
          <Route path="execution" element={<RunExecutionPage />} />
          <Route path="runs" element={<RunsListPage />} />
          <Route path="runs/:runId" element={<RunDetailsPage />} />
          <Route path="repairs" element={<DiagnosisPage />} />
          <Route path="comparison" element={<ComparisonPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
