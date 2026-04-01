import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App.jsx'
import StockDetail from './StockDetail.jsx'
import Guide from './Guide.jsx'
import ModelPerformance from './ModelPerformance.jsx'
import Feedback from './Feedback.jsx'
import './index.css'

createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<App />} />
      <Route path="/stock/:ticker" element={<StockDetail />} />
      <Route path="/guide" element={<Guide />} />
      <Route path="/model-performance" element={<ModelPerformance />} />
      <Route path="/feedback" element={<Feedback />} />
    </Routes>
  </BrowserRouter>,
)