/**
 * JavaScript for admin files management page
 */

function confirmDeleteShare(isExpired) {
    // If file is expired, delete without confirmation
    if (isExpired) {
        return true;
    }
    // If file is not expired, ask for confirmation
    return confirm('Delete this file share? This cannot be undone.');
}

// Event delegation for delete forms
document.addEventListener('DOMContentLoaded', function() {
    document.addEventListener('submit', function(e) {
        if (e.target.classList.contains('delete-share-form')) {
            const isExpired = e.target.getAttribute('data-is-expired') === 'true';
            if (!confirmDeleteShare(isExpired)) {
                e.preventDefault();
            }
        }
    });
});
