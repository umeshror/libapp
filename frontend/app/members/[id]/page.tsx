'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
    MemberCoreDetails,
    MemberBorrowHistoryItem,
    MemberAnalyticsResponse,
    ActivityTrendItem
} from '@/types'
import {
    getMemberCoreDetails,
    getMemberBorrowHistory,
    getMemberAnalytics
} from '@/lib/api'
import { useReturnBook } from '@/hooks/useReturnBook'
import { toast } from 'sonner'
import ConfirmationModal from '@/components/ConfirmationModal'
import {
    Calendar,
    Mail,
    Phone,
    Clock,
    TrendingUp,
    AlertCircle,
    CheckCircle,
    ChevronLeft,
    ChevronRight,
    History,
    Activity,
    User,
    BookOpen,
    Filter,
    ArrowUpDown,
    RotateCcw,
    Loader2
} from 'lucide-react'
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    AreaChart,
    Area
} from 'recharts'
import { format, differenceInDays } from 'date-fns'

export default function MemberDetailPage() {
    const params = useParams()
    const router = useRouter()
    const memberId = params.id as string

    // State
    const [core, setCore] = useState<MemberCoreDetails | null>(null)
    const [history, setHistory] = useState<MemberBorrowHistoryItem[]>([])
    const [analytics, setAnalytics] = useState<MemberAnalyticsResponse | null>(null)
    const [loading, setLoading] = useState(true)
    const [returningId, setReturningId] = useState<string | null>(null)
    const [confirmingReturn, setConfirmingReturn] = useState<{ id: string, title: string } | null>(null)
    const [error, setError] = useState<string | null>(null)

    // Pagination & Filter State
    const [page, setPage] = useState(1)
    const [limit] = useState(10)
    const [total, setTotal] = useState(0)
    const [status, setStatus] = useState<'all' | 'active' | 'returned'>('all')
    const [sort, setSort] = useState<'borrowed_at' | 'returned_at'>('borrowed_at')
    const [order, setOrder] = useState<'asc' | 'desc'>('desc')

    const fetchData = useCallback(async () => {
        try {
            setLoading(true)
            const [coreData, analyticsData] = await Promise.all([
                getMemberCoreDetails(memberId),
                getMemberAnalytics(memberId)
            ])
            setCore(coreData)
            setAnalytics(analyticsData)

            // Initial history fetch
            const historyData = await getMemberBorrowHistory(memberId, limit, 0, status, sort, order)
            setHistory(historyData.data)
            setTotal(historyData.meta.total)

            setError(null)
        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to load member data';
            setError(errorMessage)
        } finally {
            setLoading(false)
        }
    }, [memberId, limit, status, sort, order])

    const fetchHistoryOnly = useCallback(async (p: number) => {
        try {
            const offset = (p - 1) * limit
            const historyData = await getMemberBorrowHistory(memberId, limit, offset, status, sort, order)
            setHistory(historyData.data)
            setTotal(historyData.meta.total)
        } catch (err: unknown) {
            console.error('Failed to load history', err)
        }
    }, [memberId, limit, status, sort, order])

    useEffect(() => {
        fetchData()
    }, [fetchData])

    useEffect(() => {
        if (!loading) {
            fetchHistoryOnly(page)
        }
    }, [page, fetchHistoryOnly, loading])

    const { returnBook, isPending: isReturning } = useReturnBook({
        onSuccess: () => {
            setConfirmingReturn(null)
            fetchData()
        }
    })

    const handleReturn = async (borrowId: string, bookTitle: string) => {
        setConfirmingReturn({ id: borrowId, title: bookTitle })
    }

    const executeReturn = async () => {
        if (!confirmingReturn) return
        returnBook(confirmingReturn.id)
    }

    const getRiskBadge = (level: string) => {
        const colors = {
            'LOW': 'bg-emerald-100 text-emerald-700 border-emerald-200',
            'MEDIUM': 'bg-amber-100 text-amber-700 border-amber-200',
            'HIGH': 'bg-rose-100 text-rose-700 border-rose-200'
        }
        return (
            <span className={`px-3 py-1 rounded-full text-xs font-bold border ${colors[level as keyof typeof colors]}`}>
                {level} RISK
            </span>
        )
    }

    if (loading && !core) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="max-w-4xl mx-auto mt-12 p-8 bg-white rounded-2xl shadow-sm border border-rose-100 text-center">
                <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-4" />
                <h2 className="text-xl font-bold text-slate-800 mb-2">Something went wrong</h2>
                <p className="text-slate-500 mb-6">{error}</p>
                <button onClick={() => fetchData()} className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">
                    Try Again
                </button>
            </div>
        )
    }

    const activeBorrows = history.filter(h => h.returned_at === null)

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in fade-in duration-500">
            {/* Header & Breadcrumb */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1">
                    <Link href="/members" className="flex items-center text-slate-500 hover:text-indigo-600 transition-colors text-sm group">
                        <ChevronLeft className="w-4 h-4 mr-1 group-hover:-translate-x-1 transition-transform" />
                        Back to Members
                    </Link>
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center text-white">
                            <User className="w-6 h-6" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold text-slate-900 tracking-tight">{core?.member.name}</h1>
                            <p className="text-slate-500 flex items-center gap-2">
                                <Mail className="w-4 h-4" /> {core?.member.email}
                            </p>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-3 self-end md:self-auto">
                    {core && getRiskBadge(core.analytics_summary.risk_level)}
                    <div className="px-4 py-2 bg-white rounded-lg border border-slate-200 shadow-sm text-sm font-medium text-slate-600">
                        Member for {core?.membership_duration_days} days
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Main Content */}
                <div className="lg:col-span-2 space-y-8">

                    {/* Active Borrows */}
                    <section className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                            <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                                <BookOpen className="w-5 h-5 text-indigo-500" />
                                Current Active Borrows
                                <span className="bg-indigo-100 text-indigo-700 text-xs py-0.5 px-2 rounded-full font-bold ml-1">
                                    {core?.active_borrows_count} Active
                                </span>
                            </h2>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead className="bg-slate-50/50 text-slate-500 text-xs font-semibold uppercase tracking-wider">
                                    <tr>
                                        <th className="px-6 py-3">Book Title</th>
                                        <th className="px-6 py-3">Borrowed At</th>
                                        <th className="px-6 py-3">Due Date</th>
                                        <th className="px-6 py-3 text-right">Status</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 text-sm">
                                    {activeBorrows.length > 0 ? activeBorrows.map((record, i) => {
                                        const now = new Date();
                                        const dueDate = new Date(record.due_date);
                                        const daysRemaining = differenceInDays(dueDate, now);

                                        return (
                                            <tr key={i} className="hover:bg-slate-50 transition-colors group">
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <Link href={`/books/${record.book_id}`} target="_blank" className="font-medium text-slate-900 hover:text-indigo-600 hover:underline transition-colors block max-w-[200px] truncate" title={record.book_title}>
                                                        {record.book_title}
                                                    </Link>
                                                </td>
                                                <td className="px-6 py-4 text-slate-500">
                                                    {format(new Date(record.borrowed_at), 'MMM dd, yyyy')}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className={`font-medium ${daysRemaining < 0 ? 'text-rose-600' : 'text-slate-700'}`}>
                                                        {format(dueDate, 'MMM dd, yyyy')}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-right flex items-center justify-end gap-3">
                                                    {daysRemaining < 0 ? (
                                                        <span className="text-rose-600 font-bold bg-rose-50 px-2 py-1 rounded text-xs animate-pulse">
                                                            {Math.abs(daysRemaining)}d OVERDUE
                                                        </span>
                                                    ) : (
                                                        <span className="text-emerald-600 font-bold bg-emerald-50 px-2 py-1 rounded text-xs">
                                                            {daysRemaining}d REMAINING
                                                        </span>
                                                    )}
                                                    <button
                                                        onClick={() => handleReturn(record.id, record.book_title)}
                                                        disabled={isReturning}
                                                        className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-bold hover:bg-indigo-600 transition-all shadow-sm disabled:opacity-50"
                                                        title="Process Return"
                                                    >
                                                        {isReturning ? (
                                                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                        ) : (
                                                            <RotateCcw className="w-3.5 h-3.5" />
                                                        )}
                                                        Return
                                                    </button>
                                                </td>
                                            </tr>
                                        )
                                    }) : (
                                        <tr>
                                            <td colSpan={4} className="px-6 py-12 text-center text-slate-400 italic">
                                                No books currently borrowed
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </section>

                    {/* Borrow History */}
                    <section className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                        <div className="px-6 py-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50/50">
                            <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                                <History className="w-5 h-5 text-indigo-500" />
                                Borrow History
                            </h2>
                            <div className="flex items-center gap-2">
                                <div className="flex items-center gap-1 bg-white border border-slate-200 rounded-lg px-2 py-1 shadow-sm">
                                    <Filter className="w-3.5 h-3.5 text-slate-400" />
                                    <select
                                        className="text-xs font-semibold text-slate-600 bg-transparent border-none focus:ring-0 cursor-pointer"
                                        value={status}
                                        onChange={(e) => {
                                            setStatus(e.target.value as 'all' | 'active' | 'returned')
                                            setPage(1)
                                        }}
                                    >
                                        <option value="all">All Records</option>
                                        <option value="active">Active Only</option>
                                        <option value="returned">Returned Only</option>
                                    </select>
                                </div>
                                <div className="flex items-center gap-1 bg-white border border-slate-200 rounded-lg px-2 py-1 shadow-sm">
                                    <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
                                    <select
                                        className="text-xs font-semibold text-slate-600 bg-transparent border-none focus:ring-0 cursor-pointer"
                                        value={sort}
                                        onChange={(e) => setSort(e.target.value as 'borrowed_at' | 'returned_at')}
                                    >
                                        <option value="borrowed_at">Date Borrowed</option>
                                        <option value="returned_at">Date Returned</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead className="bg-slate-50/50 text-slate-500 text-xs font-semibold uppercase tracking-wider">
                                    <tr>
                                        <th className="px-6 py-3">Book</th>
                                        <th className="px-6 py-3">Borrowed</th>
                                        <th className="px-6 py-3">Returned</th>
                                        <th className="px-6 py-3">Duration</th>
                                        <th className="px-6 py-3 text-right">Result</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 text-sm">
                                    {history.map((item, idx) => (
                                        <tr key={idx} className="hover:bg-slate-50 transition-colors group">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Link href={`/books/${item.book_id}`} target="_blank" className="font-medium text-slate-900 hover:text-indigo-600 hover:underline transition-colors block max-w-[150px] truncate" title={item.book_title}>
                                                    {item.book_title}
                                                </Link>
                                            </td>
                                            <td className="px-6 py-4 text-slate-500">
                                                {format(new Date(item.borrowed_at), 'MMM dd, yyyy')}
                                            </td>
                                            <td className="px-6 py-4 text-slate-500">
                                                {item.returned_at ? format(new Date(item.returned_at), 'MMM dd, yyyy') : '-'}
                                            </td>
                                            <td className="px-6 py-4 text-slate-500">
                                                {item.duration_days !== null ? `${item.duration_days} days` : 'Ongoing'}
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                {item.was_overdue ? (
                                                    <span className="inline-flex items-center text-rose-600 font-bold bg-rose-50 px-2 py-0.5 rounded text-[10px]">
                                                        OVERDUE
                                                    </span>
                                                ) : item.returned_at ? (
                                                    <span className="inline-flex items-center text-emerald-600 font-bold bg-emerald-50 px-2 py-0.5 rounded text-[10px]">
                                                        ON TIME
                                                    </span>
                                                ) : (
                                                    <span className="inline-flex items-center text-indigo-600 font-bold bg-indigo-50 px-2 py-0.5 rounded text-[10px]">
                                                        IN PROGRESS
                                                    </span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {/* Pagination */}
                        <div className="px-6 py-4 bg-slate-50/30 border-t border-slate-100 flex items-center justify-between">
                            <span className="text-sm text-slate-500 font-medium">
                                Showing <span className="text-slate-900">{(page - 1) * limit + 1}</span> to <span className="text-slate-900">{Math.min(page * limit, total)}</span> of <span className="text-slate-900">{total}</span>
                            </span>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setPage(p => Math.max(1, p - 1))}
                                    disabled={page === 1}
                                    className="p-2 bg-white border border-slate-200 rounded-lg shadow-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors"
                                >
                                    <ChevronLeft className="w-4 h-4" />
                                </button>
                                <button
                                    onClick={() => setPage(p => p + 1)}
                                    disabled={page * limit >= total}
                                    className="p-2 bg-white border border-slate-200 rounded-lg shadow-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors"
                                >
                                    <ChevronRight className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    </section>
                </div>

                {/* Sidebar Analytics */}
                <div className="space-y-8">
                    {/* KPI Cards */}
                    <section className="bg-indigo-600 rounded-2xl p-6 text-white shadow-xl shadow-indigo-100 space-y-6 relative overflow-hidden">
                        <div className="absolute -top-12 -right-12 w-48 h-48 bg-white/10 rounded-full blur-3xl"></div>
                        <div className="flex items-center justify-between relative">
                            <h3 className="text-lg font-bold opacity-90">Performance Summary</h3>
                            <Activity className="w-5 h-5 opacity-80" />
                        </div>
                        <div className="grid grid-cols-2 gap-4 relative">
                            <div className="bg-white/10 rounded-xl p-3 backdrop-blur-sm">
                                <p className="text-xs opacity-70 mb-1">Total Borrowed</p>
                                <p className="text-2xl font-bold">{analytics?.total_books_borrowed}</p>
                            </div>
                            <div className="bg-white/10 rounded-xl p-3 backdrop-blur-sm">
                                <p className="text-xs opacity-70 mb-1">Overdue Rate</p>
                                <p className="text-2xl font-bold">{analytics?.overdue_rate_percent}%</p>
                            </div>
                            <div className="bg-white/10 rounded-xl p-3 backdrop-blur-sm">
                                <p className="text-xs opacity-70 mb-1">Avg. Duration</p>
                                <p className="text-2xl font-bold">{analytics?.average_borrow_duration}d</p>
                            </div>
                            <div className="bg-white/10 rounded-xl p-3 backdrop-blur-sm">
                                <p className="text-xs opacity-70 mb-1">Borrow Freq.</p>
                                <p className="text-2xl font-bold">{analytics?.borrow_frequency_per_month}/mo</p>
                            </div>
                        </div>
                    </section>

                    {/* Behavior Insights */}
                    <section className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
                        <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-indigo-500" />
                            Behavioral Insights
                        </h3>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                                <div>
                                    <p className="text-xs text-slate-500 font-medium">Favorite Author</p>
                                    <p className="text-sm font-bold text-slate-900">{analytics?.favorite_author || 'N/A'}</p>
                                </div>
                                <User className="w-5 h-5 text-indigo-300" />
                            </div>
                            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                                <div>
                                    <p className="text-xs text-slate-500 font-medium">Longest Borrow</p>
                                    <p className="text-sm font-bold text-slate-900">{analytics?.longest_borrow_duration} Days</p>
                                </div>
                                <Clock className="w-5 h-5 text-indigo-300" />
                            </div>
                            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                                <div>
                                    <p className="text-xs text-slate-500 font-medium">Shortest Borrow</p>
                                    <p className="text-sm font-bold text-slate-900">{analytics?.shortest_borrow_duration} Days</p>
                                </div>
                                <TrendingUp className="w-5 h-5 text-indigo-300" />
                            </div>
                        </div>

                        {/* Chart */}
                        {analytics?.activity_trend && analytics.activity_trend.length > 0 && (
                            <div className="pt-4 space-y-4 border-t border-slate-100">
                                <p className="text-sm font-bold text-slate-800">Borrowing Trend</p>
                                <div className="h-32 w-full">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <AreaChart data={analytics.activity_trend}>
                                            <defs>
                                                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.1} />
                                                    <stop offset="95%" stopColor="#4f46e5" stopOpacity={0} />
                                                </linearGradient>
                                            </defs>
                                            <Area
                                                type="monotone"
                                                dataKey="count"
                                                stroke="#4f46e5"
                                                strokeWidth={2}
                                                fillOpacity={1}
                                                fill="url(#colorCount)"
                                            />
                                            <Tooltip
                                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                                labelStyle={{ fontWeight: 'bold' }}
                                            />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        )}
                    </section>
                </div>
            </div>

            <ConfirmationModal
                isOpen={!!confirmingReturn}
                onClose={() => setConfirmingReturn(null)}
                onConfirm={executeReturn}
                isLoading={isReturning}
                title="Confirm Return"
                description={`Are you sure you want to return "${confirmingReturn?.title}"?`}
                confirmText="Confirm Return"
                isDanger={false}
            />
        </div>
    )
}
