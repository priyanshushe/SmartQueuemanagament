let countdownInterval;
let refreshInterval;

// Show the selected box and animate it
function showBox(boxId) {
    document.querySelectorAll('.box').forEach(b => {
        b.classList.remove('active', 'animate__fadeIn');
    });
    document.getElementById(boxId).classList.add('active', 'animate__animated', 'animate__fadeIn');
}

// Event listener for checking token status
document.getElementById('check-status').addEventListener('click', () => {
    // Clear any existing countdown or refresh intervals
    clearInterval(countdownInterval);
    clearInterval(refreshInterval);

    const tokenNumber = document.getElementById('status-token-number').value;
    if (!tokenNumber) return alert("Enter token number");

    const resultDiv = document.getElementById('status-result');

    // Helper function to update the status display based on token data
    function updateStatusDisplay(data) {
        const countdownEl = document.getElementById('status-countdown');
        const status = data.status.toLowerCase();

        // Display token info and status
        resultDiv.innerHTML = `
            <p>Token Number: <strong>${data.token_number}</strong></p>
            <p>Status: <strong id="token-status">${data.status}</strong></p>
            <p id="status-countdown"></p>
        `;

        // Show completed or cancelled message if applicable
        if (status.includes("done") || status.includes("completed")) {
            countdownEl.innerText = "✅ Completed";
            return false;
        }
        if (status.includes("cancelled")) {
            countdownEl.innerText = "❌ Cancelled";
            return false;
        }
        return true; // Token is active
    }

    // Fetch token status from backend
    fetch(`/api/token_status/${tokenNumber}`)
        .then(res => res.json())
        .then(data => {
            const startCountdown = updateStatusDisplay(data);
            // If not active or no end_datetime, stop here
            if (!startCountdown || !data.end_datetime) return;

            const endTime = new Date(data.end_datetime);

            // Start countdown interval to update every second
            countdownInterval = setInterval(() => {
                // Fetch latest token status on each tick
                fetch(`/api/token_status/${tokenNumber}`)
                    .then(res => res.json())
                    .then(updatedData => {
                        const countdownEl = document.getElementById('status-countdown');
                        const status = updatedData.status.toLowerCase();

                        // If token is completed or cancelled, show message and stop countdown
                        if (status.includes("done") || status.includes("completed")) {
                            countdownEl.innerText = "✅ Completed";
                            clearInterval(countdownInterval);
                            return;
                        }
                        if (status.includes("cancelled")) {
                            countdownEl.innerText = "❌ Cancelled";
                            clearInterval(countdownInterval);
                            return;
                        }

                        // Calculate time difference for countdown
                        const now = new Date();
                        let diff = Math.floor((endTime - now) / 1000);
                        if (diff <= 0) {
                            countdownEl.innerText = "⏰ It's your turn! Please wait for staff.";
                        } else {
                            const min = Math.floor(diff / 60);
                            const sec = diff % 60;
                            countdownEl.innerText = `Countdown: ${min} min ${sec} sec`;
                        }
                    });
            }, 1000);
        })
        .catch(err => console.error(err));
});