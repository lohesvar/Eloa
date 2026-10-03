/* ==========================================
   ANALYTICS & PERFORMANCE CHART.JS LOGIC
   ========================================== */

let lineChartInstance = null;
let pieChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('performanceLineChart')) {
    initAnalyticsPage();
  }
});

async function initAnalyticsPage() {
  initPeriodButtons();
  await loadAnalyticsData('week');
}

function initPeriodButtons() {
  document.querySelectorAll('.period-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      const period = e.target.getAttribute('data-period');
      loadAnalyticsData(period);
    });
  });
}

async function loadAnalyticsData(period = 'week') {
  try {
    const response = await fetch(`/api/analytics?period=${period}`);
    const data = await response.json();

    updateSummaryCards(data.summary);
    updateCategoryStats(data.category_stats);
    renderCharts(data);
  } catch (err) {
    console.error('Failed to load analytics:', err);
  }
}

function updateSummaryCards(summary) {
  const elemMap = {
    'stat-total-tasks': summary.total_tasks,
    'stat-completed-tasks': summary.completed_tasks,
    'stat-pending-tasks': summary.pending_tasks,
    'stat-overdue-tasks': summary.overdue_tasks,
    'stat-completion-rate': `${summary.completion_rate}%`,
    'stat-avg-performance': `${summary.avg_performance}%`,
    'stat-current-streak': `${summary.current_streak} days`,
    'stat-longest-streak': `${summary.longest_streak} days`
  };

  for (const [id, val] of Object.entries(elemMap)) {
    const elem = document.getElementById(id);
    if (elem) elem.innerText = val;
  }
}

function updateCategoryStats(catStats) {
  const catMap = {
    'long_term': 'Long-Term Goals',
    'short_term': 'Short-Term Tasks',
    'daily': 'Daily Tasks'
  };

  const container = document.getElementById('category-stats-list');
  if (!container) return;

  container.innerHTML = '';
  for (const [key, stats] of Object.entries(catStats)) {
    const name = catMap[key] || key;
    const item = document.createElement('div');
    item.className = 'cat-progress-item';
    
    let colorClass = 'var(--accent-amber)';
    if (key === 'long_term') colorClass = 'var(--accent-blue)';
    if (key === 'daily') colorClass = 'var(--accent-green)';

    item.innerHTML = `
      <div class="cat-label-row">
        <span>${name} (${stats.completed}/${stats.total})</span>
        <span>${stats.rate}%</span>
      </div>
      <div class="cat-bar-wrap">
        <div class="cat-bar-fill" style="width: ${stats.rate}%; background: ${colorClass};"></div>
      </div>
    `;
    container.appendChild(item);
  }
}

function renderCharts(data) {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const textColor = isDark ? '#9ea0a6' : '#78736b';
  const gridColor = isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(180, 170, 155, 0.2)';

  // 1. Line Chart
  const lineCtx = document.getElementById('performanceLineChart').getContext('2d');
  if (lineChartInstance) lineChartInstance.destroy();

  lineChartInstance = new Chart(lineCtx, {
    type: 'line',
    data: {
      labels: data.line_chart.labels,
      datasets: [
        {
          label: 'Daily Performance %',
          data: data.line_chart.daily_performance,
          borderColor: isDark ? '#ff2e43' : '#d97706',
          backgroundColor: isDark ? 'rgba(255, 46, 67, 0.1)' : 'rgba(217, 119, 6, 0.1)',
          borderWidth: 3,
          fill: true,
          tension: 0.35,
          pointRadius: 4,
          pointHoverRadius: 6
        },
        {
          label: 'Overall Completion Rate %',
          data: data.line_chart.overall_completion,
          borderColor: '#10b981',
          backgroundColor: 'transparent',
          borderWidth: 2,
          borderDash: [5, 5],
          tension: 0.35,
          pointRadius: 3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: textColor, font: { family: 'Inter', size: 12 } }
        }
      },
      scales: {
        x: {
          ticks: { color: textColor },
          grid: { color: gridColor }
        },
        y: {
          min: 0,
          max: 100,
          ticks: { color: textColor, callback: v => v + '%' },
          grid: { color: gridColor }
        }
      }
    }
  });

  // 2. Pie / Donut Chart
  const pieCtx = document.getElementById('completionPieChart').getContext('2d');
  if (pieChartInstance) pieChartInstance.destroy();

  pieChartInstance = new Chart(pieCtx, {
    type: 'doughnut',
    data: {
      labels: ['Completed', 'Pending', 'Overdue'],
      datasets: [{
        data: [
          data.pie_chart.completed,
          data.pie_chart.pending,
          data.pie_chart.overdue
        ],
        backgroundColor: [
          '#10b981',
          isDark ? '#3b82f6' : '#d97706',
          '#ef4444'
        ],
        borderWidth: 2,
        borderColor: isDark ? '#121216' : '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: textColor, font: { family: 'Inter', size: 12 } }
        }
      },
      cutout: '70%'
    }
  });
}

// Global hook so main.js theme switcher re-renders chart colors on toggle
window.renderAnalyticsCharts = () => {
  const activeBtn = document.querySelector('.period-btn.active');
  const period = activeBtn ? activeBtn.getAttribute('data-period') : 'week';
  loadAnalyticsData(period);
};
