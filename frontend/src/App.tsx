import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Overview } from './pages/Overview';
import { Tasks } from './pages/Tasks';
import { TaskDetail } from './pages/TaskDetail';
import { Workers } from './pages/Workers';
import { Metrics } from './pages/Metrics';
import { Queue } from './pages/Queue';
import { Simulate } from './pages/Simulate';
import { SSEProvider } from './context/SSEContext';

function App() {
  return (
    <SSEProvider>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="tasks" element={<Tasks />} />
          <Route path="tasks/:id" element={<TaskDetail />} />
          <Route path="workers" element={<Workers />} />
          <Route path="metrics" element={<Metrics />} />
          <Route path="queue" element={<Queue />} />
          <Route path="simulate" element={<Simulate />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
    </SSEProvider>
  );
}

export default App;
