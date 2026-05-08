import { useState, useEffect, useRef } from 'react'
import {
  Play,
  Pause,
  Square,
  Camera,
  AlertCircle,
  CheckCircle,
  Clock,
  Target,
  Activity,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const LiveMonitoring = () => {
  const [isMonitoring, setIsMonitoring] = useState(false)
  const [currentDecision, setCurrentDecision] = useState(null)
  const [ballTracking, setBallTracking] = useState([])
  const [matchState, setMatchState] = useState({
    over: 5,
    ball: 3,
    legalDeliveries: 3,
  })
  const [cameraFeeds, setCameraFeeds] = useState([
    { id: 'cam1', name: 'Bowler End', status: 'active', fps: 30 },
    { id: 'cam2', name: 'Batsman End', status: 'active', fps: 30 },
    { id: 'cam3', name: 'Side View', status: 'active', fps: 29 },
    { id: 'cam4', name: 'Wide Angle', status: 'active', fps: 30 },
  ])

  const videoRef = useRef(null)

  const handleStartMonitoring = () => {
    setIsMonitoring(true)
    // Simulate decision after 3 seconds
    setTimeout(() => {
      simulateDecision()
    }, 3000)
  }

  const handleStopMonitoring = () => {
    setIsMonitoring(false)
    setCurrentDecision(null)
  }

  const simulateDecision = () => {
    const decisions = [
      {
        type: 'OUT',
        subType: 'Bowled',
        confidence: 98.5,
        requiresReview: false,
        color: 'red',
        detections: {
          ball: 'Detected',
          stumps: 'Detected',
          bails: 'Dislodged',
          batsman: 'Detected',
        },
      },
      {
        type: 'LEGAL_DELIVERY',
        subType: 'Fair Delivery',
        confidence: 96.2,
        requiresReview: false,
        color: 'green',
        detections: {
          ball: 'Detected',
          bowler: 'Behind crease',
          trajectory: 'Within guidelines',
        },
      },
      {
        type: 'WIDE',
        subType: 'Wide Ball',
        confidence: 93.8,
        requiresReview: false,
        color: 'yellow',
        detections: {
          ball: 'Detected',
          trajectory: 'Outside guideline',
          batsman: 'No contact',
        },
      },
      {
        type: 'OUT',
        subType: 'LBW',
        confidence: 76.4,
        requiresReview: true,
        color: 'orange',
        detections: {
          ball: 'Detected',
          pad: 'Contact detected',
          trajectory: 'Hitting stumps',
          pitching: 'In line',
        },
      },
    ]

    const randomDecision = decisions[Math.floor(Math.random() * decisions.length)]
    setCurrentDecision(randomDecision)

    // Simulate ball tracking
    const tracking = []
    for (let i = 0; i < 20; i++) {
      tracking.push({
        x: i * 5,
        y: 50 + Math.sin(i * 0.3) * 20,
        z: i * 3,
      })
    }
    setBallTracking(tracking)

    // Update match state
    setMatchState((prev) => ({
      ...prev,
      ball: prev.ball + 1,
      legalDeliveries:
        randomDecision.type === 'LEGAL_DELIVERY' || randomDecision.type === 'OUT'
          ? prev.legalDeliveries + 1
          : prev.legalDeliveries,
    }))

    // Clear decision after 5 seconds and simulate next
    setTimeout(() => {
      setCurrentDecision(null)
      if (isMonitoring) {
        setTimeout(simulateDecision, 2000)
      }
    }, 5000)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Live Monitoring</h1>
          <p className="text-gray-600 mt-1">
            Real-time umpiring decisions and ball tracking
          </p>
        </div>

        <div className="flex items-center space-x-4">
          {!isMonitoring ? (
            <button
              onClick={handleStartMonitoring}
              className="btn-primary flex items-center space-x-2"
            >
              <Play size={20} />
              <span>Start Monitoring</span>
            </button>
          ) : (
            <button
              onClick={handleStopMonitoring}
              className="btn-danger flex items-center space-x-2"
            >
              <Square size={20} />
              <span>Stop Monitoring</span>
            </button>
          )}
        </div>
      </div>

      {/* Match State */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-8">
            <div>
              <p className="text-sm text-gray-600">Over</p>
              <p className="text-2xl font-bold text-gray-900">
                {matchState.over}.{matchState.ball}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Legal Deliveries</p>
              <p className="text-2xl font-bold text-gray-900">
                {matchState.legalDeliveries}/6
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Status</p>
              <div className="flex items-center space-x-2 mt-1">
                {isMonitoring ? (
                  <>
                    <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />
                    <span className="text-sm font-semibold text-green-600">
                      Monitoring
                    </span>
                  </>
                ) : (
                  <>
                    <div className="w-3 h-3 bg-gray-400 rounded-full" />
                    <span className="text-sm font-semibold text-gray-600">
                      Stopped
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          {isMonitoring && (
            <div className="flex items-center space-x-2 text-blue-600">
              <Activity className="animate-pulse" size={20} />
              <span className="text-sm font-medium">Processing...</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Video Feed */}
        <div className="lg:col-span-2 space-y-6">
          {/* Primary Feed */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">
                Primary Camera Feed
              </h2>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                <span className="text-sm font-medium text-gray-600">LIVE</span>
              </div>
            </div>

            <div className="relative bg-cricket-green rounded-lg overflow-hidden aspect-video">
              {/* Simulated Cricket Field */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <Camera className="mx-auto text-white/50" size={64} />
                  <p className="text-white/70 mt-4">
                    {isMonitoring
                      ? 'Camera feed active'
                      : 'Start monitoring to view feed'}
                  </p>
                </div>
              </div>

              {/* Ball Tracking Overlay */}
              {ballTracking.length > 0 && (
                <svg className="absolute inset-0 w-full h-full pointer-events-none">
                  <motion.path
                    d={`M ${ballTracking.map((p) => `${p.x * 10},${p.y * 3}`).join(' L ')}`}
                    stroke="#DC143C"
                    strokeWidth="3"
                    fill="none"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 1 }}
                  />
                  {ballTracking.map((point, i) => (
                    <motion.circle
                      key={i}
                      cx={point.x * 10}
                      cy={point.y * 3}
                      r="4"
                      fill="#DC143C"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: i * 0.05 }}
                    />
                  ))}
                </svg>
              )}

              {/* Decision Overlay */}
              <AnimatePresence>
                {currentDecision && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    className="absolute inset-0 flex items-center justify-center bg-black/50"
                  >
                    <div className="text-center">
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: 'spring', stiffness: 200 }}
                        className={`inline-block px-8 py-4 rounded-lg bg-${currentDecision.color}-600 text-white`}
                      >
                        <p className="text-5xl font-bold">{currentDecision.type}</p>
                        <p className="text-xl mt-2">{currentDecision.subType}</p>
                        <p className="text-sm mt-2 opacity-90">
                          Confidence: {currentDecision.confidence}%
                        </p>
                      </motion.div>
                      {currentDecision.requiresReview && (
                        <motion.div
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.3 }}
                          className="mt-4 px-4 py-2 bg-yellow-500 text-white rounded-lg inline-flex items-center space-x-2"
                        >
                          <AlertCircle size={20} />
                          <span className="font-semibold">Review Recommended</span>
                        </motion.div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Multi-Camera Grid */}
          <div className="card">
            <h2 className="text-lg font-bold text-gray-900 mb-4">
              Camera Feeds
            </h2>
            <div className="grid grid-cols-2 gap-4">
              {cameraFeeds.map((camera) => (
                <div
                  key={camera.id}
                  className="relative bg-gray-800 rounded-lg overflow-hidden aspect-video"
                >
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Camera className="text-white/30" size={32} />
                  </div>
                  <div className="absolute top-2 left-2 right-2 flex items-center justify-between">
                    <span className="text-xs font-medium text-white bg-black/50 px-2 py-1 rounded">
                      {camera.name}
                    </span>
                    <div className="flex items-center space-x-1 bg-black/50 px-2 py-1 rounded">
                      <div className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                      <span className="text-xs text-white">{camera.fps} FPS</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Decision Details */}
        <div className="space-y-6">
          {/* Current Decision */}
          <div className="card">
            <h2 className="text-lg font-bold text-gray-900 mb-4">
              Current Decision
            </h2>

            {currentDecision ? (
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-600">
                      Decision Type
                    </span>
                    <span
                      className={`px-3 py-1 rounded-full text-sm font-semibold bg-${currentDecision.color}-100 text-${currentDecision.color}-800`}
                    >
                      {currentDecision.type}
                    </span>
                  </div>
                  <p className="text-lg font-bold text-gray-900">
                    {currentDecision.subType}
                  </p>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-600">
                      Confidence Score
                    </span>
                    <span className="text-sm font-bold text-gray-900">
                      {currentDecision.confidence}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`bg-${currentDecision.color}-500 h-2 rounded-full transition-all duration-500`}
                      style={{ width: `${currentDecision.confidence}%` }}
                    />
                  </div>
                </div>

                <div>
                  <p className="text-sm font-medium text-gray-600 mb-2">
                    Detections
                  </p>
                  <div className="space-y-2">
                    {Object.entries(currentDecision.detections).map(
                      ([key, value]) => (
                        <div
                          key={key}
                          className="flex items-center justify-between text-sm"
                        >
                          <span className="text-gray-700 capitalize">{key}</span>
                          <span className="font-medium text-gray-900">
                            {value}
                          </span>
                        </div>
                      )
                    )}
                  </div>
                </div>

                {currentDecision.requiresReview && (
                  <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <div className="flex items-start space-x-2">
                      <AlertCircle className="text-yellow-600 flex-shrink-0 mt-0.5" size={16} />
                      <div>
                        <p className="text-sm font-medium text-yellow-800">
                          Review Recommended
                        </p>
                        <p className="text-xs text-yellow-700 mt-1">
                          Confidence below threshold. Manual review suggested.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <Target className="mx-auto text-gray-300" size={48} />
                <p className="text-gray-500 mt-4">
                  {isMonitoring
                    ? 'Waiting for next delivery...'
                    : 'No active decision'}
                </p>
              </div>
            )}
          </div>

          {/* Performance Metrics */}
          <div className="card">
            <h2 className="text-lg font-bold text-gray-900 mb-4">
              Performance
            </h2>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Processing Time</span>
                <span className="text-sm font-bold text-gray-900">0.82s</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Detection FPS</span>
                <span className="text-sm font-bold text-gray-900">30 FPS</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Tracking Quality</span>
                <span className="text-sm font-bold text-green-600">Excellent</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Sync Quality</span>
                <span className="text-sm font-bold text-green-600">98.5%</span>
              </div>
            </div>
          </div>

          {/* Camera Status */}
          <div className="card">
            <h2 className="text-lg font-bold text-gray-900 mb-4">
              Camera Status
            </h2>

            <div className="space-y-3">
              {cameraFeeds.map((camera) => (
                <div
                  key={camera.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full" />
                    <span className="text-sm font-medium text-gray-900">
                      {camera.name}
                    </span>
                  </div>
                  <span className="text-xs text-gray-600">{camera.fps} FPS</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LiveMonitoring
