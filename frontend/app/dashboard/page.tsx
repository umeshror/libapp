"use client"
import React, { useState } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getAnalyticsSummary } from '../../lib/api';
import BorrowTrendChart from '../../components/charts/BorrowTrendChart';
import TopMembersChart from '../../components/charts/TopMembersChart';
import InventoryHealthChart from '../../components/charts/InventoryHealthChart';
import PopularBooks from '../../components/dashboard/PopularBooks';
import RecentActivity from '../../components/dashboard/RecentActivity';
import { Calendar, RefreshCcw, TrendingUp, Users, BookOpen, AlertTriangle, ArrowUpRight, ArrowDownRight, Layers } from 'lucide-react';

export default function DashboardPage() {
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
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
                <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                <p className="text-gray-500 font-medium">Preparing your insights...</p>
            </div>
        );
    }

    if (error && !data) {
        return (
            <div className="p-8 flex flex-col items-center justify-center min-h-[60vh] text-center">
                <div className="bg-red-50 p-4 rounded-full text-red-600 mb-4">
                    <AlertTriangle size={48} />
                </div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Analytics Unavailable</h2>
                <p className="text-gray-500 max-w-md mb-6">{error}</p>
                <button onClick={() => fetchAnalytics()} className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                    Try Again
                </button>
            </div>
        );
    }

    return (
        <div className="p-4 md:p-8 bg-[#fafafa] min-h-screen">
            {/* Header Section */}
            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end mb-10 gap-6">
                <div>
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-blue-600 rounded-lg text-white">
                            <Layers size={20} />
                        </div>
                        <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">System Insights</h1>
                    </div>
                    <p className="text-gray-500 font-medium flex items-center gap-2">
                        Real-time performance metrics for your library
                        <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
                        <span className="text-xs text-gray-400">
                            Updated {data?.generated_at ? new Date(data.generated_at).toLocaleTimeString() : '-'}
                        </span>
                    </p>
                </div>

                <div className="flex flex-wrap items-center gap-2 bg-white p-1.5 rounded-xl shadow-sm border border-gray-100">
                    <div className="flex gap-1 p-1 bg-gray-50 rounded-lg">
                        {[7, 30, 90].map((days) => (
                            <button
                                key={days}
                                onClick={() => setRange(days)}
                                className={`px-4 py-1.5 text-xs font-bold rounded-md transition-all ${startDate === new Date(new Date().setDate(new Date().getDate() - days)).toISOString().split('T')[0]
                                        ? 'bg-white shadow-sm text-blue-600'
                                        : 'text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                {days}D
                            </button>
                        ))}
                    </div>
                    <div className="w-px h-8 bg-gray-100 mx-1 hidden sm:block"></div>
                    <div className="flex items-center gap-2 px-2">
                        <input
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            className="bg-transparent border-none text-xs font-bold text-gray-700 focus:ring-0 cursor-pointer"
                        />
                        <span className="text-gray-300">→</span>
                        <input
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            className="bg-transparent border-none text-xs font-bold text-gray-700 focus:ring-0 cursor-pointer"
                        />
                    </div>
                    <button
                        onClick={() => fetchAnalytics()}
                        className="ml-2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all shadow-md shadow-blue-100"
                    >
                        <RefreshCcw size={16} />
                    </button>
                </div>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
                <KPICard
                    title="Library Volume"
                    value={data?.overview.total_books}
                    description="Total books in catalog"
                    icon={<BookOpen size={20} />}
                    trend="+1.2% vs last month"
                    color="text-blue-600"
                    bgColor="bg-blue-50"
                />
                <KPICard
                    title="Active Borrow"
                    value={data?.overview.active_borrows}
                    description={`${data?.overview.utilization_rate}% capacity utilized`}
                    icon={<TrendingUp size={20} />}
                    trend="+5.4% activity"
                    color="text-emerald-600"
                    bgColor="bg-emerald-50"
                />
                <KPICard
                    title="Overdue Risk"
                    value={data?.overview.overdue_borrows}
                    description="Requires immediate attention"
                    icon={<AlertTriangle size={20} />}
                    trend="Check breakdown"
                    color="text-rose-600"
                    bgColor="bg-rose-50"
                    isAlert={data?.overview.overdue_borrows ? data.overview.overdue_borrows > 0 : false}
                />
                <KPICard
                    title="Demand Forecast"
                    value={data?.forecast.projected_next_7_days_total}
                    description={`Avg ${data?.forecast.daily_projection} borrows/day`}
                    icon={<Calendar size={20} />}
                    trend="Next 7 days"
                    color="text-violet-600"
                    bgColor="bg-violet-50"
                />
            </div>

            {/* Main Charts & Activity Row */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 mb-10">
                {/* Main Trend Chart - 8 cols */}
                <div className="xl:col-span-8 flex flex-col gap-6">
                    <BorrowTrendChart
                        data={data?.daily_borrows || []}
                        title="Circulation velocity"
                        dataKey="Daily Borrows"
                        color="#2563eb"
                    />

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <BorrowTrendChart
                            data={data?.daily_active_members || []}
                            title="Member Engagement"
                            dataKey="Active Members"
                            color="#10b981"
                        />
                        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                            <h3 className="text-lg font-semibold mb-6 text-gray-800">Inventory Status</h3>
                            {data?.inventory_health && <InventoryHealthChart data={data.inventory_health} />}
                        </div>
                    </div>
                </div>

                {/* Right Sidebar - 4 cols */}
                <div className="xl:col-span-4 flex flex-col gap-6">
                    <RecentActivity data={data?.recent_activity || []} />
                    <PopularBooks data={data?.popular_books || []} />
                </div>
            </div>

            {/* Bottom Row - More Lists */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-1">
                    <TopMembersChart data={data?.top_members || []} />
                </div>

                <div className="lg:col-span-2 bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-lg font-semibold text-gray-800">Overdue Risk Distribution</h3>
                        <span className="text-xs bg-rose-50 text-rose-600 px-2 py-1 rounded font-bold uppercase">Critical Items</span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <OverdueMetric
                            label="Early Warning"
                            sublabel="1-3 Days"
                            count={data?.overdue_breakdown.days_1_3 || 0}
                            color="text-amber-600"
                            bgColor="bg-amber-50"
                        />
                        <OverdueMetric
                            label="At Risk"
                            sublabel="4-7 Days"
                            count={data?.overdue_breakdown.days_4_7 || 0}
                            color="text-orange-600"
                            bgColor="bg-orange-50"
                        />
                        <OverdueMetric
                            label="Critical"
                            sublabel="7+ Days"
                            count={data?.overdue_breakdown.days_7_plus || 0}
                            color="text-rose-600"
                            bgColor="bg-rose-50"
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}

interface KPICardProps {
    title: string;
    value?: number | string;
    description: string;
    icon: React.ReactNode;
    trend: string;
    color: string;
    bgColor: string;
    isAlert?: boolean;
}

function KPICard({ title, value, description, icon, trend, color, bgColor, isAlert }: KPICardProps) {
    return (
        <div className={`bg-white p-6 rounded-2xl shadow-sm border border-gray-100 transition-all hover:shadow-md group ${isAlert ? 'ring-2 ring-rose-500 ring-offset-2' : ''}`}>
            <div className="flex justify-between items-start mb-4">
                <div className={`p-2.5 rounded-xl ${bgColor} ${color} group-hover:scale-110 transition-transform`}>
                    {icon}
                </div>
                {isAlert && (
                    <span className="flex h-2 w-2 rounded-full bg-rose-500 animate-ping"></span>
                )}
            </div>
            <div>
                <p className="text-sm font-bold text-gray-400 uppercase tracking-tight mb-1">{title}</p>
                <div className="flex items-baseline gap-2">
                    <h3 className="text-3xl font-black text-gray-900 leading-none">
                        {value !== undefined ? value.toLocaleString() : '-'}
                    </h3>
                </div>
                <p className="text-xs font-semibold text-gray-500 mt-2 mb-4 leading-relaxed">{description}</p>
                <div className="flex items-center gap-1.5 pt-3 border-t border-gray-50">
                    <div className={`p-1 rounded-full ${bgColor} ${color}`}>
                        {trend.includes('+') ? <ArrowUpRight size={10} /> : <ArrowDownRight size={10} />}
                    </div>
                    <span className={`text-[10px] font-bold uppercase tracking-wider ${color}`}>{trend}</span>
                </div>
            </div>
        </div>
    );
}

function OverdueMetric({ label, sublabel, count, color, bgColor }: { label: string, sublabel: string, count: number, color: string, bgColor: string }) {
    return (
        <div className={`p-5 rounded-2xl ${bgColor} border-2 border-transparent hover:border-white transition-all`}>
            <p className={`text-xs font-black uppercase tracking-widest ${color} opacity-70 mb-1`}>{label}</p>
            <p className="text-sm font-bold text-gray-500 mb-3">{sublabel}</p>
            <div className="flex items-baseline gap-2">
                <span className={`text-4xl font-black ${color}`}>{count}</span>
                <span className="text-xs font-bold text-gray-400 uppercase">Items</span>
            </div>
        </div>
    );
}
