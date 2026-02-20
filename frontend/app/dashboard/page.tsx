"use client"
import React, { useState } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getAnalyticsSummary } from '../../lib/api';
import { AnalyticsSummaryResponse } from '../../types';
import BorrowTrendChart from '../../components/charts/BorrowTrendChart';
import TopMembersChart from '../../components/charts/TopMembersChart';
import InventoryHealthChart from '../../components/charts/InventoryHealthChart';
import { Calendar, RefreshCcw, TrendingUp, Users, BookOpen, AlertTriangle } from 'lucide-react';

export default function DashboardPage() {
    // Date Filters
    const [endDate, setEndDate] = useState<string>(new Date().toISOString().split('T')[0]);
    const [startDate, setStartDate] = useState<string>(() => {
        const d = new Date();
        d.setDate(d.getDate() - 30);
        return d.toISOString().split('T')[0];
    });

    const { data, isLoading, error: queryError, refetch: fetchAnalytics } = useQuery({
        queryKey: ['analytics', startDate, endDate],
        queryFn: () => getAnalyticsSummary(startDate, endDate),
        placeholderData: keepPreviousData,
    });

    const error = queryError ? queryError.message : null;

    const setRange = (days: number) => {
        const end = new Date();
        const start = new Date();
        start.setDate(end.getDate() - days);
        setEndDate(end.toISOString().split('T')[0]);
        setStartDate(start.toISOString().split('T')[0]);
    };

    if (isLoading && !data) {
        return <div className="p-8 text-center">Loading dashboard...</div>;
    }

    if (error && !data) {
        return <div className="p-8 text-center text-red-500">Error: {error}</div>;
    }

    return (
        <div className="p-8 bg-gray-50 min-h-screen">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>
                    <p className="text-sm text-gray-500 flex items-center gap-2 mt-1">
                        Last updated: {data?.generated_at ? new Date(data.generated_at).toLocaleString() : '-'}
                        {data?.cache_hit && <span className="bg-green-100 text-green-800 text-xs px-2 py-0.5 rounded">Cached</span>}
                    </p>
                </div>

                <div className="flex flex-wrap items-center gap-3 bg-white p-2 rounded-lg shadow-sm">
                    <button onClick={() => setRange(7)} className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded">7D</button>
                    <button onClick={() => setRange(30)} className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded">30D</button>
                    <button onClick={() => setRange(90)} className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded">90D</button>
                    <div className="w-px h-6 bg-gray-300 mx-1"></div>
                    <input
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        className="border rounded px-2 py-1 text-sm"
                    />
                    <span className="text-gray-400">-</span>
                    <input
                        type="date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        className="border rounded px-2 py-1 text-sm"
                    />
                    <button onClick={() => fetchAnalytics()} className="p-2 bg-blue-50 text-blue-600 rounded hover:bg-blue-100">
                        <RefreshCcw size={18} />
                    </button>
                </div>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <KPICard
                    title="Total Books"
                    value={data?.overview.total_books}
                    icon={<BookOpen size={24} className="text-blue-600" />}
                    color="bg-blue-50"
                />
                <KPICard
                    title="Active Borrows"
                    value={data?.overview.active_borrows}
                    subvalue={`${data?.overview.utilization_rate}% Utilization`}
                    icon={<TrendingUp size={24} className="text-green-600" />}
                    color="bg-green-50"
                />
                <KPICard
                    title="Overdue"
                    value={data?.overview.overdue_borrows}
                    icon={<AlertTriangle size={24} className="text-red-600" />}
                    color="bg-red-50"
                />
                <KPICard
                    title="Next 7 Days Forecast"
                    value={data?.forecast.projected_next_7_days_total}
                    subvalue={`~${data?.forecast.daily_projection}/day`}
                    icon={<Calendar size={24} className="text-purple-600" />}
                    color="bg-purple-50"
                />
            </div>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                {/* Main Trend - Spans 2 cols */}
                <div className="lg:col-span-2">
                    <BorrowTrendChart
                        data={data?.daily_borrows || []}
                        title="Borrowing Trend"
                        dataKey="Daily Borrows"
                        color="#4f46e5"
                    />
                </div>

                {/* Daily Active Members */}
                <div>
                    <BorrowTrendChart
                        data={data?.daily_active_members || []}
                        title="Daily Active Members"
                        dataKey="Active Members"
                        color="#10b981"
                    />
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                {/* Top Members */}
                <div className="lg:col-span-1">
                    <TopMembersChart data={data?.top_members || []} />
                </div>

                {/* Inventory Health */}
                <div className="lg:col-span-1">
                    {data?.inventory_health && <InventoryHealthChart data={data.inventory_health} />}
                </div>

                {/* Overdue Breakdown */}
                <div className="lg:col-span-1 bg-white p-4 rounded-lg shadow">
                    <h3 className="text-lg font-semibold mb-4">Overdue Risk Breakdown</h3>
                    <div className="space-y-4">
                        <OverdueBucket label="1-3 Days" count={data?.overdue_breakdown.days_1_3 || 0} color="bg-yellow-100 text-yellow-800" />
                        <OverdueBucket label="4-7 Days" count={data?.overdue_breakdown.days_4_7 || 0} color="bg-orange-100 text-orange-800" />
                        <OverdueBucket label="7+ Days" count={data?.overdue_breakdown.days_7_plus || 0} color="bg-red-100 text-red-800" />
                    </div>
                </div>
            </div>
        </div>
    );
}

interface KPICardProps {
    title: string;
    value?: number | string;
    subvalue?: string;
    icon: React.ReactNode;
    color: string;
}

function KPICard({ title, value, subvalue, icon, color }: KPICardProps) {
    return (
        <div className="bg-white p-6 rounded-lg shadow flex items-center justify-between">
            <div>
                <p className="text-sm font-medium text-gray-500">{title}</p>
                <p className="text-2xl font-bold mt-1">{value !== undefined ? value : '-'}</p>
                {subvalue && <p className="text-xs text-gray-400 mt-1">{subvalue}</p>}
            </div>
            <div className={`p-3 rounded-full ${color}`}>
                {icon}
            </div>
        </div>
    );
}

interface OverdueBucketProps {
    label: string;
    count: number;
    color: string;
}

function OverdueBucket({ label, count, color }: OverdueBucketProps) {
    return (
        <div className="flex items-center justify-between p-3 border rounded-lg">
            <span className="font-medium text-gray-600">{label}</span>
            <span className={`px-3 py-1 rounded-full text-sm font-bold ${color}`}>
                {count}
            </span>
        </div>
    );
}
