import { useState, useMemo, useRef, useEffect } from 'react';
import CloudDownload from '@mui/icons-material/CloudDownload';
import ArrowDropDown from '@mui/icons-material/ArrowDropDown';


const FeatureTable = ({ tasks, selectedTaskIndex, fileName, includeUnavailable = false, featureOrder = [], featureSections = [] }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef();

  const task = tasks[selectedTaskIndex] || {};
  const sections = featureSections.length && task.data
    ? featureSections.map(section => ({ ...section, entries: section.features.map(feature => {
        const key = typeof feature === 'string' ? feature : feature.key;
        return { key, label: typeof feature === 'string' ? feature : feature.label, value: task.data[key] ?? null };
      }) }))
    : [{ entries: featureOrder.length && task.data
        ? featureOrder.map(key => ({ key, label: key, value: task.data[key] ?? null }))
        : Object.entries(task.data || {}).filter(([, v]) => typeof v === 'number' || typeof v === 'string' || (includeUnavailable && v === null)).map(([key, value]) => ({ key, label: key, value })) }];
  const entries = sections.flatMap(section => section.entries);
  const header = useMemo(() => entries.map(entry => entry.label), [entries]);
  const keys = entries.map(entry => entry.key);

  const btn = `bg-[#1976d2] hover:bg-[#1565c0] text-white font-medium px-3 py-1 rounded-md inline-flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed`;

  const hasData = !!task.data;
  const hasGroup = tasks.some(t => t.name === task.name && t.data);
  
  const safe = s => s.toLowerCase().replace(/[^a-z0-9]+/g, '_');
  const csvRow = arr => {
    return (
      arr.map(v =>
        v == null ? '' : typeof v === 'string' && /[",\r\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v
      ).join(',')
    )
  };

  const blob = (txt, name) => {
    const url = URL.createObjectURL(
      new Blob([txt], { type: 'text/csv;charset=utf-8;' })
    );
    Object.assign(document.createElement('a'), { href: url, download: name }).click();
    URL.revokeObjectURL(url);
  };

  const csvHeader = featureSections.length ? ["Video name", ...header] : header;
  const csvValues = t => {
    const values = keys.map(key => t.data[key] ?? '');
    return featureSections.length ? [t.data['File name'] || fileName, ...values] : values;
  };

  const csvCurrent = () => {
    if (!task.data) return;
    blob(
      [csvRow(csvHeader), csvRow(csvValues(task))].join('\n'),
      `${safe(fileName)}_${safe(task.name)}.csv`
    );
  };

  const csvAll = () => {
    const group = tasks.filter(t => t.name === task.name && t.data);
    if (!group.length) return;
    const rows = group.map(t => csvRow(csvValues(t)));
    const avg = keys.map(h => {
      const lower = h.toLowerCase();
      if (lower === 'task name') return `average_${fileName.split('.')[0]}`;
      if (lower === 'file name') return fileName;
      const nums = group.map(t => t.data[h]).filter(v => typeof v === 'number');
      return nums.length ? (nums.reduce((a, b) => a + b, 0) / nums.length).toFixed(4) : '';
    });
    rows.push(csvRow(featureSections.length ? [`Average (${fileName})`, ...avg] : avg));
    blob(
      [csvRow(csvHeader), ...rows].join('\n'),
      `${safe(fileName)}_${safe(task.name)}_all.csv`
    );
  };

  useEffect(() => {
    const h = e => !ref.current?.contains(e.target) && setOpen(false);
    open && document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);

  return (
    <div>
      {sections.map((section, index) => (
        <section key={section.title || index}>
          {section.title && <h2 className="mx-4 mt-5 text-lg font-semibold text-gray-100">{section.title}</h2>}
          {section.description && <p className="mx-4 mt-1 text-sm text-gray-300">{section.description}</p>}
          <div className="overflow-x-auto m-4 rounded-lg border-2 border-zinc-500 bg-[#333338]">
            <table className="min-w-full divide-y divide-zinc-400">
              <thead><tr>
                <th className="px-6 py-3 text-left font-normal text-gray-100">Feature</th>
                <th className="px-6 py-3 text-left font-normal text-gray-100">Value</th>
              </tr></thead>
              <tbody className="divide-y divide-zinc-600">
                {section.entries.map(({ key, label, value }) => (
                  <tr key={key}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200">{label}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                      {value == null || (typeof value === 'number' && !Number.isFinite(value)) ? 'Unavailable' : typeof value === 'number' ? value.toFixed(4) : value}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}

      <div ref={ref} className="relative flex justify-center mt-4 mb-12">
        <div className="flex">
          <button
            className={`${btn} rounded-r-none border-r border-blue-800`}
            onClick={csvCurrent}
            disabled={!hasData}
          >
            <CloudDownload fontSize="small" /> Download CSV
          </button>
          <button
            className={`${btn} rounded-l-none px-2`}
            onClick={() => setOpen(o => !o)}
            disabled={!hasGroup}
          >
            <ArrowDropDown fontSize="small" />
          </button>
        </div>

        {open && (
          <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 w-40 border border-gray-200 rounded-md z-20">
            <button
              className="w-full text-center rounded-md px-2 py-1 bg-white hover:bg-gray-100"
              onClick={() => {
                csvAll();
                setOpen(false);
              }}
              disabled={!hasGroup}
            >
              Download All
            </button>
          </div>
        )}
      </div>

    </div>
  );
};

export default FeatureTable;
