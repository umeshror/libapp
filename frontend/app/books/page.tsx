'use client';

import { useEffect, useState, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { Book, BulkOperationResponse } from '../../types';
import { getBooks, fetchAPI, getMembers, borrowBook, exportBooksCSV, importBooksCSV, archiveBook, restoreBook } from '../../lib/api';
import SearchBar from '../../components/SearchBar';
import Pagination from '../../components/Pagination';
import SortSelect from '../../components/SortSelect';
import { toast } from 'sonner';
import ConfirmationModal from '../../components/ConfirmationModal';
import MemberSelectionModal from '../../components/MemberSelectionModal';
import BookFormModal from '../../components/BookFormModal';
import CSVImportModal from '../../components/CSVImportModal';
import { Plus, Edit, Book as BookIcon, Download, Upload, Archive, RotateCcw } from 'lucide-react';

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
    const [showBookModal, setShowBookModal] = useState(false);
    const [editingBook, setEditingBook] = useState<Book | null>(null);
    // Borrow Modal State
    const [borrowingBook, setBorrowingBook] = useState<Book | null>(null);
    const [borrowError, setBorrowError] = useState('');

    // Confirmation State
    const [confirmingBorrow, setConfirmingBorrow] = useState<{ book: Book, member: { id: string, name: string } } | null>(null);
    const [confirmingArchive, setConfirmingArchive] = useState<Book | null>(null);
    const [isExporting, setIsExporting] = useState(false);
    const [showImportModal, setShowImportModal] = useState(false);

    // Mutations
    const bookMutation = useMutation({
        mutationFn: (bookData: Partial<Book>) => {
            if (editingBook) {
                return fetchAPI(`/books/${editingBook.id}`, { method: 'PUT', body: JSON.stringify(bookData) });
            }
            return fetchAPI('/books/', { method: 'POST', body: JSON.stringify(bookData) });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['books'] });
            setShowBookModal(false);
            setEditingBook(null);
            toast.success(editingBook ? 'Book updated successfully' : 'Book added successfully');
        },
        onError: (err: Error) => {
            toast.error(err.message || 'Failed to save book');
        }
    });

    const borrowMutation = useMutation({
        mutationFn: ({ bookId, memberId }: { bookId: string, memberId: string }) => borrowBook({ book_id: bookId, member_id: memberId }),
        onSuccess: (data, variables) => {
            queryClient.invalidateQueries({ queryKey: ['books'] });
            setBorrowingBook(null);
            setConfirmingBorrow(null);
            toast.success(`Book borrowed successfully!`);
            // Redirect to member detail page
            router.push(`/members/${variables.memberId}`);
        },
        onError: (err: Error) => {
            setBorrowError(err.message);
            toast.error(err.message);
        }
    });

    async function handleConfirmBorrow(memberId: string, memberName: string) {
        if (!borrowingBook) return;
        setConfirmingBorrow({ book: borrowingBook, member: { id: memberId, name: memberName } });
    }

    async function executeBorrow() {
        if (!confirmingBorrow) return;
        borrowMutation.mutate({
            bookId: confirmingBorrow.book.id,
            memberId: confirmingBorrow.member.id
        });
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

    const handleAddClick = () => {
        setEditingBook(null);
        setShowBookModal(true);
    };

    const handleEditClick = (book: Book) => {
        setEditingBook(book);
        setShowBookModal(true);
    };

    const handleSaveBook = (data: Partial<Book>) => {
        bookMutation.mutate(data);
    };

    const archiveMutation = useMutation({
        mutationFn: (bookId: string) => archiveBook(bookId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['books'] });
            setConfirmingArchive(null);
            toast.success('Book archived successfully');
        },
        onError: (err: Error) => {
            toast.error(err.message || 'Failed to archive book');
        }
    });

    const restoreMutation = useMutation({
        mutationFn: (bookId: string) => restoreBook(bookId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['books'] });
            toast.success('Book restored successfully');
        },
        onError: (err: Error) => {
            toast.error(err.message || 'Failed to restore book');
        }
    });

    const handleExport = async () => {
        try {
            setIsExporting(true);
            const blob = await exportBooksCSV();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `books_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            toast.success('Export completed');
        } catch (err: any) {
            toast.error(err.message);
        } finally {
            setIsExporting(false);
        }
    };

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
                        onClick={() => setShowImportModal(true)}
                        className="flex items-center gap-2 bg-white text-slate-700 border border-slate-200 px-4 py-2 rounded-xl font-bold hover:bg-slate-50 transition-all whitespace-nowrap"
                    >
                        <Upload className="w-4 h-4" />
                        Import
                    </button>
                    <button
                        onClick={handleExport}
                        disabled={isExporting}
                        className="flex items-center gap-2 bg-white text-slate-700 border border-slate-200 px-4 py-2 rounded-xl font-bold hover:bg-slate-50 transition-all whitespace-nowrap"
                    >
                        <Download className="w-4 h-4" />
                        Export
                    </button>
                    <button
                        onClick={handleAddClick}
                        className="flex items-center gap-2 bg-indigo-600 text-white px-6 py-2 rounded-xl font-bold hover:bg-indigo-700 shadow-lg shadow-indigo-100 transition-all whitespace-nowrap"
                    >
                        <Plus className="w-4 h-4" />
                        Add Book
                    </button>
                </div>
            </div>

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
                                        className="p-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
                                        title="View Details"
                                    >
                                        <BookIcon className="w-4 h-4" />
                                    </Link>
                                    <button
                                        onClick={() => handleEditClick(book)}
                                        className="p-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
                                        title="Edit Book"
                                    >
                                        <Edit className="w-4 h-4" />
                                    </button>
                                    <button
                                        onClick={() => setConfirmingArchive(book)}
                                        className="p-2 rounded-lg border border-slate-200 text-rose-600 hover:bg-rose-50 transition-colors"
                                        title="Archive Book"
                                    >
                                        <Archive className="w-4 h-4" />
                                    </button>
                                    <button
                                        className={`px-4 py-1.5 rounded-lg text-sm font-bold transition-all shadow-sm ${book.available_copies > 0
                                            ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                                            : 'bg-slate-100 text-slate-400 cursor-not-allowed shadow-none'
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

            <BookFormModal
                isOpen={showBookModal}
                onClose={() => setShowBookModal(false)}
                onSave={handleSaveBook}
                book={editingBook}
                isLoading={bookMutation.isPending}
            />

            <MemberSelectionModal
                isOpen={!!borrowingBook}
                onClose={() => { setBorrowingBook(null); setBorrowError(''); }}
                onSelect={handleConfirmBorrow}
                title={`Borrow "${borrowingBook?.title}"`}
            />

            <ConfirmationModal
                isOpen={!!confirmingBorrow}
                onClose={() => setConfirmingBorrow(null)}
                onConfirm={executeBorrow}
                isLoading={borrowMutation.isPending}
                title="Confirm Borrow"
                description={`Are you sure you want to borrow "${confirmingBorrow?.book.title}" for member "${confirmingBorrow?.member.name}"?`}
                confirmText="Confirm Borrow"
            />
            <CSVImportModal
                isOpen={showImportModal}
                onClose={() => { setShowImportModal(false); queryClient.invalidateQueries({ queryKey: ['books'] }); }}
                onImport={importBooksCSV}
                title="Import Books from CSV"
            />
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
