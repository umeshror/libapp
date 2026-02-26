'use client';

import { useEffect, useState, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { Member, BulkOperationResponse } from '../../types';
import { getMembers, fetchAPI, exportMembersCSV, importMembersCSV, archiveMember, restoreMember } from '../../lib/api';
import SearchBar from '../../components/SearchBar';
import Pagination from '../../components/Pagination';
import SortSelect from '../../components/SortSelect';
import MemberFormModal from '../../components/MemberFormModal';
import CSVImportModal from '../../components/CSVImportModal';
import { Plus, Edit, User, Mail, Phone, Calendar, Download, Upload, Archive, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';
import ConfirmationModal from '../../components/ConfirmationModal';

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

    // Form State
    const [showMemberModal, setShowMemberModal] = useState(false);
    const [editingMember, setEditingMember] = useState<Member | null>(null);
    const [confirmingArchive, setConfirmingArchive] = useState<Member | null>(null);
    const [isExporting, setIsExporting] = useState(false);
    const [showImportModal, setShowImportModal] = useState(false);

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

    // Mutations
    const memberMutation = useMutation({
        mutationFn: (memberData: Partial<Member>) => {
            if (editingMember) {
                return fetchAPI(`/members/${editingMember.id}`, { method: 'PUT', body: JSON.stringify(memberData) });
            }
            return fetchAPI('/members/', { method: 'POST', body: JSON.stringify(memberData) });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['members'] });
            setShowMemberModal(false);
            setEditingMember(null);
            toast.success(editingMember ? 'Member profile updated' : 'Member registered successfully');
        },
        onError: (err: Error) => {
            toast.error(err.message || 'Failed to save member');
        }
    });

    const handleAddClick = () => {
        setEditingMember(null);
        setShowMemberModal(true);
    };

    const handleEditClick = (member: Member) => {
        setEditingMember(member);
        setShowMemberModal(true);
    };

    const handleSaveMember = (memberData: Partial<Member>) => {
        memberMutation.mutate(memberData);
    };

    const archiveMutation = useMutation({
        mutationFn: (memberId: string) => archiveMember(memberId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['members'] });
            setConfirmingArchive(null);
            toast.success('Member archived successfully');
        },
        onError: (err: Error) => {
            toast.error(err.message || 'Failed to archive member');
        }
    });

    const restoreMutation = useMutation({
        mutationFn: (memberId: string) => restoreMember(memberId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['members'] });
            toast.success('Member profile restored');
        },
        onError: (err: Error) => {
            toast.error(err.message || 'Failed to restore member');
        }
    });

    const handleExport = async () => {
        try {
            setIsExporting(true);
            const blob = await exportMembersCSV();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `members_${new Date().toISOString().split('T')[0]}.csv`;
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
                        Register Member
                    </button>
                </div>
            </div>

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
                                            <div className="flex items-center justify-end gap-2">
                                                <button
                                                    onClick={() => handleEditClick(member)}
                                                    className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-slate-100 rounded-lg transition-all"
                                                    title="Edit Member"
                                                >
                                                    <Edit className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => setConfirmingArchive(member)}
                                                    className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-all"
                                                    title="Archive Member"
                                                >
                                                    <Archive className="w-4 h-4" />
                                                </button>
                                                <Link
                                                    href={`/members/${member.id}`}
                                                    className="flex items-center gap-1.5 px-3 py-1 bg-indigo-50 text-indigo-600 rounded-lg text-xs font-bold hover:bg-indigo-100 transition-all border border-indigo-100"
                                                >
                                                    Details
                                                </Link>
                                            </div>
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

            <MemberFormModal
                isOpen={showMemberModal}
                onClose={() => setShowMemberModal(false)}
                onSave={handleSaveMember}
                member={editingMember}
                isLoading={memberMutation.isPending}
            />

            <ConfirmationModal
                isOpen={!!confirmingArchive}
                onClose={() => setConfirmingArchive(null)}
                onConfirm={() => confirmingArchive && archiveMutation.mutate(confirmingArchive.id)}
                isLoading={archiveMutation.isPending}
                title="Archive Member"
                description={`Are you sure you want to archive "${confirmingArchive?.name}"? Their account will be deactivated but history will be preserved.`}
                confirmText="Archive Member"
                isDanger={true}
            />
            <CSVImportModal
                isOpen={showImportModal}
                onClose={() => { setShowImportModal(false); queryClient.invalidateQueries({ queryKey: ['members'] }); }}
                onImport={importMembersCSV}
                title="Import Members from CSV"
            />
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
