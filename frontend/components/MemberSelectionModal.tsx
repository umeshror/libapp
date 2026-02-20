'use client';

import React, { useState, useEffect } from 'react';
import { getMembers } from '../lib/api';
import { useQuery } from '@tanstack/react-query';
import { Member } from '../types';

interface MemberSelectionModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSelect: (memberId: string, memberName: string) => void;
    title: string;
}

const MemberSelectionModal = ({ isOpen, onClose, onSelect, title }: MemberSelectionModalProps) => {
    const [memberQuery, setMemberQuery] = useState('');
    const [debouncedMemberQuery, setDebouncedMemberQuery] = useState('');

    useEffect(() => {
        const timer = setTimeout(() => setDebouncedMemberQuery(memberQuery), 300);
        return () => clearTimeout(timer);
    }, [memberQuery]);

    const { data: membersData, isFetching: membersLoading } = useQuery({
        queryKey: ['members-search', debouncedMemberQuery],
        queryFn: () => getMembers({ q: debouncedMemberQuery, limit: 10 }),
        enabled: isOpen,
    });
    const memberResults = membersData?.data || [];

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white p-6 rounded-lg shadow-xl max-w-md w-full animate-in fade-in zoom-in duration-200">
                <h2 className="text-xl font-bold mb-4">{title}</h2>
                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Search Member</label>
                    <input
                        type="text"
                        placeholder="Search by name or email..."
                        className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                        value={memberQuery}
                        onChange={e => setMemberQuery(e.target.value)}
                        autoFocus
                    />
                </div>

                <div className="max-h-60 overflow-y-auto border rounded mb-4">
                    {memberResults.length === 0 && !membersLoading ? (
                        <div className="p-4 text-center text-gray-500 text-sm">No members found.</div>
                    ) : (
                        memberResults.map(member => (
                            <div key={member.id} className="p-3 border-b last:border-0 hover:bg-gray-50 flex justify-between items-center transition-colors">
                                <div>
                                    <div className="font-semibold text-gray-900">{member.name}</div>
                                    <div className="text-xs text-gray-500">{member.email}</div>
                                </div>
                                <button
                                    onClick={() => onSelect(member.id, member.name)}
                                    className="bg-blue-600 text-white px-3 py-1.5 rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors shadow-sm"
                                >
                                    Select
                                </button>
                            </div>
                        ))
                    )}
                    {membersLoading && (
                        <div className="p-4 text-center">
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mx-auto"></div>
                            <p className="text-xs text-gray-400 mt-1">Searching...</p>
                        </div>
                    )}
                </div>

                <div className="flex justify-end">
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
};

export default MemberSelectionModal;
