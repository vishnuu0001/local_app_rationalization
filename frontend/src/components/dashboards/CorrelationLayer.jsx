import React, { useState } from 'react';
import { CheckCircle2, AlertCircle, Link2 } from 'lucide-react';

const CorrelationLayer = ({ data }) => {
  const [expandedId, setExpandedId] = useState(null);
  
  if (!data || data.length === 0) {
    return <div className="text-gray-500">No correlations found</div>;
  }
  
  return (
    <div className="space-y-4">
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-blue-900 font-medium">
          {data.length} correlations found between Corent and CAST data
        </p>
      </div>
      
      {data.map((correlation, idx) => {
        const isHighConfidence = correlation.confidence_level === 'high';
        
        return (
          <div
            key={idx}
            className={`border rounded-lg overflow-hidden transition-all ${
              isHighConfidence ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-white'
            }`}
          >
            <button
              onClick={() => setExpandedId(expandedId === idx ? null : idx)}
              className={`w-full px-6 py-4 text-left flex items-center justify-between hover:opacity-80 transition-opacity ${
                isHighConfidence ? 'bg-green-50' : 'bg-gray-50'
              }`}
            >
              <div className="flex items-center gap-4 flex-1">
                <div
                  className={`flex items-center justify-center w-10 h-10 rounded-full ${
                    isHighConfidence ? 'bg-green-100' : 'bg-yellow-100'
                  }`}
                >
                  {isHighConfidence ? (
                    <CheckCircle2 size={20} className="text-green-600" />
                  ) : (
                    <AlertCircle size={20} className="text-yellow-600" />
                  )}
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-900">
                    {correlation.infra_item.app_name}
                  </p>
                  <p className="text-sm text-gray-600 mt-1">
                    {correlation.infra_item.server} → {correlation.infra_item.installed_tech}
                  </p>
                </div>
                <div
                  className={`px-4 py-2 rounded-full font-bold text-white ${
                    isHighConfidence ? 'bg-green-600' : 'bg-yellow-600'
                  }`}
                >
                  {(correlation.confidence * 100).toFixed(0)}%
                </div>
              </div>
              <div
                className={`transform transition-transform ${expandedId === idx ? 'rotate-180' : ''}`}
              >
                ▼
              </div>
            </button>
            
            {expandedId === idx && (
              <div className="p-6 border-t border-gray-200 bg-white space-y-6">
                {/* Infrastructure Side */}
                <div>
                  <h4 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <span className="text-lg">🖥️</span>
                    Infrastructure (Corent)
                  </h4>
                  <div className="grid grid-cols-2 gap-4 p-4 bg-blue-50 border border-blue-100 rounded-lg">
                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase">Application</p>
                      <p className="text-gray-900 font-medium">{correlation.infra_item.app_name}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase">App ID</p>
                      <p className="text-gray-900 font-medium">{correlation.infra_item.app_id}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase">Server</p>
                      <p className="text-gray-900 font-medium">{correlation.infra_item.server}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase">Domain</p>
                      <p className="text-gray-900 font-medium">{correlation.infra_item.domain || 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase">Tech Stack</p>
                      <p className="text-gray-900 font-medium">{correlation.infra_item.installed_tech}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase">Version</p>
                      <p className="text-gray-900 font-medium">{correlation.infra_item.version || 'N/A'}</p>
                    </div>
                    <div className="col-span-2">
                      <p className="text-xs font-semibold text-gray-600 uppercase">Deployment Path</p>
                      <p className="text-gray-900 font-medium text-sm break-words">
                        {correlation.infra_item.deployment_path || 'N/A'}
                      </p>
                    </div>
                  </div>
                </div>
                
                {/* Link Icon */}
                <div className="flex justify-center">
                  <div className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-full font-semibold">
                    <Link2 size={18} />
                    Correlated
                  </div>
                </div>
                
                {/* Code Side */}
                <div>
                  <h4 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <span className="text-lg">💻</span>
                    Code Analysis (CAST)
                  </h4>
                  <div className="grid grid-cols-2 gap-4 p-4 bg-purple-50 border border-purple-100 rounded-lg">
                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase">Application</p>
                      <p className="text-gray-900 font-medium">{correlation.cast_item.app_name}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase">App ID</p>
                      <p className="text-gray-900 font-medium">{correlation.cast_item.app_id}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase">Language</p>
                      <p className="text-gray-900 font-medium">{correlation.cast_item.language || 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase">Framework</p>
                      <p className="text-gray-900 font-medium">{correlation.cast_item.framework || 'N/A'}</p>
                    </div>
                    <div className="col-span-2">
                      <p className="text-xs font-semibold text-gray-600 uppercase">Repository</p>
                      <p className="text-gray-900 font-medium text-sm break-words">{correlation.cast_item.repo || 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase">Version</p>
                      <p className="text-gray-900 font-medium">{correlation.cast_item.version || 'N/A'}</p>
                    </div>
                  </div>
                </div>
                
                {/* Matching Criteria */}
                <div className="p-4 bg-yellow-50 border border-yellow-100 rounded-lg">
                  <h4 className="font-semibold text-gray-900 mb-3">Matching Criteria</h4>
                  <div className="space-y-2">
                    {correlation.matching_criteria.map((criterion, cidx) => (
                      <div key={cidx} className="flex items-center gap-2 text-gray-700">
                        <span className="text-yellow-600">✓</span>
                        <span>{criterion}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default CorrelationLayer;
