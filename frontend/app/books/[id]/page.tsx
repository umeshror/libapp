'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
    BookDetailResponse,
    BorrowHistoryItem,
    BorrowerInfo
} from '@/types'
import { getBookDetails, returnBook } from '@/lib/api'
import {
    ArrowLeft,
    Book as BookIcon,
    Users,
    History,
    BarChart3,
    Clock,
    Trophy,
    AlertCircle,
    ChevronLeft,
    ChevronRight,
    Calendar,
    ArrowUpRight,
    RotateCcw,
    Loader2
} from 'lucide-react'

export default function BookDetailPage() {
    const params = useParams()
    const router = useRouter()
    const id = params.id as string

    const [data, setData] = useState<BookDetailResponse | null>(null)
    const [loading, setLoading] = useState(true)
    const [returningId, setReturningId] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [historyOffset, setHistoryOffset] = useState(0)
    const HISTORY_LIMIT = 5

    const fetchData = useCallback(async (offset: number) => {
        try {
            setLoading(true)
            const detail = await getBookDetails(id, HISTORY_LIMIT, offset)
            setData(detail)
            setError(null)
        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to load book details';
            setError(errorMessage)
        } finally {
            setLoading(false)
        }
    }, [id])

    useEffect(() => {
        fetchData(0)
    }, [fetchData])

    const handlePageChange = (newOffset: number) => {
        setHistoryOffset(newOffset)
        fetchData(newOffset)
    }

    const handleReturn = async (borrowId: string) => {
        try {
            setReturningId(borrowId)
            await returnBook(borrowId)
            await fetchData(historyOffset)
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Return failed'
            alert(msg)
        } finally {
            setReturningId(null)
        }
    }

    if (loading && !data) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                <p className="text-gray-500 animate-pulse">Loading comprehensive book data...</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="max-w-3xl mx-auto mt-10 p-6 bg-red-50 border border-red-100 rounded-2xl flex flex-col items-center text-center">
                <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
                <h2 className="text-xl font-bold text-red-900 mb-2">Something went wrong</h2>
                <p className="text-red-700 mb-6">{error}</p>
                <button
                    onClick={() => fetchData(historyOffset)}
                    className="px-6 py-2 bg-red-600 text-white rounded-xl hover:bg-red-700 transition-colors shadow-lg shadow-red-200"
                >
                    Try Again
                </button>
            </div>
        )
    }

    if (!data) return null

    const { book, current_borrowers, borrow_history, analytics } = data

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {/* Header & Navigation */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div className="space-y-2">
                    <button
                        onClick={() => router.back()}
                        className="group flex items-center text-sm font-medium text-gray-500 hover:text-blue-600 transition-colors"
                    >
                        <ArrowLeft className="w-4 h-4 mr-1 group-hover:-translate-x-1 transition-transform" />
                        Back to Books
                    </button>
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-600 text-white rounded-2xl shadow-xl shadow-blue-100">
                            <BookIcon className="w-8 h-8" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">{book.title}</h1>
                            <p className="text-lg text-gray-500 font-medium">by <span className="text-gray-900">{book.author}</span></p>
                        </div>
                    </div>
                </div>
                <div className="flex gap-3">
                    <span className={`px-4 py-1.5 rounded-full text-sm font-bold shadow-sm ${analytics.availability_status === 'AVAILABLE' ? 'bg-green-100 text-green-700 border border-green-200' :
                        analytics.availability_status === 'LOW_STOCK' ? 'bg-amber-100 text-amber-700 border border-amber-200' :
                            'bg-red-100 text-red-700 border border-red-200'
                        }`}>
                        {analytics.availability_status.replace('_', ' ')}
                    </span>
                    <span className="px-4 py-1.5 bg-gray-100 text-gray-700 border border-gray-200 rounded-full text-sm font-bold">
                        ISBN: {book.isbn}
                    </span>
                </div>
            </div>

            {/* Analytics KPI Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    label="Total Borrows"
                    value={analytics.total_times_borrowed.toString()}
                    icon={<BarChart3 className="w-5 h-5" />}
                    color="text-blue-600"
                    bgColor="bg-blue-50"
                />
                <StatCard
                    label="Avg. Duration"
                    value={`${analytics.average_borrow_duration} Days`}
                    icon={<Clock className="w-5 h-5" />}
                    color="text-purple-600"
                    bgColor="bg-purple-50"
                />
                <StatCard
                    label="Popularity Rank"
                    value={`#${analytics.popularity_rank}`}
                    icon={<Trophy className="w-5 h-5" />}
                    color="text-amber-600"
                    bgColor="bg-amber-50"
                />
                <StatCard
                    label="Copies Available"
                    value={`${book.available_copies} / ${book.total_copies}`}
                    icon={<Users className="w-5 h-5" />}
                    color="text-emerald-600"
                    bgColor="bg-emerald-50"
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Main Content: Current Borrowers & History */}
                <div className="lg:col-span-2 space-y-8">
                    {/* Current Borrowers */}
                    <section className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
                        <div className="p-6 border-b border-gray-50 bg-gray-50/50 flex items-center justify-between">
                            <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                                <Users className="w-5 h-5 text-blue-600" />
                                Current Borrowers
                            </h2>
                            <span className="px-2.5 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-bold">
                                {current_borrowers.length} Active
                            </span>
                        </div>
                        <div className="overflow-x-auto">
                            {current_borrowers.length > 0 ? (
                                <table className="w-full text-left">
                                    <thead>
                                        <tr className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                                            <th className="px-6 py-4">Member</th>
                                            <th className="px-6 py-4">Borrowed At</th>
                                            <th className="px-6 py-4">Status</th>
                                            <th className="px-6 py-4 text-right">Action</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-50 text-sm">
                                        {current_borrowers.map((borrower) => (
                                            <tr key={borrower.member_id} className="hover:bg-gray-50/50 transition-colors group">
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <Link href={`/members/${borrower.member_id}`} target="_blank" className="flex items-center gap-3 group/link">
                                                        <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold text-xs group-hover/link:bg-blue-200 transition-colors">
                                                            {borrower.name.charAt(0)}
                                                        </div>
                                                        <span className="font-semibold text-gray-900 group-hover/link:text-blue-600 group-hover/link:underline transition-colors">{borrower.name}</span>
                                                    </Link>
                                                </td>
                                                <td className="px-6 py-4 text-gray-500 whitespace-nowrap">
                                                    {new Date(borrower.borrowed_at).toLocaleDateString()}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${borrower.days_until_due < 0 ? 'bg-red-100 text-red-700' :
                                                        borrower.days_until_due <= 2 ? 'bg-amber-100 text-amber-700' :
                                                            'bg-emerald-100 text-emerald-700'
                                                        }`}>
                                                        {borrower.days_until_due < 0 ? `Overdue (${Math.abs(borrower.days_until_due)}d)` :
                                                            borrower.days_until_due === 0 ? 'Due Today' :
                                                                `Due in ${borrower.days_until_due}d`}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-right whitespace-nowrap">
                                                    <button
                                                        onClick={() => handleReturn(borrower.borrow_id)}
                                                        disabled={returningId === borrower.borrow_id}
                                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-bold hover:bg-blue-600 transition-all shadow-sm disabled:opacity-50"
                                                        title="Process Return"
                                                    >
                                                        {returningId === borrower.borrow_id ? (
                                                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                        ) : (
                                                            <RotateCcw className="w-3.5 h-3.5" />
                                                        )}
                                                        Return
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            ) : (
                                <div className="p-12 text-center">
                                    <div className="bg-gray-50 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4">
                                        <Users className="w-8 h-8 text-gray-300" />
                                    </div>
                                    <p className="text-gray-500 font-medium italic">No members are currently reading this book.</p>
                                </div>
                            )}
                        </div>
                    </section>

                    {/* Borrow History */}
                    <section className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
                        <div className="p-6 border-b border-gray-50 bg-gray-50/50 flex items-center justify-between">
                            <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                                <History className="w-5 h-5 text-purple-600" />
                                Borrow History
                            </h2>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => handlePageChange(historyOffset - HISTORY_LIMIT)}
                                    disabled={historyOffset === 0 || loading}
                                    className="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-30 transition-all"
                                >
                                    <ChevronLeft className="w-4 h-4" />
                                </button>
                                <span className="text-xs font-bold text-gray-500 px-2">
                                    {Math.floor(historyOffset / HISTORY_LIMIT) + 1}
                                </span>
                                <button
                                    onClick={() => handlePageChange(historyOffset + HISTORY_LIMIT)}
                                    disabled={!borrow_history.meta.has_more || loading}
                                    className="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-30 transition-all"
                                >
                                    <ChevronRight className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                        <div className="overflow-x-auto">
                            {borrow_history.data.length > 0 ? (
                                <table className="w-full text-left">
                                    <thead>
                                        <tr className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                                            <th className="px-6 py-4">Member</th>
                                            <th className="px-6 py-4">Timeline</th>
                                            <th className="px-6 py-4 text-right">Duration</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-50 text-sm">
                                        {borrow_history.data.map((item, idx) => (
                                            <tr key={idx} className="hover:bg-gray-50/50 transition-colors">
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <Link href={`/members/${item.member_id}`} target="_blank" className="font-semibold text-gray-900 hover:text-blue-600 hover:underline transition-colors">
                                                        {item.member_name}
                                                    </Link>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="flex flex-col text-xs space-y-0.5">
                                                        <span className="text-gray-400">Borrowed: {new Date(item.borrowed_at).toLocaleDateString()}</span>
                                                        <span className="text-emerald-500 font-medium">Returned: {new Date(item.returned_at).toLocaleDateString()}</span>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 text-right whitespace-nowrap">
                                                    <span className="px-2.5 py-1 bg-gray-100 text-gray-700 rounded-lg font-mono text-xs font-bold">
                                                        {item.duration_days} Days
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            ) : (
                                <div className="p-12 text-center text-gray-500 italic">
                                    No transaction history yet.
                                </div>
                            )}
                        </div>
                    </section>
                </div>

                {/* Sidebar: Insights & Stock */}
                <div className="space-y-8">
                    {/* Inventory Health */}
                    <div className="bg-gradient-to-br from-blue-600 to-blue-800 rounded-3xl p-8 text-white shadow-xl shadow-blue-200">
                        <label className="text-blue-100 text-xs font-extrabold uppercase tracking-widest mb-4 block">Book Inventory</label>
                        <div className="space-y-6">
                            <div>
                                <div className="flex items-end justify-between mb-2">
                                    <span className="text-3xl font-black">{Math.round((book.available_copies / book.total_copies) * 100)}%</span>
                                    <span className="text-blue-200 text-sm font-medium">Available</span>
                                </div>
                                <div className="h-3 bg-blue-900/40 rounded-full overflow-hidden border border-white/10">
                                    <div
                                        className="h-full bg-white rounded-full shadow-[0_0_10px_rgba(255,255,255,0.5)] transition-all duration-1000"
                                        style={{ width: `${(book.available_copies / book.total_copies) * 100}%` }}
                                    ></div>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-white/10 rounded-2xl p-4 backdrop-blur-sm">
                                    <span className="text-blue-100 text-xs font-bold block mb-1">Total</span>
                                    <span className="text-xl font-black">{book.total_copies}</span>
                                </div>
                                <div className="bg-white/10 rounded-2xl p-4 backdrop-blur-sm">
                                    <span className="text-blue-100 text-xs font-bold block mb-1">On Borrow</span>
                                    <span className="text-xl font-black">{book.total_copies - book.available_copies}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Quick Insights Card */}
                    <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100 space-y-6">
                        <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                            <ArrowUpRight className="w-5 h-5 text-emerald-500" />
                            Behavioral Insights
                        </h3>
                        <div className="space-y-4">
                            <InsightRow
                                label="Longest Borrow"
                                value={analytics.longest_borrow_duration ? `${analytics.longest_borrow_duration} Days` : 'N/A'}
                                icon={<Calendar className="w-4 h-4" />}
                            />
                            <InsightRow
                                label="Return Delays"
                                value={analytics.return_delay_count.toString()}
                                highlight={analytics.return_delay_count > 0}
                                icon={<AlertCircle className="w-4 h-4" />}
                            />
                            <InsightRow
                                label="Last Borrowed"
                                value={analytics.last_borrowed_at ? new Date(analytics.last_borrowed_at).toLocaleDateString() : 'Never'}
                                icon={<Clock className="w-4 h-4" />}
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

interface StatCardProps {
    label: string;
    value: string;
    icon: React.ReactNode;
    color: string;
    bgColor: string;
}

function StatCard({ label, value, icon, color, bgColor }: StatCardProps) {
    return (
        <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow group">
            <div className={`p-3 rounded-2xl ${bgColor} ${color} w-fit mb-4 group-hover:scale-110 transition-transform`}>
                {icon}
            </div>
            <p className="text-sm font-semibold text-gray-400 mb-1">{label}</p>
            <p className="text-2xl font-black text-gray-900 tracking-tight">{value}</p>
        </div>
    )
}

interface InsightRowProps {
    label: string;
    value: string;
    icon: React.ReactNode;
    highlight?: boolean;
}

function InsightRow({ label, value, icon, highlight }: InsightRowProps) {
    return (
        <div className="flex items-center justify-between p-3 rounded-2xl bg-gray-50 hover:bg-gray-100 transition-colors">
            <div className="flex items-center gap-2 text-gray-500">
                {icon}
                <span className="text-sm font-medium">{label}</span>
            </div>
            <span className={`text-sm font-bold ${highlight ? 'text-red-600' : 'text-gray-900'}`}>
                {value}
            </span>
        </div>
    )
}
