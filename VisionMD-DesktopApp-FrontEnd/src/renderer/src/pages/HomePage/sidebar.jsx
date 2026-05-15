// src/pages/HomePage/sidebar.jsx
import { Folder, HelpCircle, Settings as Cog } from 'lucide-react';
import clsx from 'clsx';

const buttons = [
  { id: 'projects', Icon: Folder, label: 'Projects' },
  { id: 'info', Icon: HelpCircle, label: 'Info' },
  { id: 'settings', Icon: Cog, label: 'Settings' },
];

export default function Sidebar({ view, setView }) {
  return (
    <nav className="w-16 flex flex-col items-center bg-zinc-900">
      <div className="mt-auto mb-4 flex flex-col gap-4">
        {buttons.map(({ id, Icon, label }) => (
          <button
            key={id}
            aria-label={label}
            onClick={() => setView(id)}
            className={clsx(
              'p-2 rounded-lg hover:bg-zinc-700 focus:outline-none focus:ring',
              view === id && 'bg-zinc-700'
            )}
          >
            <Icon size={22} />
          </button>
        ))}
      </div>
    </nav>
  );
}
