import { useState, useEffect } from 'react'
import { 
  Activity, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  TrendingUp,
  Clock,
  Camera,
  Zap
} from 'lucide-react'
import { motion } from 'framer-motion'

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalDecisions: 0,
    correctDecisions: 0,
    reviewedDecisions: 0,
    accuracy: 0,
    avgLatency: 0,
    fps: 0,
    activeCameras: 0,
  })

  const [recentDecisions, setRecentDecisions] = useState([])

  useEffect(() => {
    // Simulate fetching data
    setStats({
      totalDecisions: 247,
      correctDecisions: 235,
      reviewedDecisions: 12,
      accuracy: 95.1,
      avgLatency: 0.8,
      fps: 30,
      activeCameras: 4,
    })

    setRecentDecisions([
      {
        id: 1,
        type: 'OUT',
        subType: 'Bowled',
        confidence: 98.5,
        timestamp: '2 mins ago',
        requiresReview: false,
      },
      {
        id: 2,
        type: 'WIDE',
        subType: 'Wide Ball',
        confidence: 92.3,
        timestamp: '5 mins ago',
        requiresReview: false,
      },
      {
        id: 3,
        type: 'OUT',
        subType: 'LBW',
        confidence: 78.2,
        timestamp: '8 mins ago',
        requiresReview: true,
      },
      {
        id: 4,
        type: 'NO_BALL',
        subType: 'Front Foot',
        confidence: 95.7,
        timestamp: '12 mins ago',
        requiresReview: false,
      },
    ])
  }, [])

  const statCards = [
    {
      title: 'Total Decisions',
      value: stats.totalDecisions,
      icon: Activity,
      color: 'blue',
      change: '+12 today',
    },
    {
      title: 'Accuracy',
      value: `${stats.accuracy}%`,
      icon: CheckCircle,
      color: 'green',
      change: '+2.3% vs last match',
    },
    {
      title: 'Avg Latency',
      value: `${stats.avgLatency}s`,
      icon: Clock,
      color: 'purple',
      change: 'Within target',
    },
    {
      title: 'Active Cameras',
      value: stats.activeCameras,
      icon: Camera,
      color: 'orange',
      change: 'All operational',
    },
  ]

  const getDecisionColor = (type) => {
    switch (type) {
      case 'OUT':
        return 'bg-red-100 text-red-800'
      case 'WIDE':
        return 'bg-yellow-100 text-yellow-800'
      case 'NO_BALL':
        return 'bg-orange-100 text-orange-800'
      default:
        return 'bg-green-100 text-green-800'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-1">
          Real-time overview of the AI umpiring system
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => {
          const Icon = stat.icon
          return (
            <motion.div
              key={stat.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="card hover:shadow-lg transition-shadow"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">
                    {stat.title}
                  </p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">
                    {stat.value}
                  </p>
                  <p className="text-xs text-gray-500 mt-2">{stat.change}</p>
                </div>
                <div
                  className={`w-12 h-12 rounded-lg bg-${stat.color}-100 flex items-center justify-center`}
                >
                  <Icon className={`text-${stat.color}-600`} size={24} />
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Decisions */}
        <div className="lg:col-span-2 card">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">
              Recent Decisions
            </h2>
            <button className="text-sm text-cricket-primary hover:text-blue-800 font-medium">
              View All
            </button>
          </div>

          <div className="space-y-4">
            {recentDecisions.map((decision) => (
              <motion.div
                key={decision.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center space-x-4">
                  <div
                    className={`px-3 py-1 rounded-full text-sm font-semibold ${getDecisionColor(
                      decision.type
                    )}`}
                  >
                    {decision.type}
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">
                      {decision.subType}
                    </p>
                    <p className="text-sm text-gray-500">
                      {decision.timestamp}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">
                      {decision.confidence}%
                    </p>
                    <p className="text-xs text-gray-500">Confidence</p>
                  </div>
                  {decision.requiresReview && (
                    <div className="flex items-center space-x-1 text-yellow-600">
                      <AlertTriangle size={16} />
                      <span className="text-xs font-medium">Review</span>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* System Health */}
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-6">
            System Health
          </h2>

          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">
                  Frame Rate
                </span>
                <span className="text-sm font-bold text-green-600">
                  {stats.fps} FPS
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-green-500 h-2 rounded-full"
                  style={{ width: `${(stats.fps / 30) * 100}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">
                  CPU Usage
                </span>
                <span className="text-sm font-bold text-blue-600">45%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full"
                  style={{ width: '45%' }}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">
                  Memory Usage
                </span>
                <span className="text-sm font-bold text-purple-600">
                  6.2 GB
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-purple-500 h-2 rounded-full"
                  style={{ width: '62%' }}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">
                  GPU Usage
                </span>
                <span className="text-sm font-bold text-orange-600">78%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-orange-500 h-2 rounded-full"
                  style={{ width: '78%' }}
                />
              </div>
            </div>
          </div>

          <div className="mt-6 p-4 bg-green-50 rounded-lg">
            <div className="flex items-center space-x-2">
              <CheckCircle className="text-green-600" size={20} />
              <span className="text-sm font-medium text-green-800">
                All systems operational
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <button className="btn-primary flex items-center justify-center space-x-2">
            <Activity size={20} />
            <span>Start Monitoring</span>
          </button>
          <button className="btn-secondary flex items-center justify-center space-x-2">
            <Camera size={20} />
            <span>Calibrate Cameras</span>
          </button>
          <button className="bg-purple-600 hover:bg-purple-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center space-x-2">
            <TrendingUp size={20} />
            <span>View Analytics</span>
          </button>
          <button className="bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center space-x-2">
            <Zap size={20} />
            <span>Run Diagnostics</span>
          </button>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
