/**
 * Dashboard V2 - 实时安全监控面板
 * 负责获取系统指标、安全事件统计，并驱动图表与活动日志更新
 */

let realtimeChart;
let securityEventsChart;
let systemStartTime = Date.now();
const MAX_DATA_POINTS = 30;

document.addEventListener('DOMContentLoaded', async () => {
    initCharts();
    // 初始获取一次数据
    await fetchMetrics();
    // 定时刷新
    setInterval(fetchMetrics, 5000);
    setInterval(updateUptime, 1000);
    // 初始化网络拓扑状态
    updateTopologyStatus();
    setInterval(updateTopologyStatus, 10000);
});

/**
 * 主数据获取函数，并行拉取系统指标、事件日统计和事件总览统计
 */
async function fetchMetrics() {
    try {
        const [sysRes, dailyRes, statsRes] = await Promise.all([
            fetch('/api/v1/metrics'),
            fetch('/api/v1/metrics/events'),
            fetch('/api/v1/events/stats')
        ]);

        if (sysRes.ok) {
            const sysData = await sysRes.json();
            updateSysMetricsUI(sysData);
            updateRealtimeChart(sysData);
        }

        // 每日趋势数据（Day 1 ~ Day 7）
        if (dailyRes.ok) {
            const dailyData = await dailyRes.json();
            updateDailyTrendFromData(dailyData);
        }

        // 真实总量统计（来自数据库）
        if (statsRes.ok) {
            const statsData = await statsRes.json();
            updateEventsChartFromStats(statsData);
            updateTotalBlockedFromStats(statsData);
        }

        // 活动日志 & 命中排行
        fetchTopRules();
    } catch (e) {
        console.error('Failed to fetch dashboard metrics:', e);
    }
}

/**
 * 更新系统指标卡片
 */
function updateSysMetricsUI(data) {
    setTextById('cpu-usage', `${Math.round(data.cpu_usage)}%`);
    setTextById('memory-usage', `${Math.round(data.memory_usage)}%`);
    // NOTE: HTML 中 avg-response-time 元素内已带有 <small>ms</small> 后缀
    // 直接通过 innerHTML 设置数值部分，避免重复显示 ms
    const rtEl = document.getElementById('avg-response-time');
    if (rtEl) rtEl.innerHTML = `${Math.round(data.avg_response_time)}<small style="font-size: 1rem; color: var(--text-secondary);">毫秒</small>`;
    setTextById('active-connections', data.active_requests || 0);
}

/**
 * 更新运行时间 & 当前时间
 */
function updateUptime() {
    const uptimeSecs = Math.floor((Date.now() - systemStartTime) / 1000);
    const hrs = Math.floor(uptimeSecs / 3600);
    const mins = Math.floor((uptimeSecs % 3600) / 60);
    setTextById('uptime', `${hrs}h ${mins}m`);
    setTextById('current-time', new Date().toLocaleTimeString());
}

/**
 * 初始化图表
 */
function initCharts() {
    // 实时资源监控 - 折线图
    const rtCtx = document.getElementById('realtime-metrics-chart');
    if (!rtCtx) return;
    realtimeChart = new Chart(rtCtx.getContext('2d'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'CPU (%)',
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    data: [],
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2
                },
                {
                    label: '内存 (%)',
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    data: [],
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { min: 0, max: 100, ticks: { font: { size: 11 } } },
                x: { ticks: { font: { size: 10 }, maxTicksLimit: 10 } }
            },
            animation: false,
            plugins: {
                legend: { position: 'top', labels: { font: { size: 11 } } }
            }
        }
    });

    // 安全事件分布 - 甜甜圈图
    const evtCtx = document.getElementById('security-events-chart');
    if (!evtCtx) return;
    securityEventsChart = new Chart(evtCtx.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['提示注入', '越狱攻击', '敏感信息', '有害内容', '合规违规'],
            datasets: [{
                data: [0, 0, 0, 0, 0],
                backgroundColor: ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6'],
                borderWidth: 2,
                borderColor: '#1a1a2e'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#a0aec0',
                        font: { size: 11 },
                        padding: 12
                    }
                }
            }
        }
    });
}

/**
 * 更新实时资源利用率折线图
 */
function updateRealtimeChart(data) {
    if (!realtimeChart) return;
    const timeLabel = new Date().toLocaleTimeString();

    if (realtimeChart.data.labels.length > MAX_DATA_POINTS) {
        realtimeChart.data.labels.shift();
        realtimeChart.data.datasets[0].data.shift();
        realtimeChart.data.datasets[1].data.shift();
    }

    realtimeChart.data.labels.push(timeLabel);
    realtimeChart.data.datasets[0].data.push(data.cpu_usage);
    realtimeChart.data.datasets[1].data.push(data.memory_usage);

    realtimeChart.update();
}

/**
 * 使用 /api/v1/events/stats 的真实统计更新甜甜圈图
 */
function updateEventsChartFromStats(stats) {
    if (!securityEventsChart || !stats) return;
    securityEventsChart.data.datasets[0].data = [
        stats.prompt_injection || 0,
        stats.jailbreak || 0,
        stats.sensitive_info || 0,
        stats.harmful_content || 0,
        stats.compliance_violation || 0
    ];
    securityEventsChart.update();
}

/**
 * 使用 stats API 更新总拦截数
 */
function updateTotalBlockedFromStats(stats) {
    if (!stats) return;
    setTextById('blocked-requests', stats.total || 0);
}

/**
 * 从每日趋势数据计算（暂时保留，用于未来趋势面板扩展）
 */
function updateDailyTrendFromData(data) {
    // NOTE: 当前 /api/v1/metrics/events 返回 Day 1~7 的分布
    // 可考虑后续用柱状图展示每日趋势
}

/**
 * 渲染安全规则命中排行榜 & 最新活动日志
 */
async function fetchTopRules() {
    try {
        // Parallel fetch for ranking and activity
        const [rankRes, eventsRes] = await Promise.all([
            fetch('/api/v1/realtime/rule-stats?limit=5'),
            fetch('/api/v1/events?page_size=10')
        ]);

        if (rankRes.ok) {
            const ranking = await rankRes.json();
            renderRanking(ranking);
        }

        if (eventsRes.ok) {
            const data = await eventsRes.json();
            renderActivityLog(data.events || []);
        }
    } catch (e) {
        console.error('仪表板数据拉取失败:', e);
    }
}

/**
 * 渲染规则命中排行榜 (M3.2)
 */
function renderRanking(ranking) {
    const listEl = document.getElementById('rule-ranking-list');
    if (!listEl) return;
    listEl.innerHTML = '';

    if (!ranking || ranking.length === 0) {
        listEl.innerHTML = '<div style="padding: 2rem; color: var(--text-secondary); text-align: center;">暂无命中数据</div>';
        return;
    }

    ranking.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'ranking-item';
        const rankClass = index < 3 ? `top-${index + 1}` : '';

        div.innerHTML = `
            <div style="display: flex; align-items: center;">
                <span class="ranking-badge ${rankClass}">${index + 1}</span>
                <span class="ranking-name">${item.rule_name || '未知规则'}</span>
            </div>
            <span class="ranking-count">${item.hit_count} 次</span>
        `;
        listEl.appendChild(div);
    });
}

/**
 * 渲染活动日志 (M3.2)
 */
function renderActivityLog(events) {
    const listEl = document.getElementById('activity-log');
    if (!listEl) return;
    listEl.innerHTML = '';

    if (!events || events.length === 0) {
        listEl.innerHTML = '<div style="padding: 2rem; color: var(--text-secondary); text-align: center;">暂无近期拦截活动</div>';
        return;
    }

    events.slice(0, 8).forEach(event => {
        const typeIcon = getEventIcon(event.detection_type);
        const typeClass = getEventSeverityClass(event.severity);
        const timeStr = formatTimestamp(event.timestamp);

        const div = document.createElement('div');
        div.className = 'activity-item';
        div.innerHTML = `
            <div class="activity-icon ${typeClass}"><i class="fas ${typeIcon}"></i></div>
            <div class="activity-content">
                <h4>${event.rule_name || event.detection_type || '安全事件'}</h4>
                <p>${truncateText(event.reason || '', 100)}</p>
            </div>
            <div class="activity-time">${timeStr}</div>
        `;
        listEl.appendChild(div);
    });
}

/**
 * 更新网络拓扑节点状态与通过率/拦截率
 */
async function updateTopologyStatus() {
    try {
        const [metricsRes, statsRes] = await Promise.all([
            fetch('/api/v1/metrics'),
            fetch('/api/v1/events/stats')
        ]);

        if (metricsRes.ok) {
            setNodeStatus('gateway-status', 'online');
            setNodeStatus('client-status', 'online');
            setNodeStatus('llm-status', 'online');

            const metrics = await metricsRes.json();
            // 计算通过率和拦截率
            if (statsRes.ok) {
                const stats = await statsRes.json();
                const blocked = stats.total || 0;
                // 利用 metrics 中的总请求数来计算率
                const totalRequests = metrics.total_requests || (blocked * 5) || 1;
                const blockRate = ((blocked / totalRequests) * 100).toFixed(1);
                const passRate = (100 - parseFloat(blockRate)).toFixed(1);

                setTextById('pass-rate-stat', `${passRate}%`);
                setTextById('block-rate-stat', `${blockRate}%`);
            }
        } else {
            setNodeStatus('gateway-status', 'warning');
        }
    } catch {
        setNodeStatus('gateway-status', 'offline');
        setNodeStatus('llm-status', 'offline');
    }
}

// ============ 工具函数 ============

function setTextById(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
}

function setNodeStatus(id, statusType) {
    const el = document.getElementById(id);
    if (!el) return;
    el.className = `status-dot ${statusType}`;
}

function getEventIcon(detectionType) {
    const iconMap = {
        'prompt_injection': 'fa-syringe',
        'jailbreak': 'fa-unlock-alt',
        'sensitive_info': 'fa-eye-slash',
        'harmful_content': 'fa-skull-crossbones',
        'compliance_violation': 'fa-gavel',
        'role_play': 'fa-theater-masks'
    };
    return iconMap[detectionType] || 'fa-shield-alt';
}

function getEventSeverityClass(severity) {
    const classMap = {
        'critical': 'danger',
        'high': 'warning',
        'medium': 'info',
        'low': 'success'
    };
    return classMap[severity] || 'info';
}

function formatTimestamp(ts) {
    if (!ts) return '';
    const d = new Date(ts * 1000);
    const now = new Date();
    const diffMs = now - d;
    const diffSec = Math.floor(diffMs / 1000);

    if (diffSec < 60) return `${diffSec}秒前`;
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}分钟前`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}小时前`;
    return d.toLocaleDateString();
}

function truncateText(text, maxLen) {
    if (text.length <= maxLen) return text;
    return text.substring(0, maxLen) + '...';
}
