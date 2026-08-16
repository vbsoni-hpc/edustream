'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { analyticsApi, dashboardApi, progressApi, subscriptionsApi } from '@/lib/api';
import { formatHours } from '@/lib/utils';
import Sidebar from '@/components/Sidebar';
import AuthGuard from '@/components/AuthGuard';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

export default function LearningPage() {
  return (
    <AuthGuard>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <LearningContent />
        </main>
      </div>
    </AuthGuard>
  );
}

function LearningContent() {
  const { token, user } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [segStats, setSegStats] = useState<any[]>([]);
  const [modStats, setModStats] = useState<any[]>([]);
  const [dailyActivity, setDailyActivity] = useState<any[]>([]);
  const [progress, setProgress] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    (async () => {
      try {
        const [statsRes, segRes, modRes, dailyRes, progRes, subsRes] = await Promise.all([
          dashboardApi.getStats(token),
          analyticsApi.getSegments(token),
          analyticsApi.getModules(token),
          analyticsApi.getDaily(token, 30),
          progressApi.getAll(token),
          subscriptionsApi.get(token),
        ]);
        
        const subIds = new Set(subsRes.subscribed_ids);
        const filteredSegs = segRes.segments.filter((s: any) => subIds.has(s.id));
        const filteredMods = modRes.modules.filter((m: any) => subIds.has(m.segment_id));

        let totalVideos = 0;
        let completedVideos = 0;
        let totalWatchSeconds = 0;
        filteredSegs.forEach((s: any) => {
          totalVideos += s.total_videos || 0;
          completedVideos += s.completed_videos || 0;
          totalWatchSeconds += s.watch_seconds || 0;
        });
        const completionPct = totalVideos > 0 ? (completedVideos / totalVideos * 100) : 0;
        
        setStats({
          total_videos: totalVideos,
          completed_videos: completedVideos,
          completion_pct: completionPct,
          total_watch_hours: totalWatchSeconds / 3600,
          total_watch_seconds: totalWatchSeconds
        });
        
        setSegStats(filteredSegs);
        setModStats(filteredMods);
        setDailyActivity(dailyRes.activity);
        setProgress(progRes.progress);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  if (loading) {
    return <div className="loading-screen"><div className="spinner" /><span>Loading analytics...</span></div>;
  }

  if (!stats) return null;

  const sessions = progress.filter(p => p.watch_seconds > 0).length;
  const avgSession = sessions > 0 ? (stats.total_watch_seconds / sessions / 60) : 0;

  // Donut data
  const donutData = [
    { name: 'Completed', value: stats.completed_videos },
    { name: 'Remaining', value: Math.max(stats.total_videos - stats.completed_videos, 0) },
  ];
  const DONUT_COLORS = ['#6C63FF', 'rgba(255,255,255,0.06)'];

  // Bar chart data
  const barData = segStats.map(s => ({
    name: `${s.icon} ${s.name}`,
    hours: parseFloat((s.watch_seconds / 3600).toFixed(1)),
  }));

  // Daily activity
  const activityData = dailyActivity.map(d => ({
    date: d.date,
    minutes: Math.round(d.watch_seconds / 60),
  }));

  return (
    <div className="animate-fade-in">
      <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>📊 Learning Dashboard</h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>Your progress overview, <strong>{user?.display_name}</strong></p>
      <div className="divider" />

      {/* Stat Cards */}
      <div className="grid-4 mb-6">
        <div className="stat-card">
          <div className="stat-value">{stats.completed_videos}/{stats.total_videos}</div>
          <div className="stat-label">Videos Completed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.completion_pct.toFixed(0)}%</div>
          <div className="stat-label">Completion Rate</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.total_watch_hours.toFixed(1)}h</div>
          <div className="stat-label">Total Watch Time</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{avgSession.toFixed(0)}m</div>
          <div className="stat-label">Avg Session</div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid-2 mb-6">
        {/* Donut */}
        <div className="chart-card">
          <div className="chart-title">📈 Overall Completion</div>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={donutData}
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={100}
                paddingAngle={2}
                dataKey="value"
              >
                {donutData.map((_, i) => (
                  <Cell key={i} fill={DONUT_COLORS[i]} stroke="#0E1117" strokeWidth={3} />
                ))}
              </Pie>
              <text x="50%" y="50%" textAnchor="middle" fill="#FAFAFA" fontSize={32} fontWeight={800} dy={8}>
                {stats.completion_pct.toFixed(0)}%
              </text>
            </PieChart>
          </ResponsiveContainer>
          <div style={{ textAlign: 'center', marginTop: -8 }}>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              <span style={{ color: '#6C63FF' }}>●</span> Completed &nbsp;
              <span style={{ color: 'rgba(255,255,255,0.2)' }}>●</span> Remaining
            </span>
          </div>
        </div>

        {/* Bar Chart */}
        <div className="chart-card">
          <div className="chart-title">⏱️ Watch Hours by Segment</div>
          {barData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={barData} layout="vertical" margin={{ left: 20, right: 20, top: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis type="number" tick={{ fill: '#6B7280', fontSize: 12 }} />
                <YAxis type="category" dataKey="name" tick={{ fill: '#FAFAFA', fontSize: 12 }} width={140} />
                <Tooltip
                  contentStyle={{ background: '#1A1D29', border: '1px solid rgba(108,99,255,0.2)', borderRadius: 8, color: '#FAFAFA' }}
                  formatter={(value: any) => [`${value}h`, 'Hours']}
                />
                <Bar dataKey="hours" fill="#6C63FF" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>No segments to display yet.</p>
          )}
        </div>
      </div>

      {/* Daily Activity */}
      <div className="chart-card mb-6">
        <div className="chart-title">📅 Daily Watch Activity (Last 30 Days)</div>
        {activityData.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={activityData} margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
              <XAxis dataKey="date" tick={{ fill: '#6B7280', fontSize: 11 }} />
              <YAxis tick={{ fill: '#6B7280', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#1A1D29', border: '1px solid rgba(108,99,255,0.2)', borderRadius: 8, color: '#FAFAFA' }}
                formatter={(value: any) => [`${value} minutes`, 'Watch Time']}
              />
              <Bar dataKey="minutes" fill="#6C63FF" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>No watch activity recorded yet.</p>
        )}
      </div>

      {/* Segment Breakdown */}
      <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>📋 Segment Breakdown</h3>
      {segStats.map(seg => {
        const pct = seg.total_videos > 0 ? (seg.completed_videos / seg.total_videos * 100) : 0;
        return (
          <div key={seg.id} className="flex-row mb-4" style={{ gap: 16 }}>
            <div style={{ minWidth: 240 }}>
              <strong>{seg.icon} {seg.name}</strong>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                {seg.completed_videos}/{seg.total_videos} done · {formatHours(seg.watch_seconds)} watched
              </div>
            </div>
            <div style={{ flex: 1 }}>
              <div className="flex-row" style={{ gap: 8 }}>
                <div className="progress-outer" style={{ flex: 1 }}>
                  <div className="progress-inner" style={{ width: `${Math.min(pct, 100)}%` }} />
                </div>
                <span style={{ fontSize: 13, color: 'var(--text-secondary)', minWidth: 40 }}>{pct.toFixed(0)}%</span>
              </div>
            </div>
          </div>
        );
      })}

      {/* Module Breakdown */}
      {modStats.length > 0 && (
        <>
          <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16, marginTop: 32 }}>📂 Module Breakdown</h3>
          {(() => {
            const bySegment: Record<string, any[]> = {};
            modStats.forEach(m => {
              const key = m.segment_name || 'Unknown';
              if (!bySegment[key]) bySegment[key] = [];
              bySegment[key].push(m);
            });
            return Object.entries(bySegment).map(([segName, mods]) => (
              <div key={segName} style={{ marginBottom: 16 }}>
                <strong style={{ fontSize: 15 }}>{segName}</strong>
                {mods.map(m => {
                  const mPct = m.total_videos > 0 ? (m.completed_videos / m.total_videos * 100) : 0;
                  return (
                    <div key={m.id} className="flex-row mb-4" style={{ gap: 16, paddingLeft: 20, marginTop: 8 }}>
                      <div style={{ minWidth: 220 }}>
                        <span style={{ fontSize: 14 }}>↳ {m.icon} {m.name}</span>
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                          {m.completed_videos}/{m.total_videos} done · {formatHours(m.watch_seconds)}
                        </div>
                      </div>
                      <div style={{ flex: 1 }}>
                        <div className="flex-row" style={{ gap: 8 }}>
                          <div className="progress-outer" style={{ flex: 1 }}>
                            <div className="progress-inner" style={{ width: `${Math.min(mPct, 100)}%` }} />
                          </div>
                          <span style={{ fontSize: 13, color: 'var(--text-secondary)', minWidth: 40 }}>{mPct.toFixed(0)}%</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ));
          })()}
        </>
      )}
    </div>
  );
}
