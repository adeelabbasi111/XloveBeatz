document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('cropperModal');
    const image = document.getElementById('cropperImage');
    const cancelBtn = document.getElementById('cropperCancelBtn');
    const saveBtn = document.getElementById('cropperSaveBtn');
    
    let cropper = null;
    let currentInput = null;
    let ignoreNextChange = false;
    
    // Find all image upload inputs
    const imageInputs = document.querySelectorAll('input[type="file"][accept="image/*"]');
    
    imageInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            if (ignoreNextChange) {
                ignoreNextChange = false;
                return; // We just set this programmatically, don't reopen cropper!
            }
            
            const file = e.target.files[0];
            if (!file) return;
            
            // Only process images
            if (!file.type.startsWith('image/')) return;
            
            currentInput = this;
            
            // Determine aspect ratio based on input name/id
            let aspectRatio = 1; // Default square for covers, beats, presets
            if (this.name === 'image' && window.location.href.includes('genres')) {
                // Genres typically use 4:3 or 1:1, we'll enforce 1:1 square for consistency with our backend
                aspectRatio = 1; 
            }
            
            const reader = new FileReader();
            reader.onload = (evt) => {
                image.src = evt.target.result;
                modal.style.display = 'block';
                
                // Initialize Cropper
                if (cropper) cropper.destroy();
                cropper = new Cropper(image, {
                    aspectRatio: aspectRatio,
                    viewMode: 1, // Restrict crop box to not exceed canvas
                    dragMode: 'move', // Allow moving the image like FB
                    autoCropArea: 1, // Try to crop full area initially
                    restore: false,
                    guides: true,
                    center: true,
                    highlight: false,
                    cropBoxMovable: true,
                    cropBoxResizable: true,
                    toggleDragModeOnDblclick: false,
                });
            };
            reader.readAsDataURL(file);
        });
    });
    
    cancelBtn.addEventListener('click', () => {
        modal.style.display = 'none';
        if (cropper) cropper.destroy();
        cropper = null;
        if (currentInput) currentInput.value = ''; // Reset input
    });
    
    saveBtn.addEventListener('click', () => {
        if (!cropper) return;
        
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        saveBtn.disabled = true;
        
        const canvas = cropper.getCroppedCanvas();
        
        // Convert to Blob and place into the file input
        canvas.toBlob((blob) => {
            const originalFile = currentInput.files[0];
            const newFile = new File([blob], originalFile.name, {
                type: 'image/jpeg',
                lastModified: Date.now()
            });
            
            // Use DataTransfer to programmatically set the files on the input element
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(newFile);
            
            ignoreNextChange = true;
            currentInput.files = dataTransfer.files;
            
            // Update preview image if it exists nearby
            const formRow = currentInput.closest('.form-group');
            if (formRow) {
                const previewImg = formRow.querySelector('img');
                if (previewImg) {
                    previewImg.src = URL.createObjectURL(blob);
                }
            }
            
            // Cleanup
            modal.style.display = 'none';
            if (cropper) cropper.destroy();
            cropper = null;
            saveBtn.innerHTML = 'Crop & Save';
            saveBtn.disabled = false;
        }, 'image/jpeg', 0.95); // High quality JPEG, backend will convert to WebP
    });
});
