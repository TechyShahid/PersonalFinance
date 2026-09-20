import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import Dashboard from './pages/Dashboard';
import Scanner from './pages/Scanner';
import Calculator from './pages/Calculator';
import Portfolio from './pages/Portfolio';
import Journal from './pages/Journal';
import NewListingsTracker from './pages/NewListingsTracker';

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-navy-950">
        <Sidebar />
        <main className="flex-1 w-full max-w-full md:ml-64 pt-20 md:pt-8 p-3 sm:p-5 md:p-8 overflow-x-hidden min-h-screen">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/new-listings" element={<NewListingsTracker />} />
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

