'use client';

import { useEffect, useState, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { BorrowRecord } from '../../types';
import { getBorrows, fetchAPI } from '../../lib/api';
import SearchBar from '../../components/SearchBar';
import Pagination from '../../components/Pagination';
import SortSelect from '../../components/SortSelect';

function BorrowsContent() {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const queryClient = useQueryClient();

    // URL State
    const page = Number(searchParams.get('page')) || 1;
    const pageSize = Number(searchParams.get('page_size')) || 20;
    const query = searchParams.get('q') || '';
    const sortBy = searchParams.get('sort_by') || 'borrowed_at';
    const order = searchParams.get('order') || 'desc';
    const sortParam = order === 'desc' ? `-${sortBy}` : sortBy;

    // React Query for Borrows
    const { data: borrowsData, isLoading, error: queryError } = useQuery({
        queryKey: ['borrows', { page, pageSize, query, sortParam }],
        queryFn: () => getBorrows({ limit: pageSize, offset: (page - 1) * pageSize, q: query, sort: sortParam }),
        placeholderData: keepPreviousData,
    });

    const borrows: BorrowRecord[] = borrowsData?.data || [];
    const total = borrowsData?.meta?.total || 0;
    const totalPages = Math.ceil(total / pageSize) || 0;
    const error = queryError ? queryError.message : '';

    const [actionError, setActionError] = useState<string | null>(null);

    const updateUrl = (newParams: Record<string, string | number>) => {
        const params = new URLSearchParams(searchParams.toString());
        Object.entries(newParams).forEach(([key, value]) => {
            if (value === '' || value === undefined) {
                params.delete(key);
            } else {
                params.set(key, String(value));
            }
        });
        router.push(`${pathname}?${params.toString()}`);
    };



    // Handlers
    const handleSearch = (newQuery: string) => {
        updateUrl({ q: newQuery, page: 1 });
    };

    const handlePageChange = (newPage: number) => {
        updateUrl({ page: newPage });
    };

    const handleSortChange = (field: string, newOrder: string) => {
        updateUrl({ sort_by: field, order: newOrder, page: 1 });
    };

    const returnMutation = useMutation({
        mutationFn: (borrowId: string) => fetchAPI(`/borrows/${borrowId}/return/`, { method: 'POST' }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['borrows'] });
            // Also invalidate books and members to keep availability and counts synced
            queryClient.invalidateQueries({ queryKey: ['books'] });
            queryClient.invalidateQueries({ queryKey: ['members'] });
        },
        onError: (err: Error) => {
            setActionError(err.message);
            setTimeout(() => setActionError(null), 5000);
        }
    });

    async function handleReturn(borrowId: string) {
        if (!confirm('Are you sure you want to return this book?')) return;
        returnMutation.mutate(borrowId);
    }

    return (
        <div className="p-8">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                <h1 className="text-3xl font-bold">Borrowing Records</h1>
                <div className="flex flex-col md:flex-row gap-4 w-full md:w-auto">
                    <SearchBar initialValue={query} onSearch={handleSearch} placeholder="Search borrows..." />
                    <SortSelect
                        sortBy={sortBy}
                        order={order}
                        onSortChange={handleSortChange}
                        options={[
                            { label: 'Date Borrowed', value: 'borrowed_at' },
                            { label: 'Due Date', value: 'due_date' },
                            { label: 'Status', value: 'status' },
                        ]}
                    />
                </div>
            </div>

            {actionError && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg shadow-sm flex items-center justify-between animate-in fade-in">
                    <div>
                        <strong className="font-bold">Action Failed: </strong>
                        <span className="block sm:inline">{actionError}</span>
                    </div>
                    <button onClick={() => setActionError(null)} className="text-red-500 hover:text-red-700 font-bold ml-4">
                        &times;
                    </button>
                </div>
            )}

            {isLoading ? (
                <div className="text-center py-12">Loading borrow records...</div>
            ) : error ? (
                <div className="bg-red-50 text-red-600 p-4 rounded text-center">Error: {error}</div>
            ) : (
                <>
                    <div className="mb-4 text-sm text-gray-500">
                        Total: {total} records
                    </div>

                    <div className="bg-white shadow rounded-lg overflow-hidden">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Book</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Member</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date Borrowed</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {borrows.map(record => (
                                    <tr key={record.id}>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="font-medium text-gray-900">{record.book?.title || 'Unknown Book'}</div>
                                            <div className="text-sm text-gray-500">{record.book?.author}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm text-gray-900">{record.member?.name || 'Unknown Member'}</div>
                                            <div className="text-sm text-gray-500">{record.member?.email}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {new Date(record.borrowed_at).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${record.status === 'borrowed' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                                                }`}>
                                                {record.status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                            {record.status === 'borrowed' && (
                                                <button
                                                    onClick={() => handleReturn(record.id)}
                                                    disabled={returnMutation.isPending && returnMutation.variables === record.id}
                                                    className="text-indigo-600 hover:text-indigo-900 disabled:opacity-50"
                                                >
                                                    {returnMutation.isPending && returnMutation.variables === record.id ? 'Returning...' : 'Return'}
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}

            <div className="mt-6 flex justify-center">
                <Pagination currentPage={page} totalPages={totalPages} onPageChange={handlePageChange} />
            </div>
        </div>
    );
}

export default function BorrowsPage() {
    return (
        <Suspense fallback={<div className="p-8">Loading...</div>}>
            <BorrowsContent />
        </Suspense>
    );
}
