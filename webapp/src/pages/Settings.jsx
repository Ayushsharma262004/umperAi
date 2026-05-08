import { useState } from 'react'
import { Save, RefreshCw } from 'lucide-react'

const Settings = () => {
  const [settings, setSettings] = useState({
    // Detection Settings
    detectionModel: 'yolov8m',
    confidenceThreshold: 0.7,
    nmsThreshold: 0.5,
    maxCameras: 4,

    // Tracking Settings
    maxOcclusionFrames: 10,
    processNoise: 0.1,
    measurementNoise: 0.5,

    // Decision Settings
    decisionConfidenceThreshold: 0.8,
    wideGuidelineDistance: 0.5,
    enableLBW: true,
    enableBowled: true,
    enableCaught: true,

    // Output Settings
    enableTextOutput: true,
    enableAudioOutput: false,
    enableVisualOutput: true,
    maxLatency: 1.0,

    // Performance Settings
    targetFPS: 30,
    fpsThreshold: 25,
    memoryThreshold: 8.0,
    enableGPU: true,
  })

  const handleChange = (key, value) => {
    setSettings({
      ...settings,
      [key]: value,
    })
  }

  const handleSave = () => {
    console.log('Saving settings:', settings)
    alert('Settings saved successfully!')
  }

  const handleReset = () => {
    if (confirm('Are you sure you want to reset all settings to defaults?')) {
      // Reset to defaults
      setSettings({
        detectionModel: 'yolov8m',
        confidenceThreshold: 0.7,
        nmsThreshold: 0.5,
        maxCameras: 4,
        maxOcclusionFrames: 10,
        processNoise: 0.1,
        measurementNoise: 0.5,
        decisionConfidenceThreshold: 0.8,
        wideGuidelineDistance: 0.5,
        enableLBW: true,
        enableBowled: true,
        enableCaught: true,
        enableTextOutput: true,
        enableAudioOutput: false,
        enableVisualOutput: true,
        maxLatency: 1.0,
        targetFPS: 30,
        fpsThreshold: 25,
        memoryThreshold: 8.0,
        enableGPU: true,
      })
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-600 mt-1">
            Configure system parameters and preferences
          </p>
        </div>

        <div className="flex items-center space-x-4">
          <button
            onClick={handleReset}
            className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <RefreshCw size={20} />
            <span>Reset to Defaults</span>
          </button>
          <button
            onClick={handleSave}
            className="btn-primary flex items-center space-x-2"
          >
            <Save size={20} />
            <span>Save Changes</span>
          </button>
        </div>
      </div>

      {/* Settings Sections */}
      <div className="space-y-6">
        {/* Detection Settings */}
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-6">
            Detection Settings
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Detection Model
              </label>
              <select
                value={settings.detectionModel}
                onChange={(e) => handleChange('detectionModel', e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cricket-primary focus:border-transparent"
              >
                <option value="yolov8n">YOLOv8 Nano (Fastest)</option>
                <option value="yolov8s">YOLOv8 Small</option>
                <option value="yolov8m">YOLOv8 Medium (Balanced)</option>
                <option value="yolov8l">YOLOv8 Large</option>
                <option value="yolov8x">YOLOv8 XLarge (Most Accurate)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Confidence Threshold
              </label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={settings.confidenceThreshold}
                onChange={(e) =>
                  handleChange('confidenceThreshold', parseFloat(e.target.value))
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cricket-primary focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">
                Current: {(settings.confidenceThreshold * 100).toFixed(0)}%
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                NMS Threshold
              </label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={settings.nmsThreshold}
                onChange={(e) =>
                  handleChange('nmsThreshold', parseFloat(e.target.value))
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cricket-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Maximum Cameras
              </label>
              <input
                type="number"
                min="1"
                max="8"
                value={settings.maxCameras}
                onChange={(e) =>
                  handleChange('maxCameras', parseInt(e.target.value))
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cricket-primary focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Tracking Settings */}
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-6">
            Tracking Settings
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Max Occlusion Frames
              </label>
              <input
                type="number"
                min="1"
                max="30"
                value={settings.maxOcclusionFrames}
                onChange={(e) =>
                  handleChange('maxOcclusionFrames', parseInt(e.target.value))
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cricket-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Process Noise
              </label>
              <input
                type="number"
                min="0.01"
                max="1"
                step="0.01"
                value={settings.processNoise}
                onChange={(e) =>
                  handleChange('processNoise', parseFloat(e.target.value))
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cricket-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Measurement Noise
              </label>
              <input
                type="number"
                min="0.01"
                max="2"
                step="0.1"
                value={settings.measurementNoise}
                onChange={(e) =>
                  handleChange('measurementNoise', parseFloat(e.target.value))
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cricket-primary focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Decision Settings */}
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-6">
            Decision Settings
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Decision Confidence Threshold
              </label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={settings.decisionConfidenceThreshold}
                onChange={(e) =>
                  handleChange(
                    'decisionConfidenceThreshold',
                    parseFloat(e.target.value)
                  )
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cricket-primary focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">
                Decisions below this threshold will be flagged for review
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Wide Guideline Distance (m)
              </label>
              <input
                type="number"
                min="0.1"
                max="2"
                step="0.1"
                value={settings.wideGuidelineDistance}
                onChange={(e) =>
                  handleChange('wideGuidelineDistance', parseFloat(e.target.value))
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cricket-primary focus:border-transparent"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Enable Detectors
              </label>
              <div className="space-y-2">
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={settings.enableLBW}
                    onChange={(e) => handleChange('enableLBW', e.target.checked)}
                    className="w-4 h-4 text-cricket-primary border-gray-300 rounded focus:ring-cricket-primary"
                  />
                  <span className="text-sm text-gray-700">LBW Detector</span>
                </label>
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={settings.enableBowled}
                    onChange={(e) =>
                      handleChange('enableBowled', e.target.checked)
                    }
                    className="w-4 h-4 text-cricket-primary border-gray-300 rounded focus:ring-cricket-primary"
                  />
                  <span className="text-sm text-gray-700">Bowled Detector</span>
                </label>
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={settings.enableCaught}
                    onChange={(e) =>
                      handleChange('enableCaught', e.target.checked)
                    }
                    className="w-4 h-4 text-cricket-primary border-gray-300 rounded focus:ring-cricket-primary"
                  />
                  <span className="text-sm text-gray-700">Caught Detector</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        {/* Output Settings */}
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-6">
            Output Settings
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Output Formats
              </label>
              <div className="space-y-2">
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={settings.enableTextOutput}
                    onChange={(e) =>
                      handleChange('enableTextOutput', e.target.checked)
                    }
                    className="w-4 h-4 text-cricket-primary border-gray-300 rounded focus:ring-cricket-primary"
                  />
                  <span className="text-sm text-gray-700">Text Output</span>
                </label>
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={settings.enableAudioOutput}
                    onChange={(e) =>
                      handleChange('enableAudioOutput', e.target.checked)
                    }
                    className="w-4 h-4 text-cricket-primary border-gray-300 rounded focus:ring-cricket-primary"
                  />
                  <span className="text-sm text-gray-700">Audio Output</span>
                </label>
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={settings.enableVisualOutput}
                    onChange={(e) =>
                      handleChange('enableVisualOutput', e.target.checked)
                    }
                    className="w-4 h-4 text-cricket-primary border-gray-300 rounded focus:ring-cricket-primary"
                  />
                  <span className="text-sm text-gray-700">Visual Output</span>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Maximum Latency (seconds)
              </label>
              <input
                type="number"
                min="0.1"
                max="5"
                step="0.1"
                value={settings.maxLatency}
                onChange={(e) =>
                  handleChange('maxLatency', parseFloat(e.target.value))
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cricket-primary focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Performance Settings */}
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-6">
            Performance Settings
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Target FPS
              </label>
              <input
                type="number"
                min="15"
                max="60"
                value={settings.targetFPS}
                onChange={(e) =>
                  handleChange('targetFPS', parseInt(e.target.value))
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cricket-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                FPS Threshold (Alert)
              </label>
              <input
                type="number"
                min="10"
                max="50"
                value={settings.fpsThreshold}
                onChange={(e) =>
                  handleChange('fpsThreshold', parseInt(e.target.value))
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cricket-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Memory Threshold (GB)
              </label>
              <input
                type="number"
                min="1"
                max="32"
                step="0.5"
                value={settings.memoryThreshold}
                onChange={(e) =>
                  handleChange('memoryThreshold', parseFloat(e.target.value))
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cricket-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="flex items-center space-x-3 mt-8">
                <input
                  type="checkbox"
                  checked={settings.enableGPU}
                  onChange={(e) => handleChange('enableGPU', e.target.checked)}
                  className="w-4 h-4 text-cricket-primary border-gray-300 rounded focus:ring-cricket-primary"
                />
                <span className="text-sm font-medium text-gray-700">
                  Enable GPU Acceleration
                </span>
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Settings
