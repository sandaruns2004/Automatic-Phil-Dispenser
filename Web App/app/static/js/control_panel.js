document.addEventListener('DOMContentLoaded', function() {
    const ctx = document.getElementById('sensorChart').getContext('2d');
    const dataList = document.getElementById('data-list');

    const sensorChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Temperature (°C)',
                data: [],
                borderColor: 'rgba(255, 99, 132, 1)',
                borderWidth: 1,
                fill: false
            }, {
                label: 'Humidity (%)',
                data: [],
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1,
                fill: false
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    async function fetchData() {
        try {
            const response = await fetch('/api/data/latest');
            const data = await response.json();
            
            // Clear previous data
            dataList.innerHTML = '';
            sensorChart.data.labels = [];
            sensorChart.data.datasets[0].data = [];
            sensorChart.data.datasets[1].data = [];

            // Reverse to show oldest first in the chart
            data.reverse().forEach(reading => {
                // Update list
                const listItem = document.createElement('a');
                listItem.href = '#';
                listItem.className = 'list-group-item list-group-item-action';
                listItem.innerHTML = `<strong>${reading.type}:</strong> ${reading.value}${reading.unit} <small class="text-muted">(${reading.time})</small>`;
                dataList.prepend(listItem);

                // Update chart
                if (reading.type === 'Temperature') {
                    sensorChart.data.datasets[0].data.push(reading.value);
                } else if (reading.type === 'Humidity') {
                    sensorChart.data.datasets[1].data.push(reading.value);
                }
                // Use a common label for both datasets
                if (!sensorChart.data.labels.includes(reading.time)) {
                    sensorChart.data.labels.push(reading.time);
                }
            });

            sensorChart.update();

        } catch (error) {
            console.error('Error fetching data:', error);
            dataList.innerHTML = '<li class="list-group-item">Failed to load data.</li>';
        }
    }

    fetchData();
    // Refresh data every 30 seconds
    setInterval(fetchData, 30000);
});