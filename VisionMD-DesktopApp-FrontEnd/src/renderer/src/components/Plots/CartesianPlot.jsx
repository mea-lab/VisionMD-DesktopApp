import { forwardRef, useEffect, useState } from 'react';
import createPlotlyComponent from 'react-plotly.js/factory';
import plotlyBasicUrl from 'plotly.js/dist/plotly-basic.min.js?url';

let cachedComponent;
let plotlyLoadPromise;

const loadPlotly = () => {
  if (cachedComponent) return Promise.resolve(cachedComponent);
  if (plotlyLoadPromise) return plotlyLoadPromise;

  plotlyLoadPromise = new Promise((resolve, reject) => {
    const finish = () => {
      if (!window.Plotly) {
        reject(new Error('Plotly loaded without exposing its browser API.'));
        return;
      }
      cachedComponent = createPlotlyComponent(window.Plotly);
      resolve(cachedComponent);
    };

    if (window.Plotly) {
      finish();
      return;
    }

    const script = document.createElement('script');
    script.src = plotlyBasicUrl;
    script.async = true;
    script.dataset.visionmdPlotly = 'basic';
    script.onload = finish;
    script.onerror = () => reject(new Error('Could not load the chart library.'));
    document.head.appendChild(script);
  });

  return plotlyLoadPromise;
};

const CartesianPlot = forwardRef((props, ref) => {
  const [PlotComponent, setPlotComponent] = useState(() => cachedComponent);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    let active = true;
    loadPlotly()
      .then((component) => {
        if (active) setPlotComponent(() => component);
      })
      .catch((error) => {
        if (active) setLoadError(error.message);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loadError) {
    return <div role="alert" className="p-4 text-red-300">{loadError}</div>;
  }
  if (!PlotComponent) {
    return <div aria-busy="true" style={props.style} className="p-4">Loading chart…</div>;
  }
  return <PlotComponent {...props} ref={ref} />;
});

CartesianPlot.displayName = 'CartesianPlot';

export default CartesianPlot;
