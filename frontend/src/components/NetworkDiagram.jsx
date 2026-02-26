import React from 'react';

const NetworkDiagram = () => {
  const nodes = [
    { id: 1, name: 'prd-mfg-app-01', type: 'Server', env: 'Production' },
    { id: 2, name: 'k8s-eu-central-1', type: 'K8s', env: 'Production' },
    { id: 3, name: 'dev-fin-app-01', type: 'Server', env: 'Development' },
    { id: 4, name: 'MfgExecutionService', type: 'App', env: 'Production' },
    { id: 5, name: 'InventoryAPI', type: 'App', env: 'Production' },
    { id: 6, name: 'FinanceLedgerApp', type: 'App', env: 'Development' },
  ];

  const getNodeColor = (type) => {
    const colors = {
      Server: 'bg-blue-100 text-blue-900',
      K8s: 'bg-purple-100 text-purple-900',
      App: 'bg-green-100 text-green-900',
    };
    return colors[type] || 'bg-gray-100 text-gray-900';
  };

  return (
    <div className="w-full">
      <div className="bg-gray-100 rounded-lg p-8 min-h-96 flex flex-col items-center justify-center">
        <div className="text-center mb-12">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Network → Infrastructure → Application Linkage
          </h3>
          <p className="text-sm text-gray-600">
            5 discovered servers | 8 mapped applications | 12 identified integrations
          </p>
        </div>

        <div className="flex flex-wrap gap-4 justify-center max-w-4xl">
          {nodes.map((node) => (
            <div
              key={node.id}
              className={`${getNodeColor(
                node.type
              )} px-6 py-4 rounded-lg shadow-md font-semibold text-center min-w-40 transform transition-all hover:scale-105`}
            >
              <div className="text-sm opacity-75">{node.type}</div>
              <div className="font-bold text-lg">{node.name}</div>
              <div className="text-xs opacity-75 mt-1">{node.env}</div>
            </div>
          ))}
        </div>

        <div className="mt-12 grid grid-cols-3 gap-8 text-center">
          <div>
            <div className="text-2xl font-bold text-green-600">420</div>
            <div className="text-sm text-gray-600">VMs</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-purple-600">35</div>
            <div className="text-sm text-gray-600">K8s Clusters</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-red-600">17</div>
            <div className="text-sm text-gray-600">Orphan Systems</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NetworkDiagram;
