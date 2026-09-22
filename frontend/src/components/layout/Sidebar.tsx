import { useState } from 'react';
import { useLocation, Link } from 'react-router-dom';

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/new-listings', label: 'New Listings Tracker', icon: '🚀' },
  { path: '/scanner', label: 'Swing Scanner', icon: '🔍' },
  { path: '/paper-trading', label: 'Paper Trading', icon: '📈' },
  { path: '/calculator', label: 'Position Sizer', icon: '🧮' },
  { path: '/portfolio', label: 'Portfolio', icon: '💼' },
  { path: '/journal', label: 'Trade Journal', icon: '📒' },
];


export default function Sidebar() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile Top Header */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-16 bg-navy-900/90 backdrop-blur-lg border-b border-navy-700/50 z-40 px-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-electric-500 to-emerald-500 flex items-center justify-center text-sm font-bold text-white shadow-md shadow-electric-500/30">
            T
          </div>
          <div>
            <span className="text-base font-bold text-white tracking-tight">TradeLab</span>
            <span className="ml-2 text-[10px] text-gray-400 uppercase tracking-wider">NSE • BSE</span>
          </div>
        </div>

        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 rounded-xl bg-navy-800 border border-navy-700 text-gray-200 hover:text-white focus:outline-none"
          aria-label="Toggle navigation menu"
        >
          {mobileOpen ? (
            <span className="text-lg font-bold">✕</span>
          ) : (
            <span className="text-lg">☰</span>
          )}
        </button>
      </div>

      {/* Mobile Backdrop Overlay */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          className="md:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity"
        />
      )}

      {/* Sidebar Drawer (Fixed on desktop, slide-out on mobile) */}
      <aside
        className={`fixed top-0 bottom-0 left-0 w-64 bg-navy-900/95 md:bg-navy-900/80 backdrop-blur-lg border-r border-navy-700/50 z-50 flex flex-col transition-transform duration-300 ease-in-out ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        {/* Logo */}
        <div className="p-6 border-b border-navy-700/50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-electric-500 to-emerald-500 flex items-center justify-center text-xl font-bold text-white shadow-lg shadow-electric-500/30">
              T
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-tight">TradeLab</h1>
              <p className="text-[10px] text-gray-500 uppercase tracking-widest">NSE • BSE</p>
            </div>
          </div>
          {/* Close button inside drawer on mobile */}
          <button
            onClick={() => setMobileOpen(false)}
            className="md:hidden p-1.5 rounded-lg text-gray-400 hover:text-white bg-navy-800"
          >
            ✕
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                className={isActive ? 'nav-item-active' : 'nav-item'}
              >
                <span className="text-lg">{item.icon}</span>
                <span className="text-sm">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Market Status */}
        <div className="p-4 border-t border-navy-700/50">
          <div className="glass-card p-3">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-coral-400 animate-pulse-slow" />
              <span className="text-xs text-gray-400">Market Closed</span>
            </div>
            <p className="text-[11px] text-gray-500">
              Next session: Mon 9:15 AM IST
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}

