/* filepath: c:\Users\USER\Documents\Raterx\klinchainx\static\js\main.js */
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const fileUploadContainer = document.getElementById('file-upload-container');
    const fileUploadInput = document.getElementById('file-upload');
    const uploadArea = document.getElementById('upload-area');
    const fileDetails = document.getElementById('file-details');
    const fileName = document.getElementById('file-name');
    const fileSize = document.getElementById('file-size');
    const removeFileBtn = document.getElementById('remove-file');
    const optionsContainer = document.getElementById('options-container');
    const startProcessingBtn = document.getElementById('start-processing');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressStatus = document.getElementById('progress-status');
    const resultsContainer = document.getElementById('results-container');
    const downloadBtn = document.getElementById('download-btn');
    const newFileBtn = document.getElementById('new-file-btn');
    const previewContainer = document.getElementById('preview-container');
    const togglePreviewBtn = document.getElementById('toggle-preview');
    const previewContent = document.getElementById('preview-content');
    const errorContainer = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');
    const retryBtn = document.getElementById('retry-btn');
    
    // Options elements
    const outputFormat = document.getElementById('output-format');
    const extractionMethod = document.getElementById('extraction-method');
    const includeMetadata = document.getElementById('include-metadata');
    const textOnly = document.getElementById('text-only');
    
    // File data
    let currentFile = null;
    let currentTaskId = null;
    let statusCheckInterval = null;
    
    // Drag and drop functionality
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileUploadContainer.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        fileUploadContainer.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        fileUploadContainer.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        fileUploadContainer.classList.add('dragover');
    }
    
    function unhighlight() {
        fileUploadContainer.classList.remove('dragover');
    }
    
    fileUploadContainer.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            handleFiles(files);
        }
    }
    
    // File input change handler
    fileUploadInput.addEventListener('change', function(e) {
        if (this.files.length > 0) {
            handleFiles(this.files);
        }
    });
    
    // Process the selected file
    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            
            // Check if it's a PDF
            if (!file.type.match('application/pdf')) {
                showError('Please select a PDF file.');
                return;
            }
            
            // Check file size (max 10MB)
            if (file.size > 10 * 1024 * 1024) {
                showError('File size exceeds the maximum limit of 10MB.');
                return;
            }
            
            currentFile = file;
            displayFileDetails(file);
            showOptions();
        }
    }
    
    // Display file details
    function displayFileDetails(file) {
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        uploadArea.classList.add('hidden');
        fileDetails.classList.remove('hidden');
    }
    
    // Format file size
    function formatFileSize(bytes) {
        if (bytes < 1024) {
            return bytes + ' bytes';
        } else if (bytes < 1024 * 1024) {
            return (bytes / 1024).toFixed(1) + ' KB';
        } else {
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        }
    }
    
    // Show options panel
    function showOptions() {
        optionsContainer.classList.remove('hidden');
    }
    
    // Remove selected file
    removeFileBtn.addEventListener('click', function() {
        resetFileSelection();
    });
    
    // Reset file selection
    function resetFileSelection() {
        currentFile = null;
        fileUploadInput.value = '';
        fileDetails.classList.add('hidden');
        uploadArea.classList.remove('hidden');
        optionsContainer.classList.add('hidden');
    }
    
    // Start processing button
    startProcessingBtn.addEventListener('click', function() {
        if (!currentFile) {
            showError('Please select a PDF file first.');
            return;
        }
        
        // Show progress UI
        optionsContainer.classList.add('hidden');
        progressContainer.classList.remove('hidden');
        errorContainer.classList.add('hidden');
        
        // Get options
        const options = {
            output_format: outputFormat.value,
            extraction_method: extractionMethod.value,
            include_metadata: includeMetadata.checked,
            text_only: textOnly.checked
        };
        
        // Upload and process file
        uploadAndProcessFile(currentFile, options);
    });
    
    // Upload and process the file
    function uploadAndProcessFile(file, options) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('output_format', options.output_format);
        formData.append('extraction_method', options.extraction_method);
        formData.append('include_metadata', options.include_metadata);
        formData.append('text_only', options.text_only);
        
        fetch('/api/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.detail || 'Failed to upload file');
                });
            }
            return response.json();
        })
        .then(data => {
            currentTaskId = data.task_id;
            startProgressCheck(currentTaskId);
        })
        .catch(error => {
            showError(error.message || 'An error occurred during upload');
        });
    }
    
    // Check task progress
    function startProgressCheck(taskId) {
        // Clear any existing interval
        if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
        }
        
        // Set progress bar to initial state
        updateProgress(10, 'Processing started');
        
        // Check status every 2 seconds
        statusCheckInterval = setInterval(() => {
            fetch(`/api/status/${taskId}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Failed to get task status');
                    }
                    return response.json();
                })
                .then(data => {
                    updateProgress(data.progress, data.message);
                    
                    if (data.status === 'completed') {
                        clearInterval(statusCheckInterval);
                        showResults(data);
                    } else if (data.status === 'failed') {
                        clearInterval(statusCheckInterval);
                        showError(data.message || 'Processing failed');
                    }
                })
                .catch(error => {
                    console.error('Error checking task status:', error);
                });
        }, 2000);
    }
    
    // Update progress UI
    function updateProgress(percent, statusText) {
        progressBar.style.width = `${percent}%`;
        progressStatus.textContent = statusText || 'Processing...';
    }
    
    // Show results UI
    function showResults(data) {
        progressContainer.classList.add('hidden');
        resultsContainer.classList.remove('hidden');
        
        // Set download button action
        downloadBtn.onclick = () => {
            // Temporarily show downloading state
            const originalButtonText = downloadBtn.innerHTML;
            downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Downloading...';
            
            // Start download
            window.location.href = `/api/download/${data.task_id}`;
            
            // Show brief "Downloaded" flash message, then restore button
            setTimeout(() => {
                downloadBtn.innerHTML = '<i class="fas fa-check-circle mr-2"></i> Downloaded!';
                
                // Return button to original state after showing message
                setTimeout(() => {
                    downloadBtn.innerHTML = originalButtonText;
                }, 1500);
            }, 1000);
        };
        
        // Load preview
        loadPreview(data.task_id, outputFormat.value);
    }
    
    // Load preview content
    function loadPreview(taskId, format) {
        previewContent.innerHTML = '<div class="flex justify-center py-8"><div class="loading-spinner"></div></div>';
        
        // For CSV and JSON formats, we can show a preview
        if (format === 'csv' || format === 'json') {
            fetch(`/api/download/${taskId}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Failed to load preview');
                    }
                    
                    if (format === 'csv') {
                        return response.text().then(text => {
                            displayCsvPreview(text);
                        });
                    } else if (format === 'json') {
                        return response.json().then(json => {
                            displayJsonPreview(json);
                        });
                    }
                })
                .catch(error => {
                    previewContent.innerHTML = `<p class="text-red-500">Error loading preview: ${error.message}</p>`;
                });
        } else {
            // For formats like Parquet that can't easily be previewed
            previewContent.innerHTML = '<p class="text-center py-4">Preview not available for this format. Please download the file to view the results.</p>';
        }
    }
    
    // Display CSV preview
    function displayCsvPreview(csvText) {
        try {
            // Parse CSV (simple implementation, doesn't handle all cases)
            const lines = csvText.split('\n');
            if (lines.length === 0) {
                throw new Error('No data found');
            }
            
            // Get headers and rows
            const headers = lines[0].split(',');
            
            let tableHtml = '<div class="overflow-x-auto">';
            tableHtml += '<table class="min-w-full divide-y divide-gray-200">';
            
            // Header row
            tableHtml += '<thead class="bg-gray-50">';
            tableHtml += '<tr>';
            headers.forEach(header => {
                tableHtml += `<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">${header.replace(/"/g, '')}</th>`;
            });
            tableHtml += '</tr>';
            tableHtml += '</thead>';
            
            // Table body
            tableHtml += '<tbody class="bg-white divide-y divide-gray-200">';
            
            // Show up to 10 rows
            const rowsToShow = Math.min(lines.length, 11);
            for (let i = 1; i < rowsToShow; i++) {
                if (!lines[i].trim()) continue;
                
                tableHtml += '<tr>';
                const cells = lines[i].split(',');
                cells.forEach(cell => {
                    tableHtml += `<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${cell.replace(/"/g, '')}</td>`;
                });
                tableHtml += '</tr>';
            }
            
            tableHtml += '</tbody>';
            tableHtml += '</table>';
            
            // If there are more rows, show a message
            if (lines.length > 11) {
                tableHtml += `<p class="text-center text-gray-500 mt-4">Showing 10 of ${lines.length - 1} rows</p>`;
            }
            
            tableHtml += '</div>';
            
            previewContent.innerHTML = tableHtml;
            
        } catch (error) {
            previewContent.innerHTML = `<p class="text-red-500">Error parsing CSV: ${error.message}</p>`;
        }
    }
    
    // Display JSON preview
    function displayJsonPreview(jsonData) {
        try {
            // Pretty print JSON
            const formattedJson = JSON.stringify(jsonData, null, 2);
            previewContent.innerHTML = `<pre class="text-sm text-gray-800 overflow-x-auto">${formattedJson}</pre>`;
            
            // If it's very large, truncate it
            if (formattedJson.length > 5000) {
                previewContent.innerHTML = `<pre class="text-sm text-gray-800 overflow-x-auto">${formattedJson.substring(0, 5000)}...</pre>`;
                previewContent.innerHTML += '<p class="text-center text-gray-500 mt-4">Preview truncated. Download the full file to view all data.</p>';
            }
        } catch (error) {
            previewContent.innerHTML = `<p class="text-red-500">Error parsing JSON: ${error.message}</p>`;
        }
    }
    
    // Toggle preview visibility
    togglePreviewBtn.addEventListener('click', function() {
        const icon = this.querySelector('i');
        if (previewContent.classList.contains('hidden')) {
            previewContent.classList.remove('hidden');
            icon.classList.remove('rotate-180');
        } else {
            previewContent.classList.add('hidden');
            icon.classList.add('rotate-180');
        }
    });
    
    // Process new file button
    newFileBtn.addEventListener('click', function() {
        resetFileSelection();
        resultsContainer.classList.add('hidden');
    });
    
    // Show error message
    function showError(message) {
        errorMessage.textContent = message;
        errorContainer.classList.remove('hidden');
        progressContainer.classList.add('hidden');
        
        // Add shake animation
        errorContainer.classList.add('shake');
        setTimeout(() => {
            errorContainer.classList.remove('shake');
        }, 500);
    }
    
    // Retry button
    retryBtn.addEventListener('click', function() {
        errorContainer.classList.add('hidden');
        resetFileSelection();
    });
    
    // Clean up on page unload
    window.addEventListener('beforeunload', function() {
        if (currentTaskId) {
            // Attempt to clean up the task
            fetch(`/api/tasks/${currentTaskId}`, {
                method: 'DELETE',
                keepalive: true
            }).catch(error => {
                console.error('Error cleaning up task:', error);
            });
        }
    });
});