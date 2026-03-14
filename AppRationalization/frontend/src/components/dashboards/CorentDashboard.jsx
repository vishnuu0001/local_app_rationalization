import React, { useState } from 'react';
import { Server, Package, Globe, Database } from 'lucide-react';

const CorentDashboard = ({ data }) => {
  const [expandedServer, setExpandedServer] = useState(null);
  
  if (!data) return <div className="text-gray-500">No Corent data available</div>;
  
  // Ensure serverAppMapping is an array (handle case where it might be an object)
  let serverAppMapping = data.server_app_mapping || [];
  if (!Array.isArray(serverAppMapping)) {
    serverAppMapping = Object.values(serverAppMapping);
  }
  
  const techStack = data.tech_stack || {};
  const deploymentFootprint = data.deployment_footprint || {};
  
  // Group apps by server
  const appsByServer = {};
  if (Array.isArray(serverAppMapping)) {
    serverAppMapping.forEach(app => {
      if (app && typeof app === 'object') {
        const server = app.server || 'Unknown';
        if (!appsByServer[server]) appsByServer[server] = [];
        appsByServer[server].push(app);
      }
    });
  }
  
  return (
    <div className="space-y-8">
      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-600 text-sm font-semibold">Total Applications</p>
              <p className="text-blue-900 text-3xl font-bold mt-1">{serverAppMapping.length}</p>
            </div>
            <Package className="text-blue-600" size={32} />
          </div>
        </div>
        
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 border border-purple-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-600 text-sm font-semibold">Unique Servers</p>
              <p className="text-purple-900 text-3xl font-bold mt-1">{Object.keys(appsByServer).length}</p>
            </div>
            <Server className="text-purple-600" size={32} />
          </div>
        </div>
        
        <div className="bg-gradient-to-br from-orange-50 to-orange-100 border border-orange-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-orange-600 text-sm font-semibold">Tech Stack Types</p>
              <p className="text-orange-900 text-3xl font-bold mt-1">{Object.keys(techStack).length}</p>
            </div>
            <Database className="text-orange-600" size={32} />
          </div>
        </div>
        
        <div className="bg-gradient-to-br from-teal-50 to-teal-100 border border-teal-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-teal-600 text-sm font-semibold">Deployment Footprint</p>
              <p className="text-teal-900 text-3xl font-bold mt-1">{Object.keys(deploymentFootprint).length}</p>
            </div>
            <Globe className="text-teal-600" size={32} />
          </div>
        </div>
      </div>
      
      {/* Server-Application Mapping */}
      <div>
        <h3 className="text-lg font-bold text-gray-900 mb-4">Server ↔ Application Mapping</h3>
        <div className="space-y-3">
          {Object.entries(appsByServer).map(([server, apps]) => {
            // Ensure apps is an array
            let appsList = apps;
            if (!Array.isArray(appsList)) {
              appsList = Object.values(appsList);
            }
            
            return (
              <div key={server} className="border border-gray-200 rounded-lg overflow-hidden">
                <button
                  onClick={() => setExpandedServer(expandedServer === server ? null : server)}
                  className="w-full px-6 py-4 bg-gray-50 hover:bg-gray-100 transition-colors text-left flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <Server size={20} className="text-blue-600" />
                    <span className="font-semibold text-gray-900">{server}</span>
                    <span className="ml-2 px-3 py-1 bg-blue-100 text-blue-700 text-xs font-semibold rounded-full">
                      {Array.isArray(appsList) ? appsList.length : 0} app{Array.isArray(appsList) && appsList.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <span className={`transform transition-transform ${expandedServer === server ? 'rotate-180' : ''}`}>
                    ▼
                  </span>
                </button>
                
                {expandedServer === server && (
                  <div className="p-6 border-t border-gray-200 bg-white space-y-3">
                    {Array.isArray(appsList) && appsList.map((app, idx) => (
                    <div key={idx} className="p-4 bg-blue-50 border border-blue-100 rounded-lg">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-xs font-semibold text-gray-600 uppercase">Application</p>
                          <p className="text-gray-900 font-medium">{app.app_name}</p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-gray-600 uppercase">App ID</p>
                          <p className="text-gray-900 font-medium">{app.app_id}</p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-gray-600 uppercase">Tech Stack</p>
                          <p className="text-gray-900 font-medium">{app.installed_tech || 'N/A'}</p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-gray-600 uppercase">Version</p>
                          <p className="text-gray-900 font-medium">{app.version || 'N/A'}</p>
                        </div>
                        <div className="col-span-2">
                          <p className="text-xs font-semibold text-gray-600 uppercase">Deployment Path</p>
                          <p className="text-gray-900 font-medium text-sm break-words">{app.deployment_path || 'N/A'}</p>
                        </div>
                        <div className="col-span-2">
                          <p className="text-xs font-semibold text-gray-600 uppercase">Domain</p>
                          <p className="text-gray-900 font-medium">{app.domain || 'N/A'}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              </div>
            );
          })}
        </div>
      </div>
      
      {/* Technology Stack */}
      <div>
        <h3 className="text-lg font-bold text-gray-900 mb-4">Installed Technology Stack</h3>
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(techStack).map(([tech, count]) => (
              <div key={tech} className="p-4 bg-orange-50 border border-orange-100 rounded-lg">
                <p className="text-orange-900 font-semibold">{tech}</p>
                <p className="text-orange-600 text-sm mt-1">Deployed on {count} system{count !== 1 ? 's' : ''}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
      
      {/* Deployment Footprint */}
      <div>
        <h3 className="text-lg font-bold text-gray-900 mb-4">Deployment Footprint</h3>
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="space-y-0">
            {Object.entries(deploymentFootprint).map(([location, count]) => (
              <div key={location} className="p-4 border-b border-gray-100 last:border-b-0">
                <p className="font-semibold text-gray-900 mb-2">{location}</p>
                <p className="text-teal-700 text-sm">
                  {count} application{count !== 1 ? 's' : ''} deployed
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CorentDashboard;
