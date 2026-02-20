'use client';

import { useEffect, useState, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { Member } from '../../types';
import { getMembers, fetchAPI } from '../../lib/api';
import SearchBar from '../../components/SearchBar';
import Pagination from '../../components/Pagination';
import SortSelect from '../../components/SortSelect';

function MembersContent() {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const queryClient = useQueryClient();

    // URL State
    const page = Number(searchParams.get('page')) || 1;
    const pageSize = Number(searchParams.get('page_size')) || 20;
    const query = searchParams.get('q') || '';
    const sortBy = searchParams.get('sort_by') || 'created_at';
    const order = searchParams.get('order') || 'desc';
    const sortParam = order === 'desc' ? `-${sortBy}` : sortBy;

    // React Query for Members
    const { data: membersData, isLoading, error: queryError } = useQuery({
        queryKey: ['members', { page, pageSize, query, sortParam }],
        queryFn: () => getMembers({ limit: pageSize, offset: (page - 1) * pageSize, q: query, sort: sortParam }),
        placeholderData: keepPreviousData,
    });

    const members: Member[] = membersData?.data || [];
    const total = membersData?.meta?.total || 0;
    const totalPages = Math.ceil(total / pageSize) || 0;
    const error = queryError ? queryError.message : '';

    const [showAddForm, setShowAddForm] = useState(false);
    const [newMember, setNewMember] = useState({ name: '', email: '', phone: '' });
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

    const addMemberMutation = useMutation({
        mutationFn: (memberData: Partial<Member>) => fetchAPI('/members/', { method: 'POST', body: JSON.stringify(memberData) }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['members'] });
            setShowAddForm(false);
            setNewMember({ name: '', email: '', phone: '' });
        },
        onError: (err: Error) => {
            setActionError(err.message || 'Failed to add member');
            setTimeout(() => setActionError(null), 5000);
        }
    });

    async function handleAddMember(e: React.FormEvent) {
        e.preventDefault();
        addMemberMutation.mutate(newMember);
    }

    return (
        <div className="p-8">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                <h1 className="text-3xl font-bold">Members</h1>
                <div className="flex flex-col md:flex-row gap-4 w-full md:w-auto">
                    <SearchBar initialValue={query} onSearch={handleSearch} placeholder="Search members..." />
                    <SortSelect
                        sortBy={sortBy}
                        order={order}
                        onSortChange={handleSortChange}
                        options={[
                            { label: 'Name', value: 'name' },
                            { label: 'Email', value: 'email' },
                            { label: 'Joined Date', value: 'created_at' },
                        ]}
                    />
                    <button
                        onClick={() => setShowAddForm(!showAddForm)}
                        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 whitespace-nowrap"
                    >
                        {showAddForm ? 'Cancel' : 'Add New Member'}
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

            {showAddForm && (
                <div className="mb-8 bg-gray-50 p-6 rounded-lg border">
                    <h2 className="text-xl font-semibold mb-4">Add New Member</h2>
                    <form onSubmit={handleAddMember} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <input
                            type="text"
                            placeholder="Name"
                            className="p-2 border rounded"
                            value={newMember.name}
                            onChange={e => setNewMember({ ...newMember, name: e.target.value })}
                            required
                        />
                        <input
                            type="email"
                            placeholder="Email"
                            className="p-2 border rounded"
                            value={newMember.email}
                            onChange={e => setNewMember({ ...newMember, email: e.target.value })}
                            required
                        />
                        <input
                            type="text"
                            placeholder="Phone"
                            className="p-2 border rounded md:col-span-2"
                            value={newMember.phone}
                            onChange={e => setNewMember({ ...newMember, phone: e.target.value })}
                        />
                        <button type="submit" disabled={addMemberMutation.isPending} className="bg-green-600 text-white px-4 py-2 rounded md:col-span-2 disabled:opacity-50">
                            {addMemberMutation.isPending ? 'Saving...' : 'Save Member'}
                        </button>
                    </form>
                </div>
            )}

            {isLoading ? (
                <div className="text-center py-12">Loading members...</div>
            ) : error ? (
                <div className="bg-red-50 text-red-600 p-4 rounded text-center">Error: {error}</div>
            ) : (
                <>
                    <div className="mb-4 text-sm text-gray-500">
                        Total: {total} members
                    </div>
                    <div className="bg-white shadow rounded-lg overflow-hidden">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Phone</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Joined</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {members.map(member => (
                                    <tr key={member.id}>
                                        <td className="px-6 py-4 whitespace-nowrap">{member.name}</td>
                                        <td className="px-6 py-4 whitespace-nowrap">{member.email}</td>
                                        <td className="px-6 py-4 whitespace-nowrap">{member.phone}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {new Date(member.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                            <Link href={`/members/${member.id}`} className="text-blue-600 hover:text-blue-900 bg-blue-50 px-3 py-1 rounded-md transition-colors">
                                                Details
                                            </Link>
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

export default function MembersPage() {
    return (
        <Suspense fallback={<div className="p-8">Loading...</div>}>
            <MembersContent />
        </Suspense>
    );
}
