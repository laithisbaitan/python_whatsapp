function updateTemplatePreview() {
    const templateDropdown = document.getElementById('template');
    const selectedOption = templateDropdown.options[templateDropdown.selectedIndex];
    const bodyText = selectedOption.getAttribute('data-body');
    const paramCount = selectedOption.getAttribute('data-params');

    const previewDiv = document.getElementById('template-preview');
    if (bodyText) {
        let previewHtml = `<p>${bodyText.replace(/\\{\\{\\d+\\}\\}/g, '<span class="placeholder">$&</span>')}</p>`;
        previewHtml += `<p>Number of parameters: ${paramCount}</p>`;
        previewDiv.innerHTML = `<h3>Template Preview:</h3>${previewHtml}`;
    } else {
        previewDiv.innerHTML = `<h3>Template Preview:</h3><p>No preview available for this template.</p>`;
    }
}

// Initialize preview for the first selected template
document.addEventListener('DOMContentLoaded', updateTemplatePreview);
