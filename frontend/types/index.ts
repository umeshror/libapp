export interface Book {
    id: string;
    title: string;
    author: string;
    isbn: string;
    total_copies: number;
    available_copies: number;
}

export interface Member {
    id: string;
    name: string;
    email: string;
    phone?: string;
    created_at: string;
}

export interface BorrowRecord {
    id: string;
    book_id: string;
    member_id: string;
    borrowed_at: string;
    return_date: string;
    returned_at?: string;
    status: 'borrowed' | 'returned';
    book?: Book;
    member?: Member;
}

export interface PaginationMeta {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
}

export interface PaginatedResponse<T> {
    data: T[];
    meta: PaginationMeta;
}

export interface ListParams {
    limit?: number;
    offset?: number;
    q?: string;
    sort?: string;
}

export interface AnalyticsOverview {
    total_books: number;
    active_borrows: number;
    overdue_borrows: number;
    utilization_rate: number;
}

export interface OverdueBreakdown {
    days_1_3: number;
    days_4_7: number;
    days_7_plus: number;
}

export interface TopMember {
    member_id: string;
    name: string;
    borrow_count: number;
}

export interface InventoryHealth {
    low_stock_books: number;
    never_borrowed_books: number;
    fully_unavailable_books: number;
}

export interface DailyActiveMember {
    date: string;
    count: number;
}

export interface DailyBorrowCount {
    date: string;
    count: number;
}

export interface BorrowForecast {
    projected_next_7_days_total: number;
    daily_projection: number;
}

export interface AnalyticsSummaryResponse {
    overview: AnalyticsOverview;
    overdue_breakdown: OverdueBreakdown;
    top_members: TopMember[];
    inventory_health: InventoryHealth;
    daily_active_members: DailyActiveMember[];
    daily_borrows: DailyBorrowCount[];
    forecast: BorrowForecast;
    cache_hit: boolean;
    generated_at: string;
}

export interface BorrowerInfo {
    borrow_id: string;
    member_id: string;
    name: string;
    borrowed_at: string;
    due_date: string;
    days_until_due: number;
}

export interface BorrowHistoryItem {
    member_id: string;
    member_name: string;
    borrowed_at: string;
    returned_at: string;
    duration_days: number;
}

export interface BorrowHistoryResponse {
    data: BorrowHistoryItem[];
    meta: PaginationMeta;
}

export interface BookAnalytics {
    total_times_borrowed: number;
    average_borrow_duration: number;
    last_borrowed_at: string | null;
    popularity_rank: number;
    availability_status: 'AVAILABLE' | 'LOW_STOCK' | 'OUT_OF_STOCK';
    longest_borrow_duration: number | null;
    shortest_borrow_duration: number | null;
    return_delay_count: number;
}

export interface BookDetailResponse {
    book: Book;
    current_borrowers: BorrowerInfo[];
    borrow_history: BorrowHistoryResponse;
    analytics: BookAnalytics;
}

export interface MembershipAnalyticsSummary {
    total_books_borrowed: number;
    overdue_rate_percent: number;
    risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
}

export interface MemberCoreDetails {
    member: Member;
    membership_duration_days: number;
    active_borrows_count: number;
    analytics_summary: MembershipAnalyticsSummary;
}

export interface MemberBorrowHistoryItem {
    id: string;
    book_id: string;
    book_title: string;
    borrowed_at: string;
    due_date: string;
    returned_at: string | null;
    duration_days: number | null;
    was_overdue: boolean;
}

export interface MemberBorrowHistoryResponse {
    data: MemberBorrowHistoryItem[];
    meta: PaginationMeta;
}

export interface ActivityTrendItem {
    month: string;
    count: number;
}

export interface MemberAnalyticsResponse {
    total_books_borrowed: number;
    active_books: number;
    average_borrow_duration: number;
    longest_borrow_duration: number | null;
    shortest_borrow_duration: number | null;
    overdue_count: number;
    overdue_rate_percent: number;
    favorite_author: string | null;
    borrow_frequency_per_month: number;
    risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
    activity_trend: ActivityTrendItem[];
}
