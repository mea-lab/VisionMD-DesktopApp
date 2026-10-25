import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../../contexts/ThemeContext';

const shortcuts = [
  ['Ctrl+N', 'New Project'], ['Ctrl+B', 'Go Back'],
  ['Ctrl+F', 'Go Forward'], ['Ctrl+P', 'Process Video'],
  ['Ctrl+U', 'Auto-Process'], ['Ctrl+H', 'Home'],
  ['Ctrl+A', 'Analyze current task'], ['Ctrl+L', 'Analyze All'],
];

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const quit = () => window.close();

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <h2 className="text-xl font-semibold">Settings</h2>
      <section className="rounded-lg border border-zinc-600 bg-zinc-700 p-4">
        <h3 className="mb-3 font-medium">Appearance</h3>
        <div className="inline-flex rounded-lg border border-zinc-500 p-1" role="group" aria-label="Color theme">
          <button type="button" onClick={() => setTheme('light')} aria-pressed={theme === 'light'}
            className={`flex items-center gap-2 rounded-md px-4 py-2 ${theme === 'light' ? 'bg-blue-600 text-white' : 'hover:bg-zinc-600'}`}>
            <Sun size={18} /> Light
          </button>
          <button type="button" onClick={() => setTheme('dark')} aria-pressed={theme === 'dark'}
            className={`flex items-center gap-2 rounded-md px-4 py-2 ${theme === 'dark' ? 'bg-blue-600 text-white' : 'hover:bg-zinc-600'}`}>
            <Moon size={18} /> Dark
          </button>
        </div>
        <p className="mt-2 text-sm text-gray-400">Your preference is saved on this computer.</p>
      </section>
      <section className="rounded-lg border border-zinc-600 bg-zinc-700 p-4">
        <h3 className="mb-3 font-medium">Keyboard shortcuts</h3>
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
          {shortcuts.map(([keys, label]) => <div className="contents" key={keys}>
            <dt><kbd className="rounded border border-zinc-500 bg-zinc-800 px-2 py-1 font-mono">{keys}</kbd></dt>
            <dd className="self-center">{label}</dd>
          </div>)}
        </dl>
      </section>
      <button onClick={quit} className="w-fit rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700">
        Quit VisionMD
      </button>
    </div>
  );
}
