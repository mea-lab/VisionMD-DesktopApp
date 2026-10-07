import { useRef, useState } from 'react';
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from 'recharts';
import CloudDownload from '@mui/icons-material/CloudDownload';
import Button from '@mui/material/Button';

const ScatterPlot = ({ tasks, selectedTaskIndex, fileName }) => {
  const currentTask = tasks[selectedTaskIndex];
  const { radarTable } = currentTask.data;
  const currentTaskName = currentTask.name;

  const [tableView, setTableView] = useState(true);
  const radarRef = useRef(null);
  const radarData = Object.entries(radarTable).map(([feature, value]) => ({
    feature,
    value: Number.isFinite(Number(value)) ? Number(value) : 0,
  }));
  const downloadBaseName = fileName
    ? fileName.replace(/\.[^/.]+$/, '')
    : currentTaskName;

  const showTable = () => setTableView(true);
  const showPlot = () => setTableView(false);

  const downloadCSV = () => {
    let csv = 'data:text/csv;charset=utf-8,Feature,Value\r\n';
    Object.entries(radarTable).forEach(([feat, val]) => {
      csv += `${feat},${typeof val === 'number' ? val.toFixed(6) : val}\r\n`;
    });
    const encoded = encodeURI(csv);
    const a = document.createElement('a');
    a.href = encoded;
    a.download = `${(fileName ? fileName.replace(/\.[^/.]+$/, '') : currentTaskName)}_${currentTaskName}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const downloadRadar = () => {
    const svg = radarRef.current?.querySelector('svg');
    if (!svg) return;
    const copy = svg.cloneNode(true);
    copy.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    const blob = new Blob([new XMLSerializer().serializeToString(copy)], {
      type: 'image/svg+xml;charset=utf-8',
    });
    const href = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = href;
    link.download = `${downloadBaseName}_radarPlot.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.setTimeout(() => URL.revokeObjectURL(href), 0);
  };

  return (
    <div style={{ position: 'relative' }}>
      <div className="flex p-4 space-x-2">
        <button
          className={`px-4 py-2 text-sm font-semibold rounded-md ${tableView ? 'bg-[#1976d2] hover:bg-[#1565c0] text-white' : 'bg-gray-200 text-gray-800'}`}
          onClick={showTable}
        >
          Table
        </button>
        <button
          className={`px-4 py-2 text-sm font-semibold rounded-md ${!tableView ? 'bg-[#1976d2] hover:bg-[#1565c0] text-white' : 'bg-gray-200 text-gray-800'}`}
          onClick={showPlot}
        >
          Scatter Plot
        </button>
      </div>

      {tableView ? (
        <div className="p-6">
          <div className="overflow-x-auto bg-[#333338] rounded-lg shadow-lg">
            <table className="min-w-full divide-y divide-zinc-200">
              <thead className="">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-100 uppercase tracking-wider">
                    Feature
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-100 uppercase tracking-wider">
                    Value
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-600">
                {Object.entries(radarTable).map(([feat, val]) => (
                  <tr key={feat}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-200">
                      {feat}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                      {typeof val === 'number' ? val.toFixed(4) : val}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex justify-center">
            <Button
              variant="contained"
              onClick={downloadCSV}
              startIcon={<CloudDownload />}
              sx={{
                textTransform: 'none',
                fontWeight: 'bold',
                px: 3,
                py: 1,
              }}
            >
              Download CSV
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center">
          <div ref={radarRef} className="h-[600px] w-full max-w-[700px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData} outerRadius="75%">
                <PolarGrid stroke="#71717a" />
                <PolarAngleAxis
                  dataKey="feature"
                  tick={{ fill: '#f3f4f6', fontSize: 11 }}
                />
                <PolarRadiusAxis
                  domain={[0, 'auto']}
                  tick={{ fill: '#d4d4d8', fontSize: 10 }}
                />
                <Radar
                  name={currentTaskName}
                  dataKey="value"
                  stroke="#1976d2"
                  fill="#1976d2"
                  fillOpacity={0.45}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <Button
            variant="contained"
            onClick={downloadRadar}
            startIcon={<CloudDownload />}
            sx={{ mb: 2, textTransform: 'none', fontWeight: 'bold' }}
          >
            Download plot
          </Button>
        </div>
      )}
    </div>
  );
};

export default ScatterPlot;
