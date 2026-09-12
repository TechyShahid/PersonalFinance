import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import Dashboard from './pages/Dashboard';
import Scanner from './pages/Scanner';
import Calculator from './pages/Calculator';
import Portfolio from './pages/Portfolio';
import Journal from './pages/Journal';

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 ml-64 p-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/scanner" element={<Scanner />} />
            <Route path="/calculator" element={<Calculator />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/journal" element={<Journal />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
