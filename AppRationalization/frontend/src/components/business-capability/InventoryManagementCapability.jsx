import React from 'react';
import { Package } from 'lucide-react';

const InventoryManagementCapability = () => {
  const capabilities = [
    {
      business_capability: 'Inventory Management',
      applications: 'InventoryAPI',
      technology: '.NET',
      erp_overlap: 'Partial SAP'
    },
    {
      business_capability: 'Inventory Management',
      applications: 'StockTrackerLegacy',
      technology: 'Java 8',
      erp_overlap: 'Duplicate'
    },
    {
      business_capability: 'Inventory Management',
      applications: 'WarehouseTool EU',
      technology: 'PHP',
      erp_overlap: 'Standalone'
    },
    {
      business_capability: 'Inventory Management',
      applications: 'SAP EWM',
      technology: 'SAP',
      erp_overlap: 'Core ERP'
    }
  ];

  const getERPStatusColor = (status) => {
    switch(status) {
      case 'Core ERP': return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      case 'Partial SAP': return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'Duplicate': return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'Standalone': return 'bg-gray-100 text-gray-800 border-gray-300';
      default: return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-gray-100">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center gap-3">
            <Package size={40} className="text-blue-600" />
            <div>
              <h1 className="text-4xl font-bold text-gray-900">Business Capability</h1>
              <p className="text-gray-600 mt-2">Business capability mapping with application coverage, technology stack, and ERP consolidation status</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-200">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gradient-to-r from-blue-50 to-blue-100 border-b-2 border-blue-300">
                  <th className="px-6 py-4 text-left font-bold text-gray-900 text-sm uppercase tracking-wider">
                    Business Capability
                  </th>
                  <th className="px-6 py-4 text-left font-bold text-gray-900 text-sm uppercase tracking-wider">
                    Applications
                  </th>
                  <th className="px-6 py-4 text-left font-bold text-gray-900 text-sm uppercase tracking-wider">
                    Technology
                  </th>
                  <th className="px-6 py-4 text-left font-bold text-gray-900 text-sm uppercase tracking-wider">
                    ERP Overlap
                  </th>
                </tr>
              </thead>
              <tbody>
                {capabilities.map((item, index) => (
                  <tr 
                    key={index} 
                    className={`border-b transition-colors hover:bg-blue-50 ${
                      index % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                    }`}
                  >
                    <td className="px-6 py-4 text-gray-900 font-semibold">{item.business_capability}</td>
                    <td className="px-6 py-4 text-gray-700">
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-50 text-blue-700 border border-blue-200">
                        {item.applications}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-700">
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-50 text-purple-700 border border-purple-200">
                        {item.technology}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getERPStatusColor(item.erp_overlap)}`}>
                        {item.erp_overlap}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-8">
          <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-blue-600">
            <div className="text-gray-600 text-sm font-semibold">Total Applications</div>
            <div className="text-3xl font-bold text-blue-600 mt-2">4</div>
            <p className="text-xs text-gray-500 mt-2">Covering this capability</p>
          </div>
          
          <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-orange-600">
            <div className="text-gray-600 text-sm font-semibold">Duplicates/Legacy</div>
            <div className="text-3xl font-bold text-orange-600 mt-2">1</div>
            <p className="text-xs text-gray-500 mt-2">Needs rationalization</p>
          </div>
          
          <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-emerald-600">
            <div className="text-gray-600 text-sm font-semibold">Core ERP</div>
            <div className="text-3xl font-bold text-emerald-600 mt-2">1</div>
            <p className="text-xs text-gray-500 mt-2">SAP EWM primary</p>
          </div>
          
          <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-gray-600">
            <div className="text-gray-600 text-sm font-semibold">Non-ERP</div>
            <div className="text-3xl font-bold text-gray-600 mt-2">2</div>
            <p className="text-xs text-gray-500 mt-2">Standalone/Custom</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InventoryManagementCapability;
