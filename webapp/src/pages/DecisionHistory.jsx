import { useState } from 'react'
import { Search, Filter, Download, Eye } from 'lucide-react'

const DecisionHistory = () => {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterType, setFilterType] = useState('all')

  const decisions = [
    {
      id: 1,
      timestamp: '2024-05-08 14:32:15',
      type: 'OUT',
      subType: 'Bowled',
      confidence: 98.5,
      requiresReview: false,
      over: '5.3',
      cameras: 4,
    },
    {
      id: 2,
      timestamp: '2024-05-08 14:30:42',
      type: 'WIDE',
      subType: 'Wide Ball',
      confidence: 92.3,
      requiresReview: false,
      over: '5.2',
      cameras: 4,
    },
    {
      id: 3,
      timestamp: '2024-05-08 14:28:18',
      type: 'OUT',
      subType: 'LBW',
      confidence: 78.2,
      requiresReview: true,
      over: '5.1',
      cameras: 4,
    },
    {
      id: 4,
      timestamp: '2024-05-08 14:25:55',
      type: 'NO_BALL',
      subType: 'Front Foot',
      confidence: 95.7,
      requiresReview: false,
      over: '4.6',
      cameras: 4,
    },
    {
      id: 5,
      timestamp: '2024-05-08 14:23:30',
      type: 'LEGAL_DELIVERY',
      subType: 'Fair Delivery',
      confidence: 96.8,
      requiresReview: false,
      over: '4.5',
      cameras: 4,
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
      case 'LEGAL_DELIVERY':
        return 'bg-green-100 text-green-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Decision History</h1>
        <p className="text-gray-600 mt-1">
          Browse and analyze past umpiring decisions
        </p>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
          <div className="flex-1 max-w-md">
            <div className="relative">
              <Search
                className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
                size={20}
              />
              <input
                type="text"
                placeholder="Search decisions..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cricket-primary focus:border-transparent"
              />
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cricket-primary focus:border-transparent"
            >
              <option value="all">All Decisions</option>
              <option value="OUT">Dismissals</option>
              <option value="WIDE">Wide Balls</option>
              <option value="NO_BALL">No Balls</option>
              <option value="LEGAL_DELIVERY">Legal Deliveries</option>
              <option value="review">Requires Review</option>
            </select>

            <button className="btn-secondary flex items-center space-x-2">
              <Download size={20} />
              <span>Export</span>
            </button>
          </div>
        </div>
      </div>

      {/* Decisions Table */}
      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                  Timestamp
                </th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                  Over
                </th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                  Decision
                </th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                  Type
                </th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                  Confidence
                </th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                  Status
                </th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {decisions.map((decision) => (
                <tr
                  key={decision.id}
                  className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                >
                  <td className="py-4 px-4 text-sm text-gray-900">
                    {decision.timestamp}
                  </td>
                  <td className="py-4 px-4 text-sm font-medium text-gray-900">
                    {decision.over}
                  </td>
                  <td className="py-4 px-4">
                    <span
                      className={`inline-flex px-3 py-1 rounded-full text-xs font-semibold ${getDecisionColor(
                        decision.type
                      )}`}
                    >
                      {decision.type}
                    </span>
                  </td>
                  <td className="py-4 px-4 text-sm text-gray-900">
                    {decision.subType}
                  </td>
                  <td className="py-4 px-4">
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 max-w-[100px] bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            decision.confidence >= 90
                              ? 'bg-green-500'
                              : decision.confidence >= 80
                              ? 'bg-yellow-500'
                              : 'bg-red-500'
                          }`}
                          style={{ width: `${decision.confidence}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-gray-900">
                        {decision.confidence}%
                      </span>
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    {decision.requiresReview ? (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        Review
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        Confirmed
                      </span>
                    )}
                  </td>
                  <td className="py-4 px-4">
                    <button className="text-cricket-primary hover:text-blue-800 transition-colors">
                      <Eye size={18} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between mt-6 pt-6 border-t border-gray-200">
          <p className="text-sm text-gray-600">
            Showing <span className="font-medium">1</span> to{' '}
            <span className="font-medium">5</span> of{' '}
            <span className="font-medium">247</span> decisions
          </p>
          <div className="flex items-center space-x-2">
            <button className="px-3 py-1 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">
              Previous
            </button>
            <button className="px-3 py-1 bg-cricket-primary text-white rounded-lg text-sm font-medium">
              1
            </button>
            <button className="px-3 py-1 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">
              2
            </button>
            <button className="px-3 py-1 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">
              3
            </button>
            <button className="px-3 py-1 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DecisionHistory
