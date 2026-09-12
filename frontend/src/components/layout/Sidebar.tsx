import { useLocation, Link } from 'react-router-dom';

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/scanner', label: 'Swing Scanner', icon: '🔍' },
  { path: '/calculator', label: 'Position Sizer', icon: '🧮' },
  { path: '/portfolio', label: 'Portfolio', icon: '💼' },
  { path: '/journal', label: 'Trade Journal', icon: '📒' },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-navy-900/80 backdrop-blur-lg border-r border-navy-700/50 z-50 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-navy-700/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-electric-500 to-emerald-500 flex items-center justify-center text-xl font-bold text-white shadow-lg shadow-electric-500/30">
            T
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-tight">TradeLab</h1>
            <p className="text-[10px] text-gray-500 uppercase tracking-widest">NSE • BSE</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
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
  );
}
