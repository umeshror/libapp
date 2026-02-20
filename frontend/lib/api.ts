const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';
import { ListParams, PaginatedResponse, Book, Member, BorrowRecord } from '../types';

export async function fetchAPI(endpoint: string, options: RequestInit = {}) {
    const res = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        },
    });

    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: 'Network error' }));
        throw new Error(error.detail || `Error ${res.status}`);
    }
    return res.json();
}

function validParams(params: ListParams): URLSearchParams {
    const searchParams = new URLSearchParams();
    if (params.limit !== undefined) searchParams.set('limit', params.limit.toString());
    if (params.offset !== undefined) searchParams.set('offset', params.offset.toString());
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

import {
    AnalyticsSummaryResponse,
    BookDetailResponse,
    MemberCoreDetails,
    MemberBorrowHistoryResponse,
    MemberAnalyticsResponse
} from '../types';

export async function getAnalyticsSummary(from?: string, to?: string): Promise<AnalyticsSummaryResponse> {
    const searchParams = new URLSearchParams();
    if (from) searchParams.set('from', from);
    if (to) searchParams.set('to', to);
    return fetchAPI(`/analytics/summary?${searchParams.toString()}`);
}

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
