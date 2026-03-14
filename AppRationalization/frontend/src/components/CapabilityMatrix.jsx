import React, { useState } from 'react';

const CapabilityMatrix = ({ capabilities }) => {
  const [expandedCapability, setExpandedCapability] = useState(null);

  if (!capabilities || capabilities.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">No capabilities found</p>
      </div>
    );
  }

  const getRedundancyColor = (level) => {
    const colors = {
      None: 'bg-green-100 text-green-700',
      Low: 'bg-yellow-100 text-yellow-700',
      Medium: 'bg-orange-100 text-orange-700',
      High: 'bg-red-100 text-red-700',
    };
    return colors[level] || 'bg-gray-100 text-gray-700';
  };

  const getERPOverlapColor = (overlap) => {
    const colors = {
      None: 'text-gray-600',
      Partial: 'text-yellow-600',
      Duplicate: 'text-red-600',
      'Core ERP': 'text-green-600',
    };
    return colors[overlap] || 'text-gray-600';
  };

  return (
    <div className="space-y-6">
      {capabilities.map((capability) => (
        <div
          key={capability.id}
          className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-md hover:shadow-lg transition-all"
        >
          <div
            onClick={() =>
              setExpandedCapability(
                expandedCapability === capability.id ? null : capability.id
              )
            }
            className="p-6 cursor-pointer hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h3 className="text-lg font-bold text-gray-900">
                  {capability.capability_name}
                </h3>
                {capability.parent_capability && (
                  <p className="text-sm text-gray-600 mt-1">
                    {capability.parent_capability} / {capability.capability_name}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-6 ml-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {capability.mappings.length}
                  </div>
                  <div className="text-xs text-gray-600">Applications</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">
                    {capability.summary.duplicate_count}
                  </div>
                  <div className="text-xs text-gray-600">Duplicates</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    €
                    {(capability.summary.total_maintenance_cost / 1000000).toFixed(
                      1
                    )}
                    M
                  </div>
                  <div className="text-xs text-gray-600">Cost</div>
                </div>
                <div className="text-xl text-gray-400">
                  {expandedCapability === capability.id ? '▼' : '▶'}
                </div>
              </div>
            </div>
          </div>

          {expandedCapability === capability.id && (
            <div className="border-t border-gray-200 bg-gray-50 p-6">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-200">
                      <th className="px-4 py-3 text-left font-semibold text-gray-700">
                        Application
                      </th>
                      <th className="px-4 py-3 text-left font-semibold text-gray-700">
                        Technology
                      </th>
                      <th className="px-4 py-3 text-left font-semibold text-gray-700">
                        ERP Overlap
                      </th>
                      <th className="px-4 py-3 text-left font-semibold text-gray-700">
                        Redundancy
                      </th>
                      <th className="px-4 py-3 text-left font-semibold text-gray-700">
                        Criticality
                      </th>
                      <th className="px-4 py-3 text-left font-semibold text-gray-700">
                        Cost
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {capability.mappings.map((mapping) => (
                      <tr
                        key={mapping.id}
                        className="border-b border-gray-200 hover:bg-gray-100"
                      >
                        <td className="px-4 py-3 font-semibold text-gray-900">
                          {mapping.application_name}
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {mapping.technology}
                        </td>
                        <td
                          className={`px-4 py-3 font-semibold ${getERPOverlapColor(
                            mapping.erp_overlap
                          )}`}
                        >
                          {mapping.erp_overlap}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-3 py-1 rounded-full text-xs font-semibold ${getRedundancyColor(
                              mapping.redundancy_level
                            )}`}
                          >
                            {mapping.redundancy_level}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {mapping.criticality}
                        </td>
                        <td className="px-4 py-3 font-semibold text-gray-900">
                          €
                          {mapping.maintenance_cost
                            ? (mapping.maintenance_cost / 1000000).toFixed(2)
                            : '0'}
                          M
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white p-4 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    {capability.summary.erp_coverage.core}
                  </div>
                  <div className="text-xs text-gray-600">Core ERP</div>
                </div>
                <div className="bg-white p-4 rounded-lg">
                  <div className="text-2xl font-bold text-yellow-600">
                    {capability.summary.erp_coverage.partial}
                  </div>
                  <div className="text-xs text-gray-600">Partial Overlap</div>
                </div>
                <div className="bg-white p-4 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">
                    {capability.summary.erp_coverage.duplicate}
                  </div>
                  <div className="text-xs text-gray-600">Duplicate</div>
                </div>
                <div className="bg-white p-4 rounded-lg">
                  <div className="text-2xl font-bold text-gray-600">
                    {capability.summary.erp_coverage.none}
                  </div>
                  <div className="text-xs text-gray-600">Standalone</div>
                </div>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default CapabilityMatrix;
