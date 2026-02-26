const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';
import {
    ListParams,
    PaginatedResponse,
    Book,
    Member,
    BorrowRecord,
    AnalyticsSummaryResponse,
    BookDetailResponse,
    MemberCoreDetails,
    MemberBorrowHistoryResponse,
    MemberAnalyticsResponse,
    BulkOperationResponse
} from '../types';

/** Fetch wrapper with JSON headers and error extraction from API responses. */
export async function fetchAPI(endpoint: string, options: RequestInit = {}) {
    const res = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        },
    });

    if (!res.ok) {
        let errorMsg = `API Error: ${res.status} ${res.statusText}`;
        let errorCode = 'INTERNAL_ERROR';
        let correlationId = 'unknown';

        try {
            const errorData = await res.json();
            correlationId = errorData.correlation_id || 'unknown';
            errorCode = errorData.error_code || 'LIBRARY_ERROR';

            // Handle Standardized Validation errors
            if (res.status === 422 && Array.isArray(errorData.validation_errors)) {
                errorMsg = errorData.validation_errors
                    .map((err: any) => `${err.loc[err.loc.length - 1]}: ${err.msg}`)
                    .join(', ');
            } else if (errorData.detail) {
                errorMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
            }
        } catch (e) {
            // Fallback for non-JSON or malformed responses
        }

        const finalError = new Error(errorMsg) as any;
        finalError.code = errorCode;
        finalError.correlationId = correlationId;

        console.error(`[${errorCode}] ${errorMsg} (ID: ${correlationId})`);
        throw finalError;
    }

    // Handle 204 No Content
    if (res.status === 204) {
        return null;
    }

    return res.json();
}

/** Convert ListParams to URLSearchParams, omitting undefined values. */
function validParams(params: ListParams): URLSearchParams {
    const searchParams = new URLSearchParams();
    if (params.limit !== undefined) searchParams.set('limit', params.limit.toString());
    if (params.offset !== undefined) searchParams.set('offset', params.offset.toString());
    if (params.cursor) searchParams.set('cursor', params.cursor);
    if (params.sort) searchParams.set('sort', params.sort);
    if (params.q) searchParams.set('q', params.q);
    return searchParams;
}

export async function getBooks(params: ListParams): Promise<PaginatedResponse<Book>> {
    const searchParams = validParams(params);
    return fetchAPI(`/books/?${searchParams.toString()}`);
}

export async function getMembers(params: ListParams): Promise<PaginatedResponse<Member>> {
    const searchParams = validParams(params);
    return fetchAPI(`/members/?${searchParams.toString()}`);
}

export async function getBorrows(params: ListParams): Promise<PaginatedResponse<BorrowRecord>> {
    const searchParams = validParams(params);
    return fetchAPI(`/borrows/?${searchParams.toString()}`);
}

export async function getMemberBorrows(memberId: string, params: ListParams): Promise<PaginatedResponse<BorrowRecord>> {
    const searchParams = validParams(params);
    return fetchAPI(`/members/${memberId}/borrows?${searchParams.toString()}`);
}



/** Fetch dashboard analytics with optional date range filter. */
export async function getAnalyticsSummary(from?: string, to?: string): Promise<AnalyticsSummaryResponse> {
    const searchParams = new URLSearchParams();
    if (from) searchParams.set('from', from);
    if (to) searchParams.set('to', to);
    return fetchAPI(`/analytics/summary?${searchParams.toString()}`);
}

/** Fetch book details including borrowers, history, and analytics. */
export async function getBookDetails(
    id: string,
    historyLimit: number = 10,
    historyOffset: number = 0
): Promise<BookDetailResponse> {
    return fetchAPI(`/books/${id}/details?history_limit=${historyLimit}&history_offset=${historyOffset}`);
}

export async function getMemberCoreDetails(memberId: string): Promise<MemberCoreDetails> {
    return fetchAPI(`/members/${memberId}`);
}

export async function getMemberBorrowHistory(
    memberId: string,
    limit: number = 10,
    offset: number = 0,
    status: string = 'all',
    sort: string = 'borrowed_at',
    order: string = 'desc'
): Promise<MemberBorrowHistoryResponse> {
    const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
        status,
        sort,
        order
    });
    return fetchAPI(`/members/${memberId}/history?${params.toString()}`);
}

export async function getMemberAnalytics(memberId: string): Promise<MemberAnalyticsResponse> {
    return fetchAPI(`/members/${memberId}/analytics`);
}

export async function borrowBook(payload: { book_id: string, member_id: string }): Promise<BorrowRecord> {
    return fetchAPI('/borrows/', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function returnBook(borrowId: string): Promise<BorrowRecord> {
    return fetchAPI(`/borrows/${borrowId}/return/`, {
        method: 'POST'
    });
}

export async function updateBook(id: string, data: Partial<Book>): Promise<Book> {
    return fetchAPI(`/books/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data)
    });
}

export async function updateMember(id: string, data: Partial<Member>): Promise<Member> {
    return fetchAPI(`/members/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data)
    });
}
export async function archiveBook(id: string): Promise<void> {
    return fetchAPI(`/books/${id}`, { method: 'DELETE' });
}

export async function restoreBook(id: string): Promise<Book> {
    return fetchAPI(`/books/${id}/restore`, { method: 'POST' });
}

export async function archiveMember(id: string): Promise<void> {
    return fetchAPI(`/members/${id}`, { method: 'DELETE' });
}

export async function restoreMember(id: string): Promise<Member> {
    return fetchAPI(`/members/${id}/restore`, { method: 'POST' });
}

export async function exportBooksCSV(): Promise<Blob> {
    const res = await fetch(`${API_URL}/books/export/csv`);
    if (!res.ok) throw new Error('Failed to export books');
    return res.blob();
}

export async function importBooksCSV(file: File): Promise<BulkOperationResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_URL}/books/import/csv`, {
        method: 'POST',
        body: formData,
    });

    if (!res.ok) throw new Error('Failed to import books');
    return res.json();
}

export async function exportMembersCSV(): Promise<Blob> {
    const res = await fetch(`${API_URL}/members/export/csv`);
    if (!res.ok) throw new Error('Failed to export members');
    return res.blob();
}

export async function importMembersCSV(file: File): Promise<BulkOperationResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_URL}/members/import/csv`, {
        method: 'POST',
        body: formData,
    });

    if (!res.ok) throw new Error('Failed to import members');
    return res.json();
}
