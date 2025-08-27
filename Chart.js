const isDark = bodyEl.classList.contains('dark-mode');
new Chart(document.getElementById('wishlistProductChart'), {
  type: 'bar',
  data: {
    labels: wishlistProducts.labels,
    datasets: [{
      label: 'Wishlists',
      data: wishlistProducts.counts,
      borderRadius: 7,
      backgroundColor: "#ad00e2"
    }]
  },
  options: {
    plugins: {
      legend: { display: false }
    },
    scales: {
      y: { 
        beginAtZero: true,
        grid: { color: isDark ? '#444' : '#eee' },
        ticks: { color: isDark ? '#fff' : '#23242a' }
      },
      x: {
        grid: { display: false },
        ticks: { color: isDark ? '#fff' : '#23242a' }
      }
    }
  }
});
