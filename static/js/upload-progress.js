// ═══════════════════════════════════════════════════════
//  UPLOAD PROGRESS — Files upload on select, not on submit
// ═══════════════════════════════════════════════════════

(function () {
    'use strict';

    var form = document.getElementById('productForm');
    if (!form) return;

    var fileInputs = form.querySelectorAll('input[type="file"]');
    var uploadedFiles = {};

    // ═══════════════════════════════════════════════════════
    //  PROGRESS BARS UNDER EACH FILE INPUT
    // ═══════════════════════════════════════════════════════
    fileInputs.forEach(function (input) {
        var wrapper = document.createElement('div');
        wrapper.className = 'upload-progress-wrapper';
        wrapper.innerHTML =
            '<div class="upload-progress-bar">' +
                '<div class="upload-progress-fill" data-fill></div>' +
            '</div>' +
            '<div class="upload-progress-info">' +
                '<span class="upload-progress-label" data-label>No file selected</span>' +
                '<span class="upload-progress-percent" data-percent></span>' +
            '</div>' +
            '<button type="button" class="upload-remove-btn" data-remove style="display:none;">' +
                '<i class="fas fa-times"></i> Remove' +
            '</button>';
        wrapper.style.display = 'none';

        input.parentNode.insertBefore(wrapper, input.nextSibling);

        var fill = wrapper.querySelector('[data-fill]');
        var label = wrapper.querySelector('[data-label]');
        var percent = wrapper.querySelector('[data-percent]');
        var removeBtn = wrapper.querySelector('[data-remove]');

        // Store refs for later access
        input._progressRefs = {
            wrapper: wrapper,
            fill: fill,
            label: label,
            percent: percent,
            removeBtn: removeBtn
        };

        // ── Remove button ──
        removeBtn.addEventListener('click', function () {
            var existing = uploadedFiles[input.name];
            if (existing && existing.tempPath) {
                fetch('/api/admin/cleanup-temp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ temp_path: existing.tempPath })
                }).catch(function () {});
            }

            delete uploadedFiles[input.name];
            input.value = '';
            wrapper.style.display = 'none';
            fill.style.width = '0%';
            fill.className = 'upload-progress-fill';
            percent.textContent = '';
            removeBtn.style.display = 'none';
        });

        // ── On file select → upload immediately ──
        input.addEventListener('change', function () {
            var file = input.files[0];
            if (!file) return;

            var sizeMB = (file.size / (1024 * 1024)).toFixed(1);
            wrapper.style.display = '';
            label.textContent = file.name + ' (' + sizeMB + ' MB)';
            fill.style.width = '0%';
            fill.className = 'upload-progress-fill';
            percent.textContent = '0%';
            percent.className = 'upload-progress-percent';
            removeBtn.style.display = 'none';

            // Upload immediately
            var formData = new FormData();
            formData.append('file', file);

            var csrfInput = form.querySelector('input[name="csrf_token"]');
            if (csrfInput) {
                formData.append('csrf_token', csrfInput.value);
            }

            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/admin/upload-temp', true);

            xhr.upload.addEventListener('progress', function (e) {
                if (e.lengthComputable) {
                    var pct = Math.round((e.loaded / e.total) * 100);
                    fill.style.width = pct + '%';
                    percent.textContent = pct + '%';
                }
            });

            xhr.addEventListener('load', function () {
                try {
                    var result = JSON.parse(xhr.responseText);
                    if (xhr.status >= 200 && xhr.status < 400 && result.success) {
                        fill.className = 'upload-progress-fill complete';
                        percent.textContent = 'Ready';
                        percent.className = 'upload-progress-percent complete';
                        removeBtn.style.display = '';

                        uploadedFiles[input.name] = {
                            tempPath: result.temp_path,
                            originalName: result.original_name,
                            size: result.size
                        };
                    } else {
                        fill.className = 'upload-progress-fill error';
                        percent.textContent = result.error || 'Error ' + xhr.status;
                        percent.className = 'upload-progress-percent error';
                        console.error('Upload failed:', result);
                    }
                } catch (parseErr) {
                    fill.className = 'upload-progress-fill error';
                    percent.textContent = 'Error';
                    percent.className = 'upload-progress-percent error';
                    console.error('Upload response parse error:', parseErr, xhr.responseText);
                }
            });

            xhr.addEventListener('error', function () {
                fill.className = 'upload-progress-fill error';
                percent.textContent = 'Network Error';
                percent.className = 'upload-progress-percent error';
            });

            xhr.send(formData);
        });
    });

    // ═══════════════════════════════════════════════════════
    //  FORM SUBMIT — send temp paths instead of files
    // ═══════════════════════════════════════════════════════
    form.addEventListener('submit', function (e) {
        // Check if any file is still uploading
        var stillUploading = false;
        fileInputs.forEach(function (input) {
            if (input._progressRefs) {
                var fillEl = input._progressRefs.fill;
                var wrapper = input._progressRefs.wrapper;
                if (wrapper.style.display !== 'none' &&
                    !fillEl.classList.contains('complete') &&
                    !fillEl.classList.contains('error') &&
                    fillEl.style.width !== '0%') {
                    stillUploading = true;
                }
            }
        });

        if (stillUploading) {
            e.preventDefault();
            alert('Please wait for files to finish uploading.');
            return;
        }

        // Inject hidden inputs with temp paths
        Object.keys(uploadedFiles).forEach(function (fieldName) {
            var data = uploadedFiles[fieldName];
            if (data && data.tempPath) {
                var hidden = document.createElement('input');
                hidden.type = 'hidden';
                hidden.name = fieldName + '_temp_path';
                hidden.value = data.tempPath;
                form.appendChild(hidden);

                // Remove actual file so it doesn't re-upload
                var realInput = form.querySelector('input[name="' + fieldName + '"]');
                if (realInput) realInput.value = '';
            }
        });
    });

})();