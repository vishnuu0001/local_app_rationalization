import React from 'react';
import { Code2, Box, Zap } from 'lucide-react';

const CASTDashboard = ({ data }) => {
  
  if (!data) return <div className="text-gray-500">No CAST data available</div>;
  
  // Ensure arrays are properly formatted (handle case where they might be objects)
  let repoAppMapping = data.repo_app_mapping || [];
  if (!Array.isArray(repoAppMapping)) {
    repoAppMapping = Object.values(repoAppMapping);
  }
  
  let components = data.architecture_components || [];
  if (!Array.isArray(components)) {
    components = Object.values(components);
  }
  
  const dependencies = data.internal_dependencies || {};
  
  return (
    <div className="space-y-8">
      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-green-50 to-green-100 border border-green-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-600 text-sm font-semibold">Total Applications</p>
              <p className="text-green-900 text-3xl font-bold mt-1">{repoAppMapping.length}</p>
            </div>
            <Code2 className="text-green-600" size={32} />
          </div>
        </div>
        
        <div className="bg-gradient-to-br from-indigo-50 to-indigo-100 border border-indigo-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-indigo-600 text-sm font-semibold">Architecture Components</p>
              <p className="text-indigo-900 text-3xl font-bold mt-1">{components.length}</p>
            </div>
            <Box className="text-indigo-600" size={32} />
          </div>
        </div>
        
        <div className="bg-gradient-to-br from-pink-50 to-pink-100 border border-pink-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-pink-600 text-sm font-semibold">Dependencies Detected</p>
              <p className="text-pink-900 text-3xl font-bold mt-1">{Object.keys(dependencies).length}</p>
            </div>
            <Zap className="text-pink-600" size={32} />
          </div>
        </div>
      </div>
      
      {/* Repository-Application Mapping */}
      <div>
        <h3 className="text-lg font-bold text-gray-900 mb-4">Repository ↔ Application Mapping</h3>
        <div className="space-y-3">
          {repoAppMapping.map((item, idx) => (
            <div
              key={idx}
              className="p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
            >
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <p className="text-xs font-semibold text-gray-600 uppercase">Application</p>
                  <p className="text-gray-900 font-medium">{item.app_name}</p>
                  <p className="text-xs text-gray-500 mt-1">ID: {item.app_id}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-gray-600 uppercase">Language</p>
                  <p className="text-gray-900 font-medium">{item.language || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-gray-600 uppercase">Framework</p>
                  <p className="text-gray-900 font-medium">{item.framework || 'N/A'}</p>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-gray-100">
                <p className="text-xs font-semibold text-gray-600 uppercase mb-1">Repository</p>
                <p className="text-gray-700 text-sm break-words">{item.repo || 'N/A'}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {/* Architecture Components */}
      <div>
        <h3 className="text-lg font-bold text-gray-900 mb-4">Architecture Components</h3>
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-indigo-50 border-b border-gray-200">
                  <th className="px-6 py-3 text-left font-semibold text-gray-900">Application</th>
                  <th className="px-6 py-3 text-left font-semibold text-gray-900">Type</th>
                  <th className="px-6 py-3 text-left font-semibold text-gray-900">Language</th>
                  <th className="px-6 py-3 text-left font-semibold text-gray-900">Framework</th>
                </tr>
              </thead>
              <tbody>
                {components.map((component, idx) => (
                  <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-6 py-3 text-gray-900 font-medium">{component.app_name}</td>
                    <td className="px-6 py-3">
                      <span className="px-2 py-1 bg-indigo-100 text-indigo-700 text-xs font-semibold rounded">
                        {component.type}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-gray-700">{component.language || 'N/A'}</td>
                    <td className="px-6 py-3 text-gray-700">{component.framework || 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      
      {/* Internal Dependencies */}
      <div>
        <h3 className="text-lg font-bold text-gray-900 mb-4">Internal Dependency Graph</h3>
        <div className="space-y-3">
          {Object.entries(dependencies).map(([app, depData]) => {
            // Handle both array and object formats for dependencies
            let depList = [];
            if (Array.isArray(depData)) {
              depList = depData;
            } else if (depData && typeof depData === 'object') {
              // If it's an object with dependency_count, just show the count
              const count = depData.dependency_count || depData.count || 0;
              depList = count > 0 ? [`${count} dependent(s)`] : ['No dependencies'];
            }
            
            return (
              <div key={app} className="p-4 bg-white border border-gray-200 rounded-lg">
                <p className="font-semibold text-gray-900 flex items-center gap-2">
                  <Code2 size={18} className="text-pink-600" />
                  {app}
                </p>
                <div className="mt-3 ml-6 flex flex-wrap gap-2">
                  {depList.map((dep, idx) => (
                    <div key={idx} className="flex items-center gap-1">
                      <span className="text-gray-600">→</span>
                      <span className="px-3 py-1 bg-pink-50 text-pink-700 text-sm rounded-full border border-pink-100">
                        {typeof dep === 'string' ? dep.trim() : String(dep)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default CASTDashboard;
