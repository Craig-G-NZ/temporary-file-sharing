/**
 * JavaScript for admin upload page
 */

// Run after DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const progressContainer = document.getElementById('uploadProgress');
    const progressBar = progressContainer.querySelector('.progress-bar');
    const progressText = document.getElementById('progressText');
    const uploadStatus = document.getElementById('uploadStatus');
    const uploadBtn = document.getElementById('uploadBtn');
    const backBtn = document.getElementById('backBtn');
    const uploadForm = document.getElementById('uploadForm');
    const filesInput = document.getElementById('files');
    const fileList = document.getElementById('fileList');

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    // Show selected files
    filesInput.addEventListener('change', function() {
        fileList.innerHTML = '';
        if (this.files.length > 0) {
            const ul = document.createElement('ul');
            ul.className = 'list-group';
            Array.from(this.files).forEach(file => {
                const li = document.createElement('li');
                li.className = 'list-group-item d-flex justify-content-between align-items-center';
                li.innerHTML = `
                    <span><i class="fas fa-file"></i> ${file.name}</span>
                    <span class="badge bg-primary rounded-pill">${formatFileSize(file.size)}</span>
                `;
                ul.appendChild(li);
            });
            fileList.appendChild(ul);
        }
    });

    // Helper to request a new share token from the backend
    async function getShareToken(recipientEmail, retentionHours) {
        const resp = await fetch('/admin/request-share-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipient_email: recipientEmail, retention_hours: retentionHours })
        });
        const data = await resp.json();
        return data.token;
    }

    // Handle form submission (chunked upload, all files in one share)
    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const files = filesInput.files;
        const recipientEmail = document.getElementById('recipient_email').value;
        const retentionHours = 24; // Or get from form if needed
        const chunkSize = 5 * 1024 * 1024; // 5MB

        if (!files.length) return;

        // 1. Get a share token for this upload session
        const shareToken = await getShareToken(recipientEmail, retentionHours);

        progressContainer.classList.remove('d-none');
        progressContainer.style.display = 'block';
        progressContainer.offsetHeight;
        uploadBtn.disabled = true;
        if (backBtn) backBtn.classList.add('d-none');
        progressBar.style.width = '0%';
        progressBar.classList.remove('bg-success', 'bg-danger');
        progressBar.classList.add('progress-bar-striped', 'progress-bar-animated');
        progressText.textContent = '0%';
        uploadStatus.textContent = 'Preparing upload...';
        uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';

        // Helper to generate a simple fileId (hash)
        function getFileId(file) {
            return (
                file.name + '-' + file.size + '-' + file.lastModified
            ).replace(/[^a-zA-Z0-9]/g, '');
        }

        // Upload a single file in chunks
        function uploadFileChunked(file, fileIndex, totalFiles, onComplete) {
            const fileId = getFileId(file);
            const totalChunks = Math.ceil(file.size / chunkSize);
            let chunkNumber = 1;
            let offset = 0;

            function uploadNextChunk() {
                const end = Math.min(offset + chunkSize, file.size);
                const chunk = file.slice(offset, end);
                const formData = new FormData();
                formData.append('chunk', chunk);
                formData.append('chunkNumber', chunkNumber);
                formData.append('totalChunks', totalChunks);
                formData.append('fileId', fileId);
                formData.append('filename', file.name);
                formData.append('share_token', shareToken); // <--- Pass the share token

                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/admin/upload-chunk');
                xhr.onload = function() {
                    if (xhr.status === 200) {
                        // Update progress
                        const percent = Math.round(((fileIndex + (chunkNumber / totalChunks)) / totalFiles) * 100);
                        progressBar.style.width = percent + '%';
                        progressText.textContent = percent + '%';
                        uploadStatus.textContent = `Uploading ${file.name} (${chunkNumber}/${totalChunks})`;

                        if (chunkNumber < totalChunks) {
                            chunkNumber++;
                            offset += chunkSize;
                            uploadNextChunk();
                        } else {
                            onComplete(xhr.responseText);
                        }
                    } else {
                        progressBar.classList.add('bg-danger');
                        uploadStatus.textContent = 'Upload failed!';
                        uploadBtn.disabled = false;
                    }
                };
                xhr.onerror = function() {
                    progressBar.classList.add('bg-danger');
                    uploadStatus.textContent = 'Upload failed!';
                    uploadBtn.disabled = false;
                };
                xhr.send(formData);
            }
            uploadNextChunk();
        }

        // Upload all files sequentially
        let currentFile = 0;
        function uploadNextFile() {
            if (currentFile < files.length) {
                uploadFileChunked(files[currentFile], currentFile, files.length, function() {
                    currentFile++;
                    uploadNextFile();
                });
            } else {
                // All files uploaded, now finalize the share (send email)
                fetch('/admin/finalize-share', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ share_token: shareToken })
                })
                .then(response => response.json())
                .then(data => {
                    progressBar.style.width = '100%';
                    progressText.textContent = '100%';
                    progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
                    progressBar.classList.add('bg-success');
                    if (data.success) {
                        uploadStatus.textContent = 'Upload complete! Email sent. Redirecting...';
                    } else {
                        uploadStatus.textContent = 'Upload complete! (Email failed)';
                    }
                    setTimeout(function() {
                        const adminFilesUrl = progressContainer.dataset.redirectUrl || '/admin/files';
                        window.location.href = adminFilesUrl;
                    }, 1200);
                })
                .catch(() => {
                    uploadStatus.textContent = 'Upload complete! (Email failed)';
                    setTimeout(function() {
                        const adminFilesUrl = progressContainer.dataset.redirectUrl || '/admin/files';
                        window.location.href = adminFilesUrl;
                    }, 1200);
                });
            }
        }
        uploadNextFile();
    });
});
