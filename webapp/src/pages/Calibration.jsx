import { useState } from 'react'
import { Camera, Target, CheckCircle, AlertCircle, Save } from 'lucide-react'

const Calibration = () => {
  const [calibrationStep, setCalibrationStep] = useState(0)
  const [calibrationData, setCalibrationData] = useState({
    pitchBoundary: false,
    creaseLines: false,
    wideGuidelines: false,
    stumpPositions: false,
    cameraHomography: false,
  })

  const calibrationSteps = [
    {
      title: 'Pitch Boundary',
      description: 'Mark the four corners of the cricket pitch',
      status: calibrationData.pitchBoundary,
    },
    {
      title: 'Crease Lines',
      description: 'Define bowling and batting crease positions',
      status: calibrationData.creaseLines,
    },
    {
      title: 'Wide Guidelines',
      description: 'Set wide ball guideline distances',
      status: calibrationData.wideGuidelines,
    },
    {
      title: 'Stump Positions',
      description: 'Mark the position of all three stumps',
      status: calibrationData.stumpPositions,
    },
    {
      title: 'Camera Homography',
      description: 'Compute camera transformation matrices',
      status: calibrationData.cameraHomography,
    },
  ]

  const handleCompleteStep = (step) => {
    const keys = Object.keys(calibrationData)
    setCalibrationData({
      ...calibrationData,
      [keys[step]]: true,
    })
    if (step < calibrationSteps.length - 1) {
      setCalibrationStep(step + 1)
    }
  }

  const allCalibrated = Object.values(calibrationData).every((v) => v)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Camera Calibration</h1>
        <p className="text-gray-600 mt-1">
          Configure camera positions and field measurements
        </p>
      </div>

      {/* Progress */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">
            Calibration Progress
          </h2>
          <span className="text-sm font-medium text-gray-600">
            {Object.values(calibrationData).filter((v) => v).length} /{' '}
            {calibrationSteps.length} Complete
          </span>
        </div>

        <div className="relative">
          <div className="overflow-hidden h-2 mb-4 text-xs flex rounded-full bg-gray-200">
            <div
              style={{
                width: `${
                  (Object.values(calibrationData).filter((v) => v).length /
                    calibrationSteps.length) *
                  100
                }%`,
              }}
              className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-cricket-secondary transition-all duration-500"
            />
          </div>
        </div>

        {allCalibrated && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg flex items-center space-x-3">
            <CheckCircle className="text-green-600" size={24} />
            <div>
              <p className="font-medium text-green-800">
                Calibration Complete!
              </p>
              <p className="text-sm text-green-700">
                All calibration steps have been completed successfully.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Calibration Steps */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Steps List */}
        <div className="space-y-4">
          {calibrationSteps.map((step, index) => (
            <div
              key={index}
              className={`card cursor-pointer transition-all ${
                calibrationStep === index
                  ? 'ring-2 ring-cricket-primary'
                  : ''
              }`}
              onClick={() => setCalibrationStep(index)}
            >
              <div className="flex items-start space-x-4">
                <div
                  className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
                    step.status
                      ? 'bg-green-100'
                      : calibrationStep === index
                      ? 'bg-blue-100'
                      : 'bg-gray-100'
                  }`}
                >
                  {step.status ? (
                    <CheckCircle className="text-green-600" size={20} />
                  ) : (
                    <span
                      className={`font-bold ${
                        calibrationStep === index
                          ? 'text-blue-600'
                          : 'text-gray-400'
                      }`}
                    >
                      {index + 1}
                    </span>
                  )}
                </div>

                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900">{step.title}</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    {step.description}
                  </p>

                  {calibrationStep === index && !step.status && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleCompleteStep(index)
                      }}
                      className="mt-3 btn-primary text-sm"
                    >
                      Complete Step
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Calibration Canvas */}
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-bold text-gray-900 mb-4">
              {calibrationSteps[calibrationStep].title}
            </h2>

            <div className="relative bg-cricket-green rounded-lg overflow-hidden aspect-video">
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <Target className="mx-auto text-white/50" size={64} />
                  <p className="text-white/70 mt-4">
                    Click to mark {calibrationSteps[calibrationStep].title.toLowerCase()}
                  </p>
                </div>
              </div>

              {/* Simulated pitch markings */}
              <svg className="absolute inset-0 w-full h-full pointer-events-none">
                {calibrationData.pitchBoundary && (
                  <rect
                    x="10%"
                    y="20%"
                    width="80%"
                    height="60%"
                    stroke="white"
                    strokeWidth="2"
                    fill="none"
                    strokeDasharray="5,5"
                  />
                )}
                {calibrationData.creaseLines && (
                  <>
                    <line
                      x1="10%"
                      y1="40%"
                      x2="90%"
                      y2="40%"
                      stroke="white"
                      strokeWidth="2"
                    />
                    <line
                      x1="10%"
                      y1="60%"
                      x2="90%"
                      y2="60%"
                      stroke="white"
                      strokeWidth="2"
                    />
                  </>
                )}
                {calibrationData.stumpPositions && (
                  <>
                    <circle cx="50%" cy="40%" r="3" fill="wheat" />
                    <circle cx="50%" cy="60%" r="3" fill="wheat" />
                  </>
                )}
              </svg>
            </div>

            <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start space-x-2">
                <AlertCircle className="text-blue-600 flex-shrink-0 mt-0.5" size={16} />
                <div>
                  <p className="text-sm font-medium text-blue-800">
                    Calibration Tip
                  </p>
                  <p className="text-xs text-blue-700 mt-1">
                    {calibrationStep === 0 &&
                      'Mark all four corners of the pitch boundary in clockwise order.'}
                    {calibrationStep === 1 &&
                      'Define both bowling and batting crease lines accurately.'}
                    {calibrationStep === 2 &&
                      'Set wide guidelines based on match format (Test/ODI/T20).'}
                    {calibrationStep === 3 &&
                      'Mark the center of each stump for accurate detection.'}
                    {calibrationStep === 4 &&
                      'Ensure all cameras have clear view of the pitch.'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Camera List */}
          <div className="card">
            <h2 className="text-lg font-bold text-gray-900 mb-4">
              Active Cameras
            </h2>

            <div className="space-y-3">
              {['Bowler End', 'Batsman End', 'Side View', 'Wide Angle'].map(
                (camera, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center space-x-3">
                      <Camera className="text-gray-600" size={20} />
                      <span className="text-sm font-medium text-gray-900">
                        {camera}
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full" />
                      <span className="text-xs text-gray-600">Calibrated</span>
                    </div>
                  </div>
                )
              )}
            </div>
          </div>

          {/* Actions */}
          {allCalibrated && (
            <div className="flex space-x-4">
              <button className="flex-1 btn-primary flex items-center justify-center space-x-2">
                <Save size={20} />
                <span>Save Calibration</span>
              </button>
              <button className="flex-1 btn-secondary">Test Calibration</button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Calibration
