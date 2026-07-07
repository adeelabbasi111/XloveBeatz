// ═══════════════════════════════════════════════════════
//  UPLOAD PROGRESS — File input bars + submit modal
// ═══════════════════════════════════════════════════════

(function () {
    'use strict';

    var form = document.getElementById('productForm');
    if (!form) return;

    var fileInputs = form.querySelectorAll('input[type="file"]');
    var progressMap = {};

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
            '</div>';
        wrapper.style.display = 'none';

        input.parentNode.insertBefore(wrapper, input.nextSibling);

        progressMap[input.name] = {
            wrapper: wrapper,
            fill: wrapper.querySelector('[data-fill]'),
            label: wrapper.querySelector('[data-label]'),
            percent: wrapper.querySelector('[data-percent]')
        };

        input.addEventListener('change', function () {
            var prog = progressMap[input.name];
            if (!prog) return;

            if (input.files && input.files.length > 0) {
                var file = input.files[0];
                var sizeMB = (file.size / (1024 * 1024)).toFixed(1);
                prog.wrapper.style.display = '';
                prog.label.textContent = file.name + ' (' + sizeMB + ' MB)';
                prog.fill.style.width = '100%';
                prog.fill.className = 'upload-progress-fill complete';
                prog.percent.textContent = 'Ready';
                prog.percent.className = 'upload-progress-percent complete';
            } else {
                prog.wrapper.style.display = 'none';
            }
        });
    });

    // ═══════════════════════════════════════════════════════
    //  CREATE UPLOAD MODAL
    // ═══════════════════════════════════════════════════════
    var modal = document.createElement('div');
    modal.className = 'upload-modal-overlay';
    modal.id = 'uploadModal';
    modal.innerHTML =
        '<div class="upload-modal">' +
            '<div class="upload-modal-header">' +
                '<div class="upload-modal-icon"><i class="fas fa-cloud-upload-alt"></i></div>' +
                '<div>' +
                    '<h3>Uploading Product</h3>' +
                    '<p class="upload-modal-sub">Please wait, do not close this page...</p>' +
                '</div>' +
            '</div>' +
            '<div class="upload-modal-body" id="uploadModalBody"></div>' +
            '<div class="upload-modal-footer">' +
                '<div class="upload-modal-total">' +
                    '<span id="uploadTotalLabel">Total Progress</span>' +
                    '<span id="uploadTotalPercent">0%</span>' +
                '</div>' +
                '<div class="upload-modal-total-bar">' +
                    '<div class="upload-modal-total-fill" id="uploadTotalFill"></div>' +
                '</div>' +
            '</div>' +
        '</div>';
    document.body.appendChild(modal);

    var modalBody = document.getElementById('uploadModalBody');
    var totalFill = document.getElementById('uploadTotalFill');
    var totalPercent = document.getElementById('uploadTotalPercent');
    var totalLabel = document.getElementById('uploadTotalLabel');

    // ═══════════════════════════════════════════════════════
    //  FORM SUBMIT — single XHR with progress
    // ═══════════════════════════════════════════════════════
    form.addEventListener('submit', function (e) {
        e.preventDefault();

        // Collect files that exist
        var filesToUpload = [];
        fileInputs.forEach(function (input) {
            if (input.files && input.files.length > 0) {
                filesToUpload.push({
                    name: input.name,
                    file: input.files[0]
                });
            }
        });

        // No files? Submit normally
        if (filesToUpload.length === 0) {
            form.removeEventListener('submit', arguments.callee);
            form.submit();
            return;
        }

        // Build modal rows
        modalBody.innerHTML = '';
        filesToUpload.forEach(function (item) {
            var sizeMB = (item.file.size / (1024 * 1024)).toFixed(1);
            var label = item.name.replace(/_/g, ' ').replace(/\b\w/g, function (c) {
                return c.toUpperCase();
            });

            var row = document.createElement('div');
            row.className = 'upload-modal-row active';
            row.setAttribute('data-field', item.name);
            row.innerHTML =
                '<div class="upload-row-header">' +
                    '<span class="upload-row-name"><i class="fas fa-file"></i> ' + label + '</span>' +
                    '<span class="upload-row-size">' + sizeMB + ' MB</span>' +
                '</div>' +
                '<div class="upload-row-bar">' +
                    '<div class="upload-row-fill" data-row-fill></div>' +
                '</div>' +
                '<div class="upload-row-status uploading" data-row-status>Uploading...</div>';

            modalBody.appendChild(row);
        });

        // Show modal
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';

        // Build FormData from entire form (fields + files)
        var formData = new FormData(form);

        // Single XHR for everything
        var xhr = new XMLHttpRequest();
        xhr.open('POST', form.action || window.location.href, true);

        xhr.upload.addEventListener('progress', function (e) {
            if (e.lengthComputable) {
                var pct = Math.round((e.loaded / e.total) * 100);
                totalFill.style.width = pct + '%';
                totalPercent.textContent = pct + '%';

                // Update each file row (estimate based on total)
                filesToUpload.forEach(function (item) {
                    var rowFill = modalBody.querySelector('[data-field="' + item.name + '"] [data-row-fill]');
                    var rowStatus = modalBody.querySelector('[data-field="' + item.name + '"] [data-row-status]');
                    if (rowFill) rowFill.style.width = pct + '%';
                    if (rowStatus) rowStatus.textContent = 'Uploading... ' + pct + '%';
                });
            }
        });

        xhr.addEventListener('load', function () {
            if (xhr.status >= 200 && xhr.status < 400) {
                // Success
                totalFill.style.width = '100%';
                totalFill.className = 'upload-modal-total-fill complete';
                totalPercent.textContent = '100%';
                totalLabel.textContent = 'Upload Complete!';

                // Mark all rows as done
                var allRows = modalBody.querySelectorAll('.upload-modal-row');
                allRows.forEach(function (row) {
                    row.classList.add('done');
                    row.classList.remove('active');
                    var fill = row.querySelector('[data-row-fill]');
                    var status = row.querySelector('[data-row-status]');
                    if (fill) {
                        fill.style.width = '100%';
                        fill.className = 'upload-row-fill complete';
                    }
                    if (status) {
                        status.textContent = 'Complete';
                        status.className = 'upload-row-status complete';
                    }
                });

                // Update input progress bars to show done
                fileInputs.forEach(function (input) {
                    var prog = progressMap[input.name];
                    if (prog && input.files && input.files.length > 0) {
                        prog.fill.className = 'upload-progress-fill complete';
                        prog.percent.textContent = 'Uploaded';
                        prog.percent.className = 'upload-progress-percent complete';
                    }
                });

                // Close modal and redirect
                setTimeout(function () {
                    modal.classList.remove('active');
                    document.body.style.overflow = '';

                    // Check if response has a redirect URL
                    var redirectUrl = xhr.getResponseHeader('X-Redirect') || xhr.responseURL;

                    // If response is HTML (redirect after POST), just go there
                    if (redirectUrl && redirectUrl !== window.location.href) {
                        window.location.href = redirectUrl;
                    } else {
                        // Reload current page
                        window.location.reload();
                    }
                }, 1200);

            } else {
                // Server error
                totalLabel.textContent = 'Upload Failed!';
                totalFill.className = 'upload-modal-total-fill error';

                var allRows = modalBody.querySelectorAll('.upload-modal-row');
                allRows.forEach(function (row) {
                    var status = row.querySelector('[data-row-status]');
                    var fill = row.querySelector('[data-row-fill]');
                    if (fill) fill.className = 'upload-row-fill error';
                    if (status) {
                        status.textContent = 'Error ' + xhr.status;
                        status.className = 'upload-row-status error';
                    }
                });

                // Allow user to close
                setTimeout(function () {
                    totalLabel.textContent = 'Failed — click anywhere to close';
                    modal.addEventListener('click', function () {
                        modal.classList.remove('active');
                        document.body.style.overflow = '';
                    }, { once: true });
                }, 2000);
            }
        });

        xhr.addEventListener('error', function () {
            totalLabel.textContent = 'Network Error!';
            totalFill.className = 'upload-modal-total-fill error';

            var allRows = modalBody.querySelectorAll('.upload-modal-row');
            allRows.forEach(function (row) {
                var status = row.querySelector('[data-row-status]');
                var fill = row.querySelector('[data-row-fill]');
                if (fill) fill.className = 'upload-row-fill error';
                if (status) {
                    status.textContent = 'Network Error';
                    status.className = 'upload-row-status error';
                }
            });

            setTimeout(function () {
                modal.addEventListener('click', function () {
                    modal.classList.remove('active');
                    document.body.style.overflow = '';
                }, { once: true });
            }, 2000);
        });

        xhr.send(formData);
    });

})();