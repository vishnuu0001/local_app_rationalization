import React, { useState, useEffect } from 'react';
import { Download, ChevronLeft, ChevronRight } from 'lucide-react';
import * as XLSX from 'xlsx';
import { API_BASE } from '../services/api';

const FileViewer = ({ fileId, filename, onClose, isInline = true }) => {
  const [error, setError] = useState(null);
  const [excelData, setExcelData] = useState(null);
  const [isLoadingExcel, setIsLoadingExcel] = useState(false);
  const [currentSheet, setCurrentSheet] = useState(0);
  const [sheetNames, setSheetNames] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');

  const fileUrl = `${API_BASE}/upload/pdf/${fileId}`;
  
  // Determine file type from filename
  const getFileType = (name) => {
    const ext = name.split('.').pop().toLowerCase();
    if (['xls', 'xlsx', 'xlsm'].includes(ext)) return 'excel';
    if (['pdf'].includes(ext)) return 'pdf';
    return 'unknown';
  };

  const fileType = getFileType(filename);

  // Load and parse Excel file
  useEffect(() => {
    if (fileType === 'excel') {
      setIsLoadingExcel(true);
      setError(null);
      fetch(fileUrl, { mode: 'cors' })
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          return response.arrayBuffer();
        })
        .then(data => {
          const workbook = XLSX.read(data, { type: 'array' });
          setSheetNames(workbook.SheetNames);
          const sheets = {};
          workbook.SheetNames.forEach((name, idx) => {
            const worksheet = workbook.Sheets[name];
            const jsonData = XLSX.utils.sheet_to_json(worksheet);
            sheets[idx] = jsonData;
          });
          setExcelData(sheets);
          setCurrentSheet(0);
          setIsLoadingExcel(false);
        })
        .catch(err => {
          setIsLoadingExcel(false);
          setError('Failed to load Excel file: ' + err.message);
        });
    }
  }, [fileId, filename, fileType, fileUrl]);

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = fileUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Filter Excel data based on search term
  const filteredExcelData = excelData && excelData[currentSheet]
    ? excelData[currentSheet].filter(row => {
        if (!searchTerm.trim()) return true;
        return Object.values(row).some(cell => 
          String(cell).toLowerCase().includes(searchTerm.toLowerCase())
        );
      })
    : [];

  // For inline mode (in expandable frame)
  if (isInline) {
    return (
      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-gray-200">
          <div className="flex-1" />
          <button
            onClick={handleDownload}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm"
            title={`Download ${fileType}`}
          >
            <Download size={18} />
            Download
          </button>
        </div>

        {/* Content */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {fileType === 'excel' ? (
            // Excel preview with table display
            <div className="w-full">
              {error ? (
                <div className="p-8 bg-red-50">
                  <p className="text-red-700 text-sm font-medium mb-2">⚠️ Preview Error</p>
                  <p className="text-red-600 text-xs">{error}</p>
                  <p className="text-red-600 text-xs mt-2">Click Download to open in Excel.</p>
                </div>
              ) : excelData && Object.keys(excelData).length > 0 ? (
                <div>
                  {/* Sheet tabs */}
                  {sheetNames.length > 1 && (
                    <div className="flex items-center gap-2 p-4 border-b border-gray-200 bg-gray-50 overflow-x-auto">
                      {sheetNames.length > 1 && currentSheet > 0 && (
                        <button
                          onClick={() => setCurrentSheet(currentSheet - 1)}
                          className="p-1 hover:bg-gray-200 rounded transition"
                          title="Previous sheet"
                        >
                          <ChevronLeft size={18} />
                        </button>
                      )}
                      {sheetNames.map((name, idx) => (
                        <button
                          key={idx}
                          onClick={() => setCurrentSheet(idx)}
                          className={`px-3 py-1 rounded text-sm font-medium whitespace-nowrap transition ${
                            currentSheet === idx
                              ? 'bg-blue-600 text-white'
                              : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
                          }`}
                        >
                          {name}
                        </button>
                      ))}
                      {sheetNames.length > 1 && currentSheet < sheetNames.length - 1 && (
                        <button
                          onClick={() => setCurrentSheet(currentSheet + 1)}
                          className="p-1 hover:bg-gray-200 rounded transition ml-auto"
                          title="Next sheet"
                        >
                          <ChevronRight size={18} />
                        </button>
                      )}
                    </div>
                  )}
                  
                  {/* Search bar */}
                  <div className="p-4 border-b border-gray-200 bg-gray-50">
                    <input
                      type="text"
                      placeholder="Search records..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                    />
                    <p className="text-xs text-gray-600 mt-2">
                      Showing {filteredExcelData.length} of {excelData[currentSheet]?.length || 0} records
                    </p>
                  </div>
                  
                  {/* Data table */}
                  <div className="overflow-x-auto max-h-96">
                    <table className="w-full text-sm border-collapse">
                      <thead>
                        <tr className="bg-gray-100 border-b border-gray-300">
                          {excelData[currentSheet] && excelData[currentSheet].length > 0
                            ? Object.keys(excelData[currentSheet][0]).map((key) => (
                                <th
                                  key={key}
                                  className="px-4 py-2 text-left font-semibold text-gray-700 border-r border-gray-300 whitespace-nowrap"
                                >
                                  {key}
                                </th>
                              ))
                            : null}
                        </tr>
                      </thead>
                      <tbody>
                        {filteredExcelData.length > 0 ? (
                          filteredExcelData.map((row, rowIdx) => (
                            <tr key={rowIdx} className="border-b border-gray-200 hover:bg-blue-50">
                              {Object.values(row).map((cell, cellIdx) => (
                                <td
                                  key={cellIdx}
                                  className="px-4 py-2 text-gray-600 border-r border-gray-200 whitespace-nowrap overflow-hidden text-ellipsis max-w-xs"
                                  title={String(cell)}
                                >
                                  {cell !== null && cell !== undefined ? String(cell) : '-'}
                                </td>
                              ))}
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan="100" className="px-4 py-4 text-center text-gray-500 text-sm">
                              No records found matching "{searchTerm}"
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : isLoadingExcel ? (
                <div className="p-8 bg-gray-50 text-center">
                  <p className="text-gray-500 text-sm">Loading Excel file...</p>
                </div>
              ) : (
                <div className="p-8 bg-yellow-50 text-center">
                  <p className="text-yellow-700 text-sm">No Excel data available for preview.</p>
                </div>
              )}
            </div>
          ) : (
            // PDF preview
            <div className="w-full">
              <iframe
                key={fileId}
                src={fileUrl}
                className="w-full border-0"
                style={{ 
                  minHeight: '700px',
                  height: '700px'
                }}
                title={filename}
                onError={() => {
                  setError(`Failed to load ${fileType}`);
                }}
              />
            </div>
          )}
        </div>
      </div>
    );
  }


  return null;
};

export default FileViewer;
