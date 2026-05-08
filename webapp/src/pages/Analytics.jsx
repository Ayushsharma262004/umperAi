import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const Analytics = () => {
  const decisionTypeData = [
    { name: 'Legal Delivery', value: 180, color: '#059669' },
    { name: 'Wide', value: 35, color: '#EAB308' },
    { name: 'No Ball', value: 18, color: '#F97316' },
    { name: 'Bowled', value: 8, color: '#DC2626' },
    { name: 'LBW', value: 4, color: '#DC2626' },
    { name: 'Caught', value: 2, color: '#DC2626' },
  ]

  const confidenceData = [
    { range: '90-100%', count: 215 },
    { range: '80-90%', count: 25 },
    { range: '70-80%', count: 7 },
    { range: '<70%', count: 0 },
  ]

  const performanceData = [
    { time: '10:00', fps: 30, latency: 0.8, accuracy: 95 },
    { time: '11:00', fps: 29, latency: 0.9, accuracy: 94 },
    { time: '12:00', fps: 30, latency: 0.7, accuracy: 96 },
    { time: '13:00', fps: 30, latency: 0.8, accuracy: 95 },
    { time: '14:00', fps: 28, latency: 1.0, accuracy: 93 },
    { time: '15:00', fps: 30, latency: 0.8, accuracy: 95 },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
        <p className="text-gray-600 mt-1">
          Detailed insights and performance metrics
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="card">
          <p className="text-sm font-medium text-gray-600">Total Decisions</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">247</p>
          <p className="text-xs text-green-600 mt-2">+12% from last match</p>
        </div>
        <div className="card">
          <p className="text-sm font-medium text-gray-600">Avg Confidence</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">94.2%</p>
          <p className="text-xs text-green-600 mt-2">+1.5% improvement</p>
        </div>
        <div className="card">
          <p className="text-sm font-medium text-gray-600">Review Rate</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">4.9%</p>
          <p className="text-xs text-green-600 mt-2">-2.1% reduction</p>
        </div>
        <div className="card">
          <p className="text-sm font-medium text-gray-600">Accuracy</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">95.1%</p>
          <p className="text-xs text-green-600 mt-2">Above target</p>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Decision Types */}
        <div className="card">
          <h2 className="text-lg font-bold text-gray-900 mb-4">
            Decision Distribution
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={decisionTypeData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) =>
                  `${name}: ${(percent * 100).toFixed(0)}%`
                }
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {decisionTypeData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Confidence Distribution */}
        <div className="card">
          <h2 className="text-lg font-bold text-gray-900 mb-4">
            Confidence Distribution
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={confidenceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="range" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#1E3A8A" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Performance Over Time */}
        <div className="card lg:col-span-2">
          <h2 className="text-lg font-bold text-gray-900 mb-4">
            Performance Metrics Over Time
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={performanceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="fps"
                stroke="#059669"
                name="FPS"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="latency"
                stroke="#F97316"
                name="Latency (s)"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="accuracy"
                stroke="#1E3A8A"
                name="Accuracy (%)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Detailed Stats */}
      <div className="card">
        <h2 className="text-lg font-bold text-gray-900 mb-4">
          Detailed Statistics
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">
              Decision Accuracy
            </h3>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Bowled</span>
                <span className="font-medium">98.5%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">LBW</span>
                <span className="font-medium">89.2%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Caught</span>
                <span className="font-medium">92.8%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Wide</span>
                <span className="font-medium">96.3%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">No Ball</span>
                <span className="font-medium">97.1%</span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">
              System Performance
            </h3>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Avg FPS</span>
                <span className="font-medium">29.5</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Avg Latency</span>
                <span className="font-medium">0.83s</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">CPU Usage</span>
                <span className="font-medium">45%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Memory Usage</span>
                <span className="font-medium">6.2 GB</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">GPU Usage</span>
                <span className="font-medium">78%</span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">
              Camera Statistics
            </h3>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Active Cameras</span>
                <span className="font-medium">4/4</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Sync Quality</span>
                <span className="font-medium">98.5%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Dropped Frames</span>
                <span className="font-medium">12</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Avg Detection Time</span>
                <span className="font-medium">0.45s</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Tracking Quality</span>
                <span className="font-medium">Excellent</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Analytics
