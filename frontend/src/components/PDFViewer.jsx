import React, { useState } from 'react';
import { Download } from 'lucide-react';

const PDFViewer = ({ fileId, filename, onClose, isInline = true }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const apiBase = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';
  const documentUrl = `${apiBase}/upload/pdf/${fileId}`;

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = documentUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

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
            title="Download PDF"
          >
            <Download size={18} />
            Download
          </button>
        </div>

        {/* Content */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <iframe
            key={fileId}
            src={documentUrl}
            className="w-full"
            style={{ minHeight: '600px' }}
            title={filename}
            onLoad={() => setLoading(false)}
            onError={() => {
              setError('Unable to load PDF');
            }}
          />
          {error && (
            <div className="flex items-center justify-center bg-gray-100 p-12 min-h-[600px]">
              <div className="text-center">
                <p className="text-red-600 font-semibold mb-4">{error}</p>
                <a 
                  href={documentUrl} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="text-blue-600 hover:underline font-medium"
                >
                  Open PDF in new tab →
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // For modal mode (fallback)
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-slate-50 to-gray-50">
          <h2 className="text-xl font-bold text-gray-900 truncate">{filename}</h2>
          <button
            onClick={handleDownload}
            className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
            title="Download PDF"
          >
            <Download size={20} className="text-gray-700" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto bg-gray-100">
          {loading && (
            <div className="flex items-center justify-center h-full">
              <div className="flex flex-col items-center gap-4">
                <div className="h-12 w-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                <p className="text-gray-600">Loading PDF...</p>
              </div>
            </div>
          )}

          <iframe
            key={fileId}
            src={documentUrl}
            className="w-full h-full"
            title={filename}
            onLoad={() => setLoading(false)}
          />
        </div>
      </div>
    </div>
  );
};

export default PDFViewer;
