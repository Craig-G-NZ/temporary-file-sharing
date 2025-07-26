/**
 * JavaScript for admin settings page
 */

function testEmail() {
    $('#testEmailModal').modal('show');
}

function manualCleanup() {
    if (confirm('Are you sure you want to manually clean up expired files? This action cannot be undone.')) {
        fetch('/admin/cleanup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name=csrf-token]').getAttribute('content')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                // Optionally reload the page to update any stats
                location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            alert('Error during cleanup: ' + error);
        });
    }
}

// Timezone display functionality
function updateCurrentTime() {
    const timezoneSelect = document.getElementById('display_timezone');
    const currentTimeDisplay = document.getElementById('current-time-display');
    
    if (timezoneSelect && currentTimeDisplay) {
        const selectedTimezone = timezoneSelect.value;
        try {
            const now = new Date();
            const options = {
                timeZone: selectedTimezone,
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                timeZoneName: 'short'
            };
            const timeString = now.toLocaleString('en-NZ', options);
            currentTimeDisplay.textContent = timeString;
            // Add some styling
            currentTimeDisplay.style.fontWeight = 'bold';
            currentTimeDisplay.style.color = '#28a745';
        } catch (error) {
            currentTimeDisplay.textContent = 'Invalid timezone';
            currentTimeDisplay.style.color = '#dc3545';
        }
    }
}

// Initialize event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Test email button
    const testEmailBtn = document.getElementById('test-email-btn');
    if (testEmailBtn) {
        testEmailBtn.addEventListener('click', testEmail);
    }

    // Manual cleanup button
    const manualCleanupBtn = document.getElementById('manual-cleanup-btn');
    if (manualCleanupBtn) {
        manualCleanupBtn.addEventListener('click', manualCleanup);
    }

    // Test email form submission
    const testEmailForm = document.getElementById('testEmailForm');
    if (testEmailForm) {
        testEmailForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            fetch('/admin/test-email', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Test email sent successfully!');
                } else {
                    alert('Error: ' + data.error);
                }
                $('#testEmailModal').modal('hide');
            })
            .catch(error => {
                alert('Error sending test email: ' + error);
                $('#testEmailModal').modal('hide');
            });
        });
    }

    // Timezone functionality
    const timezoneSelect = document.getElementById('display_timezone');
    if (timezoneSelect) {
        timezoneSelect.addEventListener('change', updateCurrentTime);
        // Update immediately
        updateCurrentTime();
        // Update every second
        setInterval(updateCurrentTime, 1000);
    }
});
