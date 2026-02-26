import React, { useState, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadIndustryTemplates, getIndustryTemplates, deleteIndustryTemplate, previewIndustryTemplate } from '../services/api';
import { toast } from 'react-toastify';
import { Eye, Trash2 } from 'lucide-react';
import LoadingSpinner from './LoadingSpinner';

const IndustryTemplates = () => {
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedTemplates, setUploadedTemplates] = useState([]);
  const [previewingTemplate, setPreviewingTemplate] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const previewRef = useRef(null);

  // Load uploaded templates on component mount
  useEffect(() => {
    fetchUploadedTemplates();
  }, []);

  // Auto-scroll to preview when it opens
  useEffect(() => {
    if (showPreview && previewRef.current) {
      setTimeout(() => {
        previewRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, [showPreview]);

  const fetchUploadedTemplates = async () => {
    try {
      setLoading(true);
      const response = await getIndustryTemplates();
      setUploadedTemplates(response.data.templates || []);
    } catch (error) {
      console.error('Error fetching templates:', error);
      toast.error('Failed to load templates');
    } finally {
      setLoading(false);
    }
  };

  const onDrop = async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;
    setSelectedFile(acceptedFiles[0]);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      toast.warning('Please select a file first');
      return;
    }

    setUploading(true);
    try {
      const response = await uploadIndustryTemplates(selectedFile);
      const message = `${selectedFile.name} uploaded successfully - ${response.data.records_imported} records imported`;
      toast.success(message);
      setSelectedFile(null);
      await fetchUploadedTemplates();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handlePreview = async (template) => {
    try {
      setPreviewingTemplate(template);
      const response = await previewIndustryTemplate(template.file_id);
      setPreviewData(response.data);
      setShowPreview(true);
    } catch (error) {
      toast.error('Failed to load preview');
    }
  };

  const handleDeleteTemplate = async (templateId, fileId) => {
    if (!window.confirm('Are you sure you want to delete this template and all associated data?')) {
      return;
    }

    setDeleting(fileId);
    try {
      await deleteIndustryTemplate(fileId);
      setUploadedTemplates(uploadedTemplates.filter(t => t.file_id !== fileId));
      toast.success('Template deleted successfully');
      if (previewingTemplate?.file_id === fileId) {
        setPreviewingTemplate(null);
        setShowPreview(false);
      }
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to delete template');
    } finally {
      setDeleting(null);
    }
  };

  const handleClosePreview = () => {
    setShowPreview(false);
    setPreviewingTemplate(null);
    setPreviewData(null);
  };

  const getColumnTypes = () => [
    'APP ID',
    'APP Name',
    'Business owner',
    'Architecture type',
    'Platform Host',
    'Application type',
    'Install type',
    'Capabilities',
  ];

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    disabled: uploading,
  });

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Header Section */}
      <div className="border-b border-gray-200 bg-gradient-to-r from-slate-50 to-gray-50 px-12 py-10">
        <h1 className="text-3xl font-bold text-gray-900">Industry Templates</h1>
        <p className="text-gray-600 mt-3">Upload your Industry Templates file to import application data</p>
      </div>

      {/* Content Section */}
      <div className="flex-1 px-12 py-10 overflow-y-auto">
        {/* Upload Area */}
        <div className="w-full">
          <div className="mb-8 p-8 bg-blue-50 rounded-lg border-2 border-dashed border-blue-300">
            <div {...getRootProps()}>
              <input {...getInputProps()} />
              <div className="text-center">
                <div className="text-5xl mb-4">📁</div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  {isDragActive ? 'Drop your file here' : 'Drag your Excel file here'}
                </h2>
                <p className="text-gray-600 mb-4">or click to browse</p>
                <p className="text-sm text-gray-500">Supports .xlsx and .xls files</p>
              </div>
            </div>
          </div>

          {/* Selected File Info */}
          {selectedFile && (
            <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{selectedFile.name}</p>
                  <p className="text-sm text-gray-500">{(selectedFile.size / 1024).toFixed(2)} KB</p>
                </div>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                >
                  Clear
                </button>
              </div>
            </div>
          )}

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className={`w-full py-3 px-6 rounded-lg font-semibold flex items-center justify-center gap-2 transition-colors ${
              uploading || !selectedFile
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {uploading ? (
              <>
                <span className="animate-spin">⟳</span>
                Uploading...
              </>
            ) : (
              <>
                📤 Upload
              </>
            )}
          </button>
        </div>

        {/* Uploaded Templates Section */}
        <div className="mt-16">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Uploaded Files</h2>

          {uploadedTemplates.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
              <p className="text-gray-500">No templates uploaded yet</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse border border-gray-300">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="border border-gray-300 px-4 py-3 text-left font-semibold">File Name</th>
                    <th className="border border-gray-300 px-4 py-3 text-left font-semibold">Uploaded Date</th>
                    <th className="border border-gray-300 px-4 py-3 text-left font-semibold">Records</th>
                    <th className="border border-gray-300 px-4 py-3 text-left font-semibold">Status</th>
                    <th className="border border-gray-300 px-4 py-3 text-center font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {uploadedTemplates.map((template) => (
                    <tr key={template.file_id} className="hover:bg-gray-50">
                      <td className="border border-gray-300 px-4 py-3">{template.filename}</td>
                      <td className="border border-gray-300 px-4 py-3">
                        {new Date(template.uploaded_at).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="border border-gray-300 px-4 py-3 text-center font-semibold">
                        {template.record_count || 0}
                      </td>
                      <td className="border border-gray-300 px-4 py-3">
                        <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">
                          Ready
                        </span>
                      </td>
                      <td className="border border-gray-300 px-4 py-3 text-center">
                        <div className="flex gap-2 justify-center">
                          <button
                            onClick={() => handlePreview(template)}
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                            title="Preview"
                          >
                            <Eye size={18} />
                          </button>
                          <button
                            onClick={() => handleDeleteTemplate(template.id, template.file_id)}
                            disabled={deleting === template.file_id}
                            className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                            title="Delete"
                          >
                            <Trash2 size={18} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Preview Section */}
        {showPreview && previewData && (
          <div ref={previewRef} className="mt-16 mb-8 bg-white border border-gray-200 rounded-lg">
            {/* Preview Header */}
            <div className="border-b border-gray-200 px-8 py-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">Preview: {previewingTemplate.filename}</h2>
                  <p className="text-sm text-gray-600 mt-1">
                    Uploaded: {new Date(previewingTemplate.uploaded_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </p>
                </div>
                <button
                  onClick={handleClosePreview}
                  className="text-gray-500 hover:text-gray-700 text-lg font-semibold"
                  title="Close Preview"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Search and Info Bar */}
            <div className="px-8 py-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
              <div className="flex-1 max-w-md">
                <input
                  type="text"
                  placeholder="Search records..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <p className="text-sm text-gray-600">
                Showing {previewData.preview_data?.filter((row) =>
                  Object.values(row).some((val) =>
                    val && val.toString().toLowerCase().includes(searchTerm.toLowerCase())
                  )
                ).length || 0} of {previewData.total_records || 0} records
              </p>
            </div>

            {/* Preview Table */}
            <div className="px-8 py-6">
              {previewData.preview_data && previewData.preview_data.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        {getColumnTypes().map((col) => (
                          <th key={col} className="px-4 py-3 text-left font-semibold text-sm text-gray-700">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.preview_data
                        .filter((row) =>
                          Object.values(row).some((val) =>
                            val && val.toString().toLowerCase().includes(searchTerm.toLowerCase())
                          )
                        )
                        .map((row, idx) => (
                          <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm text-gray-900">{row.app_id}</td>
                            <td className="px-4 py-3 text-sm text-gray-900">{row.app_name}</td>
                            <td className="px-4 py-3 text-sm text-gray-700">{row.business_owner || '-'}</td>
                            <td className="px-4 py-3 text-sm text-gray-700">{row.architecture_type || '-'}</td>
                            <td className="px-4 py-3 text-sm text-gray-700">{row.platform_host || '-'}</td>
                            <td className="px-4 py-3 text-sm text-gray-700">{row.application_type || '-'}</td>
                            <td className="px-4 py-3 text-sm text-gray-700">{row.install_type || '-'}</td>
                            <td className="px-4 py-3 text-sm text-gray-700">{row.capabilities || '-'}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">No preview data available</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default IndustryTemplates;
