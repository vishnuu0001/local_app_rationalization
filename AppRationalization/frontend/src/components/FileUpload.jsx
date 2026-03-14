import React, { useState, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadInfrastructure, getUploadedFiles, deleteFile } from '../services/api';
import { useAppStore } from '../store';
import { toast } from 'react-toastify';
import { Eye, Trash2 } from 'lucide-react';
import FileViewer from './FileViewer';
import DiscoveredApplicationsTable from './DiscoveredApplicationsTable';

const FileUpload = () => {
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [showPDFViewer, setShowPDFViewer] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [previewingFile, setPreviewingFile] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [showDiscoveredApps, setShowDiscoveredApps] = useState(null);
  const previewRef = useRef(null);
  const tableRef = useRef(null);
  const addUploadedFile = useAppStore((state) => state.addUploadedFile);
  const clearCorrelationData = useAppStore((state) => state.clearCorrelationData);

  // Load uploaded files on component mount
  useEffect(() => {
    fetchUploadedFiles();
  }, []);

  // Auto-scroll to preview when it opens
  useEffect(() => {
    if (showPDFViewer && previewRef.current) {
      setTimeout(() => {
        previewRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, [showPDFViewer]);

  // Auto-scroll to discovered apps table when it opens
  useEffect(() => {
    if (showDiscoveredApps && tableRef.current) {
      setTimeout(() => {
        tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, [showDiscoveredApps]);

  const fetchUploadedFiles = async () => {
    try {
      const response = await getUploadedFiles();
      const files = Array.isArray(response?.data?.files) ? response.data.files : [];
      const infraFiles = files.filter(f => f.type === 'Infrastructure');
      setUploadedFiles(infraFiles);

      if (!Array.isArray(response?.data?.files)) {
        console.error('Unexpected files response shape:', response?.data);
      }
    } catch (error) {
      console.error('Error fetching files:', error);
      toast.error('Unable to fetch uploaded files. Please verify API routing configuration.');
      setUploadedFiles([]);
    }
  };

  const onDrop = async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;
    setSelectedFile(acceptedFiles[0]);
  };

  const handleAssess = async () => {
    if (!selectedFile) {
      toast.warning('Please select a file first');
      return;
    }

    setUploading(true);
    try {
      const response = await uploadInfrastructure(selectedFile);
      addUploadedFile(response.data);
      const message = response.data.is_update 
        ? `${selectedFile.name} updated successfully (replaced previous version)`
        : `${selectedFile.name} assessed successfully`;
      toast.success(message);
      setSelectedFile(null);
      await fetchUploadedFiles();
    } catch (error) {
      const status = error?.response?.status;
      if (status === 405) {
        toast.error('Upload endpoint is not reachable (HTTP 405). Configure IIS /api proxy routing to backend.');
      } else {
        toast.error(error.response?.data?.error || 'Assessment failed');
      }
    } finally {
      setUploading(false);
    }
  };

  const handlePreview = (file) => {
    setPreviewingFile(file);
    setShowPDFViewer(true);
  };

  const handleDeleteFile = async (fileId) => {
    if (!window.confirm('Are you sure you want to delete this file?')) {
      return;
    }

    setDeleting(fileId);
    try {
      const response = await deleteFile(fileId);
      setUploadedFiles(uploadedFiles.filter(f => f.file_id !== fileId));
      const reportCount = response.data.pdf_reports_deleted || 0;
      const message = reportCount > 0 
        ? `File deleted successfully (removed ${reportCount} extracted data entries)`
        : 'File deleted successfully';
      toast.success(message);
      clearCorrelationData();
      // Clear preview if the deleted file was being previewed
      if (previewingFile?.file_id === fileId) {
        setPreviewingFile(null);
        setShowPDFViewer(false);
      }
      // Clear discovered apps if the deleted file was being viewed
      if (showDiscoveredApps === fileId) {
        setShowDiscoveredApps(null);
      }
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to delete file');
    } finally {
      setDeleting(null);
    }
  };


  const handleClosePDFViewer = () => {
    setShowPDFViewer(false);
    setPreviewingFile(null);
  };

  const handleCloseDiscoveredApps = () => {
    setShowDiscoveredApps(null);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.ms-excel.sheet.macroEnabled.12': ['.xlsm']
    },
    disabled: uploading,
  });

  return (
    <div className="min-h-screen bg-white">
      {/* Header Section */}
      <div className="border-b border-gray-200 bg-gradient-to-r from-slate-50 to-gray-50 px-12 py-10">
        <h1 className="text-3xl font-bold text-gray-900">Infra Scan - Corent</h1>
        <p className="text-gray-600 mt-3">Upload your Corent infrastructure analysis file to begin assessment</p>
      </div>

      {/* Content Section */}
      <div className="px-12 py-10">
        {/* File Type Section */}
        <div className="mb-12">
          <label className="text-base font-semibold text-gray-900 block mb-4">
            Select file type:
          </label>
          <div className="flex items-center gap-3 px-6 py-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors">
            <input
              type="radio"
              id="corent"
              name="fileType"
              value="infrastructure"
              checked={true}
              readOnly
              className="w-5 h-5 cursor-pointer accent-blue-600"
            />
            <label htmlFor="corent" className="flex-1 cursor-pointer text-gray-900 font-medium">
              Infrastructure Discovery (Corent)
            </label>
            <span className="text-xs font-semibold bg-slate-700 text-white px-3 py-1.5 rounded-full">
              Primary
            </span>
          </div>
        </div>

        {/* Upload Area */}
        <div className="mb-12">
          <div
            {...getRootProps()}
            className={`relative border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-300 ${
              isDragActive
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-300 hover:border-blue-400 bg-gray-50 hover:bg-blue-50'
            } ${uploading ? 'opacity-60 cursor-not-allowed' : ''}`}
          >
            <input {...getInputProps()} />
            
            <div className="space-y-2">
              <div className="text-4xl opacity-80">📄</div>
              
              {!selectedFile ? (
                <>
                  <div>
                    <p className="text-lg font-semibold text-gray-900">
                      {isDragActive ? 'Drop file here' : 'Drag file here or click to browse'}
                    </p>
                    <p className="text-gray-600 text-sm">PDF & Excel files up to 100MB</p>
                  </div>
                </>
              ) : (
                <div className="space-y-1">
                  <p className="text-base font-semibold text-emerald-600">
                    ✓ File Selected
                  </p>
                  <p className="text-gray-900 font-medium">
                    {selectedFile.name}
                  </p>
                  <p className="text-sm text-gray-600">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4 mb-12">
          <button
            onClick={handleAssess}
            disabled={!selectedFile || uploading}
            className={`flex-1 px-8 py-3 rounded-lg font-semibold transition-all duration-300 flex items-center justify-center gap-2 text-base ${
              selectedFile && !uploading
                ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-md hover:shadow-lg active:shadow-sm'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            {uploading ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                <span>Uploading...</span>
              </>
            ) : (
              <>
                <span>📁</span>
                <span>Upload</span>
              </>
            )}
          </button>
        </div>

        {/* Uploaded Files Table */}
        {uploadedFiles.length > 0 && (
          <div className="mb-12">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Uploaded Files</h3>
            <div className="overflow-x-auto border border-gray-200 rounded-lg">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gradient-to-r from-slate-50 to-gray-50 border-b border-gray-200">
                    <th className="px-6 py-4 text-left font-semibold text-gray-900">File Name</th>
                    <th className="px-6 py-4 text-left font-semibold text-gray-900">Uploaded Date</th>
                    <th className="px-6 py-4 text-left font-semibold text-gray-900">Status</th>
                    <th className="px-6 py-4 text-center font-semibold text-gray-900">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {uploadedFiles.map((file) => (
                    <tr key={file.file_id} className="border-b border-gray-200 hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 font-medium text-gray-900">
                        {file.filename}
                      </td>
                      <td className="px-6 py-4 text-gray-700">
                        {new Date(file.uploaded_at).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700">
                          {file.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            onClick={() => handlePreview(file)}
                            className="inline-flex items-center gap-1 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm"
                            title="Preview file"
                          >
                            <Eye size={16} />
                            Preview
                          </button>

                          <button
                            onClick={() => handleDeleteFile(file.file_id)}
                            disabled={deleting === file.file_id}
                            className="inline-flex items-center gap-1 px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium text-sm disabled:opacity-50"
                            title="Delete file"
                          >
                            {deleting === file.file_id ? (
                              <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                            ) : (
                              <Trash2 size={16} />
                            )}
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Help Section */}
        <div className="bg-gradient-to-r from-slate-50 to-gray-50 border border-gray-200 rounded-lg p-8 max-w-4xl">
          <h3 className="font-semibold text-gray-900 mb-2">About this step</h3>
          <p className="text-gray-700 text-sm leading-relaxed">
            Upload your Corent infrastructure assessment file to analyze your current IT infrastructure, 
            discover servers, applications, and network topology. After upload, you can view and download the PDF file.
          </p>
        </div>
      </div>

      {/* Preview Frame */}
      {showPDFViewer && previewingFile && (
        <div ref={previewRef} className="px-12 py-10 border-t border-gray-200 bg-gray-50">
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <div className="bg-gradient-to-r from-slate-50 to-gray-50 px-8 py-6 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-gray-900">Preview: {previewingFile.filename}</h3>
                <p className="text-sm text-gray-600 mt-1">Uploaded: {new Date(previewingFile.uploaded_at).toLocaleDateString()}</p>
              </div>
              <button
                onClick={handleClosePDFViewer}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors font-medium"
              >
                ✕ Collapse
              </button>
            </div>
            <div className="p-8 min-h-[500px]">
              <FileViewer
                fileId={previewingFile.file_id}
                filename={previewingFile.filename}
                onClose={handleClosePDFViewer}
                isInline={true}
              />
            </div>
          </div>
        </div>
      )}

      {/* Discovered Applications Table */}
      {showDiscoveredApps && (
        <div ref={tableRef} className="px-12 py-10 border-t border-gray-200 bg-white">
          <DiscoveredApplicationsTable
            infrastructureFileId={showDiscoveredApps}
            onClose={handleCloseDiscoveredApps}
          />
        </div>
      )}
    </div>
  );
};

export default FileUpload;
