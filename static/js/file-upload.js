/**
 * Modern File Upload System with Drag & Drop
 * Supports multiple files, auto-detection, and progress tracking
 */

class FileUploadManager {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            maxFileSize: 50 * 1024 * 1024, // 50MB
            allowedTypes: ['application/pdf'],
            autoProcess: true,
            multiple: true,
            ...options
        };
        
        this.uploadQueue = [];
        this.isUploading = false;
        
        this.init();
    }
    
    init() {
        this.createUploadInterface();
        this.setupEventListeners();
    }
    
    createUploadInterface() {
        this.container.innerHTML = `
            <div class="file-upload-area" id="uploadArea">
                <div class="upload-content">
                    <div class="upload-icon">
                        <i class="bi bi-cloud-upload fs-1 text-primary"></i>
                    </div>
                    <h5 class="upload-title">Drop files here or click to browse</h5>
                    <p class="upload-subtitle text-muted">
                        Supports PDF files up to 50MB. Payslips and runsheets will be auto-detected.
                    </p>
                    <button type="button" class="btn btn-primary" id="browseBtn">
                        <i class="bi bi-folder2-open"></i> Browse Files
                    </button>
                </div>
                
                <input type="file" id="fileInput" multiple accept=".pdf" style="display: none;">
                
                <div class="upload-options mt-3" style="display: none;">
                    <div class="row g-2">
                        <div class="col-md-4">
                            <select class="form-select" id="fileTypeSelect">
                                <option value="auto">Auto-detect type</option>
                                <option value="payslips">Payslips</option>
                                <option value="runsheets">Runsheets</option>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="autoProcessCheck" checked>
                                <label class="form-check-label" for="autoProcessCheck">
                                    Auto-process after upload
                                </label>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <button type="button" class="btn btn-success w-100" id="uploadBtn" disabled>
                                <i class="bi bi-upload"></i> Upload Files
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="upload-queue mt-3" id="uploadQueue" style="display: none;">
                <h6>Upload Queue</h6>
                <div class="queue-items" id="queueItems"></div>
            </div>
            
            <div class="upload-progress mt-3" id="uploadProgress" style="display: none;">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span>Uploading files...</span>
                    <span id="progressText">0%</span>
                </div>
                <div class="progress">
                    <div class="progress-bar" id="progressBar" style="width: 0%"></div>
                </div>
            </div>
            
            <div class="upload-results mt-3" id="uploadResults" style="display: none;">
                <div class="results-content" id="resultsContent"></div>
            </div>
        `;
    }
    
    setupEventListeners() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const browseBtn = document.getElementById('browseBtn');
        const uploadBtn = document.getElementById('uploadBtn');
        
        // Drag and drop events
        uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
        uploadArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
        uploadArea.addEventListener('drop', this.handleDrop.bind(this));
        
        // Click to browse
        browseBtn.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('click', (e) => {
            if (e.target === uploadArea || e.target.closest('.upload-content')) {
                fileInput.click();
            }
        });
        
        // File selection
        fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        
        // Upload button
        uploadBtn.addEventListener('click', this.startUpload.bind(this));
    }
    
    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        document.getElementById('uploadArea').classList.add('drag-over');
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        document.getElementById('uploadArea').classList.remove('drag-over');
    }
    
    handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        document.getElementById('uploadArea').classList.remove('drag-over');
        
        const files = Array.from(e.dataTransfer.files);
        this.addFilesToQueue(files);
    }
    
    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.addFilesToQueue(files);
    }
    
    addFilesToQueue(files) {
        const validFiles = files.filter(file => this.validateFile(file));
        
        if (validFiles.length === 0) {
            this.showError('No valid PDF files selected');
            return;
        }
        
        this.uploadQueue = [...this.uploadQueue, ...validFiles];
        this.updateQueueDisplay();
        this.showUploadOptions();
    }
    
    validateFile(file) {
        // Check file type
        if (!this.options.allowedTypes.includes(file.type) && !file.name.toLowerCase().endsWith('.pdf')) {
            this.showError(`Invalid file type: ${file.name}. Only PDF files are allowed.`);
            return false;
        }
        
        // Check file size
        if (file.size > this.options.maxFileSize) {
            this.showError(`File too large: ${file.name}. Maximum size is 50MB.`);
            return false;
        }
        
        return true;
    }
    
    updateQueueDisplay() {
        const queueContainer = document.getElementById('uploadQueue');
        const queueItems = document.getElementById('queueItems');
        const uploadBtn = document.getElementById('uploadBtn');
        
        if (this.uploadQueue.length === 0) {
            queueContainer.style.display = 'none';
            uploadBtn.disabled = true;
            return;
        }
        
        queueContainer.style.display = 'block';
        uploadBtn.disabled = false;
        
        queueItems.innerHTML = this.uploadQueue.map((file, index) => `
            <div class="queue-item d-flex justify-content-between align-items-center p-2 border rounded mb-2">
                <div class="file-info">
                    <div class="file-name fw-semibold">${file.name}</div>
                    <div class="file-details text-muted small">
                        ${this.formatFileSize(file.size)} • ${this.detectFileType(file.name)}
                    </div>
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="fileUploader.removeFromQueue(${index})">
                    <i class="bi bi-x"></i>
                </button>
            </div>
        `).join('');
    }
    
    removeFromQueue(index) {
        this.uploadQueue.splice(index, 1);
        this.updateQueueDisplay();
        
        if (this.uploadQueue.length === 0) {
            this.hideUploadOptions();
        }
    }
    
    showUploadOptions() {
        document.querySelector('.upload-options').style.display = 'block';
    }
    
    hideUploadOptions() {
        document.querySelector('.upload-options').style.display = 'none';
    }
    
    async startUpload() {
        if (this.isUploading || this.uploadQueue.length === 0) return;
        
        this.isUploading = true;
        this.showProgress();
        
        const fileType = document.getElementById('fileTypeSelect').value;
        const autoProcess = document.getElementById('autoProcessCheck').checked;
        
        try {
            const formData = new FormData();
            
            this.uploadQueue.forEach(file => {
                formData.append('files', file);
            });
            
            formData.append('type', fileType === 'auto' ? 'general' : fileType);
            formData.append('auto_process', autoProcess.toString());
            
            const response = await fetch('/api/upload/files', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showResults(result);
                this.clearQueue();
            } else {
                this.showError(result.error || 'Upload failed');
            }
            
        } catch (error) {
            this.showError(`Upload failed: ${error.message}`);
        } finally {
            this.isUploading = false;
            this.hideProgress();
        }
    }
    
    showProgress() {
        document.getElementById('uploadProgress').style.display = 'block';
        // Simulate progress for now - in a real implementation, you'd track actual progress
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 20;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
            }
            this.updateProgress(progress);
        }, 200);
    }
    
    updateProgress(percent) {
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        
        progressBar.style.width = `${percent}%`;
        progressText.textContent = `${Math.round(percent)}%`;
    }
    
    hideProgress() {
        document.getElementById('uploadProgress').style.display = 'none';
    }
    
    showResults(result) {
        const resultsContainer = document.getElementById('uploadResults');
        const resultsContent = document.getElementById('resultsContent');
        
        let html = `
            <div class="alert alert-success">
                <i class="bi bi-check-circle"></i>
                <strong>Upload Complete!</strong> ${result.uploaded_files.length} files uploaded successfully.
            </div>
        `;
        
        if (result.processing_results && result.processing_results.length > 0) {
            html += `
                <div class="processing-results mt-3">
                    <h6>Processing Results:</h6>
                    <div class="list-group">
            `;
            
            result.processing_results.forEach(item => {
                const statusClass = item.result?.success ? 'success' : 'danger';
                const statusIcon = item.result?.success ? 'check-circle' : 'x-circle';
                
                html += `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between align-items-center">
                            <span>${item.file}</span>
                            <span class="badge bg-${statusClass}">
                                <i class="bi bi-${statusIcon}"></i>
                                ${item.result?.success ? 'Processed' : 'Failed'}
                            </span>
                        </div>
                        ${item.result?.error ? `<small class="text-danger">${item.result.error}</small>` : ''}
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        }
        
        if (result.errors && result.errors.length > 0) {
            html += `
                <div class="alert alert-warning mt-3">
                    <strong>Warnings:</strong>
                    <ul class="mb-0 mt-2">
                        ${result.errors.map(error => `<li>${error}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        resultsContent.innerHTML = html;
        resultsContainer.style.display = 'block';
        
        // Trigger callback if provided
        if (this.options.onUploadComplete) {
            this.options.onUploadComplete(result);
        }
        
        // If on runsheets page, reload the data
        if (typeof loadRunSheetsList === 'function') {
            setTimeout(() => {
                loadRunSheetsList();
                loadRunSheetsSummary();
            }, 1000);
        }
    }
    
    showError(message) {
        const resultsContainer = document.getElementById('uploadResults');
        const resultsContent = document.getElementById('resultsContent');
        
        resultsContent.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                <strong>Error:</strong> ${message}
            </div>
        `;
        
        resultsContainer.style.display = 'block';
    }
    
    clearQueue() {
        this.uploadQueue = [];
        this.updateQueueDisplay();
        this.hideUploadOptions();
        document.getElementById('fileInput').value = '';
    }
    
    detectFileType(filename) {
        const name = filename.toLowerCase();
        if (name.includes('payslip') || name.includes('saser')) {
            return 'Payslip';
        } else if (name.includes('runsheet') || name.includes('run')) {
            return 'Runsheet';
        }
        return 'Unknown';
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Additional utility functions for hybrid sync
class HybridSyncManager {
    static async scanDirectories() {
        try {
            const response = await fetch('/api/upload/scan-directories');
            const result = await response.json();
            
            if (result.success) {
                return result;
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Directory scan failed:', error);
            throw error;
        }
    }
    
    static async processLocalFiles(options = {}) {
        try {
            const response = await fetch('/api/upload/process-local', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(options)
            });
            
            const result = await response.json();
            
            if (result.success) {
                return result;
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Local processing failed:', error);
            throw error;
        }
    }
    
    static async hybridSync(mode = 'smart') {
        try {
            const response = await fetch('/api/upload/hybrid-sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ mode })
            });
            
            const result = await response.json();
            
            if (result.success) {
                return result;
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Hybrid sync failed:', error);
            throw error;
        }
    }
}

// Global instance
let fileUploader = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if upload container exists
    if (document.getElementById('fileUploadContainer')) {
        fileUploader = new FileUploadManager('fileUploadContainer');
    }
});

// Export for use in other modules
window.FileUploadManager = FileUploadManager;
window.HybridSyncManager = HybridSyncManager;
