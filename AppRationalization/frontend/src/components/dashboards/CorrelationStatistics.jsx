import React from 'react';
import { AlertCircle, CheckCircle2, HelpCircle } from 'lucide-react';

const CorrelationStatistics = ({ data }) => {
  if (!data) return <div className="text-gray-500">No data available</div>;
  
  const statistics = data.statistics || {};
  const correlation = data.correlation || {};
  const unmatchedCorent = data.unmatched_corent || [];
  const unmatchedCast = data.unmatched_cast || [];
  
  // Use statistics.total_matched (all phases) as the primary matched count.
  // Fall back to correlation.matched_count for backwards-compat with stored results.
  const matchedCount = statistics.total_matched ?? statistics.correlated_total ?? correlation.matched_count ?? 0;
  // Use statistics.match_percentage which is now calculated against the proper app denominator.
  const matchPercentage = statistics.match_percentage ?? correlation.match_percentage ?? 0;
  // corent_total now = IndustryData application count (not server entries).
  const corentTotal = statistics.industry_total ?? statistics.corent_total ?? 0;
  const corentServerTotal = statistics.corent_server_total ?? 0;
  const castTotal = statistics.cast_total ?? 0;

  const directMatched     = statistics.direct_matched ?? 0;
  const serverNameMatched = statistics.server_name_matched ?? 0;
  const exactNameMatched  = statistics.exact_name_matched ?? 0;
  const fuzzyMatched      = statistics.fuzzy_matched ?? 0;
  
  return (
    <div className="space-y-8">
      {/* Main Statistics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200 rounded-lg p-6">
          <div className="text-sm font-semibold text-blue-600 uppercase mb-2">Business / Industry Apps</div>
          <div className="text-4xl font-bold text-blue-900">{corentTotal}</div>
          <p className="text-sm text-blue-700 mt-2">
            Applications in portfolio
            {corentServerTotal > 0 && <span className="block text-xs text-blue-500 mt-1">{corentServerTotal} infrastructure servers</span>}
          </p>
        </div>
        
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 border border-purple-200 rounded-lg p-6">
          <div className="text-sm font-semibold text-purple-600 uppercase mb-2">Total CAST Items</div>
          <div className="text-4xl font-bold text-purple-900">{castTotal}</div>
          <p className="text-sm text-purple-700 mt-2">Code repositories/applications</p>
        </div>
        
        <div className="bg-gradient-to-br from-green-50 to-green-100 border border-green-200 rounded-lg p-6">
          <div className="text-sm font-semibold text-green-600 uppercase mb-2">Matched Items</div>
          <div className="text-4xl font-bold text-green-900">{matchedCount}</div>
          <p className="text-sm text-green-700 mt-2">Successfully correlated (all methods)</p>
        </div>
        
        <div className="bg-gradient-to-br from-orange-50 to-orange-100 border border-orange-200 rounded-lg p-6">
          <div className="text-sm font-semibold text-orange-600 uppercase mb-2">Match Rate</div>
          <div className="text-4xl font-bold text-orange-900">{Number(matchPercentage).toFixed(1)}%</div>
          <p className="text-sm text-orange-700 mt-2">Correlation coverage</p>
        </div>
      </div>

      {/* Match method breakdown */}
      {(directMatched + serverNameMatched + exactNameMatched + fuzzyMatched) > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="font-bold text-gray-900 mb-4">Match Method Breakdown</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 bg-green-50 rounded-lg border border-green-200">
              <div className="text-2xl font-bold text-green-800">{directMatched}</div>
              <div className="text-xs font-semibold text-green-600 mt-1">APP ID Exact</div>
              <div className="text-xs text-green-500">Confidence 1.0</div>
            </div>
            <div className="text-center p-3 bg-teal-50 rounded-lg border border-teal-200">
              <div className="text-2xl font-bold text-teal-800">{serverNameMatched}</div>
              <div className="text-xs font-semibold text-teal-600 mt-1">Server Name</div>
              <div className="text-xs text-teal-500">Confidence 0.9</div>
            </div>
            <div className="text-center p-3 bg-blue-50 rounded-lg border border-blue-200">
              <div className="text-2xl font-bold text-blue-800">{exactNameMatched}</div>
              <div className="text-xs font-semibold text-blue-600 mt-1">App Name Exact</div>
              <div className="text-xs text-blue-500">Confidence 0.95</div>
            </div>
            <div className="text-center p-3 bg-yellow-50 rounded-lg border border-yellow-200">
              <div className="text-2xl font-bold text-yellow-800">{fuzzyMatched}</div>
              <div className="text-xs font-semibold text-yellow-600 mt-1">App Name Fuzzy</div>
              <div className="text-xs text-yellow-500">Confidence 0.6–0.85</div>
            </div>
          </div>
        </div>
      )}
      
      {/* Match Rate Progress Bar */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="font-bold text-gray-900 mb-4">Correlation Coverage</h3>
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-700 font-medium">Overall Match Rate</span>
              <span className="text-xl font-bold text-orange-600">{Number(matchPercentage).toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
              <div
                className="bg-gradient-to-r from-orange-500 to-orange-600 h-full transition-all duration-1000 ease-out"
                style={{ width: `${Math.min(matchPercentage, 100)}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Confidence Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-green-200 bg-green-50 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle2 size={24} className="text-green-600" />
            <h3 className="font-bold text-gray-900">High Confidence</h3>
          </div>
          <p className="text-green-700 text-sm mb-2">Matches with confidence ≥ 85%</p>
          <div className="text-3xl font-bold text-green-900">
            {data.correlation_layer?.filter(c => c.confidence_level === 'high').length || 0}
          </div>
        </div>
        
        <div className="bg-white border border-yellow-200 bg-yellow-50 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <AlertCircle size={24} className="text-yellow-600" />
            <h3 className="font-bold text-gray-900">Medium Confidence</h3>
          </div>
          <p className="text-yellow-700 text-sm mb-2">Matches with confidence 60-84%</p>
          <div className="text-3xl font-bold text-yellow-900">
            {data.correlation_layer?.filter(c => c.confidence_level === 'medium').length || 0}
          </div>
        </div>
        
        <div className="bg-white border border-gray-200 bg-gray-50 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <HelpCircle size={24} className="text-gray-600" />
            <h3 className="font-bold text-gray-900">Unmatched</h3>
          </div>
          <p className="text-gray-700 text-sm mb-2">Items with no correlation</p>
          <div className="text-3xl font-bold text-gray-900">
            {unmatchedCorent.length + unmatchedCast.length}
          </div>
        </div>
      </div>
      
      {/* Unmatched Items */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Unmatched Corent Items */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
            <AlertCircle size={20} className="text-orange-600" />
            Unmatched Infrastructure Items ({unmatchedCorent.length})
          </h3>
          
          {unmatchedCorent.length === 0 ? (
            <p className="text-gray-500 italic">All infrastructure applications are correlated</p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {unmatchedCorent.map((item, idx) => (
                <div key={idx} className="p-3 bg-orange-50 border border-orange-100 rounded text-sm">
                  <p className="font-medium text-gray-900">{item.app_name}</p>
                  <p className="text-gray-600 text-xs mt-1">
                    {item.server} | {item.installed_tech}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* Unmatched CAST Items */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
            <AlertCircle size={20} className="text-purple-600" />
            Unmatched CAST Items ({unmatchedCast.length})
          </h3>
          
          {unmatchedCast.length === 0 ? (
            <p className="text-gray-500 italic">All CAST applications are correlated</p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {unmatchedCast.map((item, idx) => (
                <div key={idx} className="p-3 bg-purple-50 border border-purple-100 rounded text-sm">
                  <p className="font-medium text-gray-900">{item.app_name}</p>
                  <p className="text-gray-600 text-xs mt-1">
                    {item.language} | {item.framework}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      
      {/* Summary */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="font-bold text-gray-900 mb-4">Summary</h3>
        <div className="space-y-3 text-gray-700">
          <p>
            <span className="font-semibold">Industry / Business Portfolio:</span> {corentTotal} applications{corentServerTotal > 0 ? `, ${corentServerTotal} infrastructure servers` : ''}
          </p>
          <p>
            <span className="font-semibold">CAST Code Analysis:</span> {castTotal} applications with {new Set(data.cast_dashboard?.repo_app_mapping?.map(a => a.language)).size} different languages
          </p>
          <p>
            <span className="font-semibold">Correlation Result:</span> {matchedCount} applications successfully matched across all methods ({directMatched} by App ID, {serverNameMatched} by Server Name, {exactNameMatched} by App Name exact, {fuzzyMatched} by fuzzy name). {unmatchedCorent.length + unmatchedCast.length} items remain unmatched.
          </p>
          <p>
            <span className="font-semibold">Next Steps:</span> Review unmatched items, investigate low-confidence correlations, and export the master matrix for further analysis.
          </p>
        </div>
      </div>
    </div>
  );
};

export default CorrelationStatistics;
