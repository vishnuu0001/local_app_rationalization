import create from 'zustand';

export const useAppStore = create((set) => ({
  uploadedFiles: [],
  analyses: [],
  capabilities: [],
  scenarios: [],
  currentAnalysis: null,
  correlationDataVersion: 0,
  
  setUploadedFiles: (files) => set({ uploadedFiles: files }),
  addUploadedFile: (file) => set((state) => ({
    uploadedFiles: [...state.uploadedFiles, file]
  })),
  
  setAnalyses: (analyses) => set({ analyses }),
  addAnalysis: (analysis) => set((state) => ({
    analyses: [...state.analyses, analysis]
  })),
  
  setCapabilities: (capabilities) => set({ capabilities }),
  setScenarios: (scenarios) => set({ scenarios }),
  setCurrentAnalysis: (analysis) => set({ currentAnalysis: analysis }),
  clearCorrelationData: () => set((state) => ({
    correlationDataVersion: state.correlationDataVersion + 1
  })),
}));
