'use client';

import { useEffect, useState, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { Book } from '../../types';
import { getBooks, fetchAPI, getMembers, borrowBook } from '../../lib/api';
import SearchBar from '../../components/SearchBar';
import Pagination from '../../components/Pagination';
import SortSelect from '../../components/SortSelect';

function BooksContent() {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const queryClient = useQueryClient();

    // URL State
    const page = Number(searchParams.get('page')) || 1;
    const pageSize = Number(searchParams.get('page_size')) || 20;
    const query = searchParams.get('q') || '';
    const sortBy = searchParams.get('sort_by') || 'title';
    const order = searchParams.get('order') || 'asc';
    const sortParam = order === 'desc' ? `-${sortBy}` : sortBy;

    // React Query for Books
    const { data: booksData, isLoading, error: queryError } = useQuery({
        queryKey: ['books', { page, pageSize, query, sortParam }],
        queryFn: () => getBooks({ limit: pageSize, offset: (page - 1) * pageSize, q: query, sort: sortParam }),
        placeholderData: keepPreviousData,
    });

    const books = booksData?.data || [];
    const total = booksData?.meta?.total || 0;
    const totalPages = Math.ceil(total / pageSize) || 0;
    const error = queryError ? queryError.message : '';

    // Form State
    const [showAddForm, setShowAddForm] = useState(false);
    const [newBook, setNewBook] = useState({ title: '', author: '', isbn: '', total_copies: 1 });

    // Borrow Modal State
    const [borrowingBook, setBorrowingBook] = useState<Book | null>(null);
    const [memberQuery, setMemberQuery] = useState('');
    const [debouncedMemberQuery, setDebouncedMemberQuery] = useState('');
    const [borrowError, setBorrowError] = useState('');

    const [actionError, setActionError] = useState<string | null>(null);
    const [actionSuccess, setActionSuccess] = useState<string | null>(null);

    useEffect(() => {
        const timer = setTimeout(() => setDebouncedMemberQuery(memberQuery), 300);
        return () => clearTimeout(timer);
    }, [memberQuery]);

    // React Query for Members in Borrow Modal
    const { data: membersData, isFetching: membersLoading } = useQuery({
        queryKey: ['members-search', debouncedMemberQuery],
        queryFn: () => getMembers({ q: debouncedMemberQuery, limit: 10 }),
        enabled: !!borrowingBook,
    });
    const memberResults = membersData?.data || [];

    // Mutations
    const addBookMutation = useMutation({
        mutationFn: (bookData: Partial<Book>) => fetchAPI('/books/', { method: 'POST', body: JSON.stringify(bookData) }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['books'] });
            setShowAddForm(false);
            setNewBook({ title: '', author: '', isbn: '', total_copies: 1 });
        },
        onError: (err: Error) => {
            setActionError(err.message || 'Failed to add book');
            setTimeout(() => setActionError(null), 5000);
        }
    });

    const borrowMutation = useMutation({
        mutationFn: ({ bookId, memberId }: { bookId: string, memberId: string }) => borrowBook({ book_id: bookId, member_id: memberId }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['books'] });
            setBorrowingBook(null);
            setMemberQuery('');
            setActionSuccess(`Book borrowed successfully!`);
            setTimeout(() => setActionSuccess(null), 5000);
        },
        onError: (err: Error) => {
            setBorrowError(err.message);
        }
    });

    async function handleConfirmBorrow(memberId: string) {
        if (!borrowingBook) return;
        setBorrowError('');
        borrowMutation.mutate({ bookId: borrowingBook.id, memberId });
    }

    const createQueryString = useCallback(
        (name: string, value: string) => {
            const params = new URLSearchParams(searchParams.toString());
            params.set(name, value);
            return params.toString();
        },
        [searchParams]
    );

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
        updateUrl({ q: newQuery, page: 1 }); // Reset to page 1 on search
    };

    const handlePageChange = (newPage: number) => {
        updateUrl({ page: newPage });
    };

    const handleSortChange = (field: string, newOrder: string) => {
        updateUrl({ sort_by: field, order: newOrder, page: 1 });
    };

    async function handleAddBook(e: React.FormEvent) {
        e.preventDefault();
        addBookMutation.mutate(newBook);
    }

    return (
        <div className="p-8">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                <h1 className="text-3xl font-bold">Books Library</h1>
                <div className="flex flex-col md:flex-row gap-4 w-full md:w-auto">
                    <SearchBar initialValue={query} onSearch={handleSearch} />
                    <SortSelect
                        sortBy={sortBy}
                        order={order}
                        onSortChange={handleSortChange}
                        options={[
                            { label: 'Title', value: 'title' },
                            { label: 'Author', value: 'author' },
                            { label: 'Availability', value: 'available_copies' },
                            { label: 'Date Added', value: 'created_at' },
                        ]}
                    />
                    <button
                        onClick={() => setShowAddForm(!showAddForm)}
                        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 whitespace-nowrap"
                    >
                        {showAddForm ? 'Cancel' : 'Add Book'}
                    </button>
                </div>
            </div>

            {actionError && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg shadow-sm flex items-center justify-between animate-in fade-in slide-in-from-top-2">
                    <div>
                        <span className="block sm:inline">{actionError}</span>
                    </div>
                    <button onClick={() => setActionError(null)} className="text-red-500 hover:text-red-700 font-bold ml-4">
                        &times;
                    </button>
                </div>
            )}

            {actionSuccess && (
                <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg shadow-sm flex items-center justify-between animate-in fade-in slide-in-from-top-2">
                    <div>
                        <span className="block sm:inline">{actionSuccess}</span>
                    </div>
                    <button onClick={() => setActionSuccess(null)} className="text-emerald-500 hover:text-emerald-700 font-bold ml-4">
                        &times;
                    </button>
                </div>
            )}

            {/* Pagination Controls Top */}
            <div className="mb-4 flex justify-between items-center text-sm text-gray-500">
                <span>Total: {total} books</span>
                <Pagination currentPage={page} totalPages={totalPages} onPageChange={handlePageChange} />
            </div>

            {isLoading ? (
                <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading library...</p>
                </div>
            ) : error ? (
                <div className="bg-red-50 text-red-600 p-4 rounded text-center">
                    Error: {error}
                </div>
            ) : books.length === 0 ? (
                <div className="text-center py-12 bg-gray-50 rounded text-gray-500">
                    No books found matching your criteria.
                </div>
            ) : (
                <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                    {books.map(book => (
                        <div key={book.id} className="border p-4 rounded shadow-sm hover:shadow-md transition bg-white flex flex-col justify-between">
                            <div>
                                <h3 className="font-bold text-lg text-gray-900 line-clamp-2" title={book.title}>{book.title}</h3>
                                <p className="text-blue-600 mb-2">{book.author}</p>
                                <div className="text-xs text-gray-400 font-mono mb-2">ISBN: {book.isbn}</div>
                            </div>
                            <div className="mt-4 pt-4 border-t flex justify-between items-center">
                                <span className={`px-2 py-1 rounded text-xs font-semibold ${book.available_copies > 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                                    }`}>
                                    {book.available_copies} / {book.total_copies} available
                                </span>
                                <div className="flex gap-2">
                                    <Link
                                        href={`/books/${book.id}`}
                                        className="px-3 py-1 rounded text-sm border border-blue-600 text-blue-600 hover:bg-blue-50 transition-colors flex items-center"
                                    >
                                        Details
                                    </Link>
                                    <button
                                        className={`px-3 py-1 rounded text-sm ${book.available_copies > 0
                                            ? 'bg-blue-600 text-white hover:bg-blue-700'
                                            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                            }`}
                                        disabled={book.available_copies <= 0}
                                        onClick={() => setBorrowingBook(book)}
                                    >
                                        Borrow
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <div className="mt-6 flex justify-center">
                <Pagination currentPage={page} totalPages={totalPages} onPageChange={handlePageChange} />
            </div>

            {showAddForm && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                    <div className="bg-white p-6 rounded-lg shadow-xl max-w-lg w-full">
                        <h2 className="text-xl font-bold mb-4">Add New Book</h2>
                        <form onSubmit={handleAddBook} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <input
                                type="text"
                                placeholder="Title"
                                className="p-2 border rounded"
                                value={newBook.title}
                                onChange={e => setNewBook({ ...newBook, title: e.target.value })}
                                required
                            />
                            <input
                                type="text"
                                placeholder="Author"
                                className="p-2 border rounded"
                                value={newBook.author}
                                onChange={e => setNewBook({ ...newBook, author: e.target.value })}
                                required
                            />
                            <input
                                type="text"
                                placeholder="ISBN"
                                className="p-2 border rounded"
                                value={newBook.isbn}
                                onChange={e => setNewBook({ ...newBook, isbn: e.target.value })}
                                required
                            />
                            <input
                                type="number"
                                placeholder="Total Copies"
                                className="p-2 border rounded"
                                value={newBook.total_copies}
                                onChange={e => setNewBook({ ...newBook, total_copies: parseInt(e.target.value) })}
                                min="1"
                                required
                            />
                            <div className="flex justify-end gap-2 md:col-span-2 mt-4">
                                <button type="button" onClick={() => setShowAddForm(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded">
                                    Cancel
                                </button>
                                <button type="submit" disabled={addBookMutation.isPending} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50">
                                    {addBookMutation.isPending ? 'Saving...' : 'Save Book'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {borrowingBook && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                    <div className="bg-white p-6 rounded-lg shadow-xl max-w-lg w-full">
                        <h2 className="text-xl font-bold mb-4">Borrow &quot;{borrowingBook.title}&quot;</h2>
                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-1">Search Member</label>
                            <input
                                type="text"
                                placeholder="Search by name or email..."
                                className="w-full p-2 border rounded"
                                value={memberQuery}
                                onChange={e => setMemberQuery(e.target.value)}
                            />
                        </div>

                        {borrowError && (
                            <div className="mb-4 p-2 bg-red-100 text-red-700 rounded text-sm">
                                {borrowError}
                            </div>
                        )}

                        <div className="max-h-60 overflow-y-auto border rounded mb-4">
                            {memberResults.length === 0 ? (
                                <div className="p-4 text-center text-gray-500 text-sm">No members found.</div>
                            ) : (
                                memberResults.map(member => (
                                    <div key={member.id} className="p-3 border-b hover:bg-gray-50 flex justify-between items-center">
                                        <div>
                                            <div className="font-semibold">{member.name}</div>
                                            <div className="text-xs text-gray-500">{member.email}</div>
                                        </div>
                                        <button
                                            onClick={() => handleConfirmBorrow(member.id)}
                                            disabled={borrowMutation.isPending}
                                            className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
                                        >
                                            {borrowMutation.isPending ? '...' : 'Select'}
                                        </button>
                                    </div>
                                ))
                            )}
                            {membersLoading && (
                                <div className="p-4 text-center text-gray-400 text-xs">Searching...</div>
                            )}
                        </div>

                        <div className="flex justify-end gap-2">
                            <button
                                type="button"
                                onClick={() => { setBorrowingBook(null); setMemberQuery(''); setBorrowError(''); }}
                                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default function BooksPage() {
    return (
        <Suspense fallback={<div className="p-8">Loading...</div>}>
            <BooksContent />
        </Suspense>
    );
}
