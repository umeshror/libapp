'use client';

import React, { useState, useEffect } from 'react';
import FormModal from './FormModal';
import { Member } from '../types';

interface MemberFormModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (data: Partial<Member>) => void;
    member?: Member | null;
    isLoading?: boolean;
}

export default function MemberFormModal({
    isOpen,
    onClose,
    onSave,
    member = null,
    isLoading = false,
}: MemberFormModalProps) {
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        phone: '',
    });

    useEffect(() => {
        if (member) {
            setFormData({
                name: member.name,
                email: member.email,
                phone: member.phone || '',
            });
        } else {
            setFormData({
                name: '',
                email: '',
                phone: '',
            });
        }
    }, [member, isOpen]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData((prev) => ({
            ...prev,
            [name]: value,
        }));
    };

    const isInvalid = !formData.name || !formData.email || !formData.email.includes('@');

    return (
        <FormModal
            isOpen={isOpen}
            onClose={onClose}
            onSave={() => onSave(formData)}
            title={member ? 'Edit Member' : 'Register New Member'}
            isLoading={isLoading}
            isSaveDisabled={isInvalid}
            saveLabel={member ? 'Update Profile' : 'Register Member'}
        >
            <div className="space-y-4">
                <div className="space-y-1.5">
                    <label className="text-sm font-bold text-slate-700 ml-1">Full Name</label>
                    <input
                        type="text"
                        name="name"
                        value={formData.name}
                        onChange={handleChange}
                        placeholder="e.g. Jane Doe"
                        className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all outline-none"
                    />
                </div>

                <div className="space-y-1.5">
                    <label className="text-sm font-bold text-slate-700 ml-1">Email Address</label>
                    <input
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleChange}
                        placeholder="e.g. jane@example.com"
                        className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all outline-none"
                    />
                </div>

                <div className="space-y-1.5">
                    <label className="text-sm font-bold text-slate-700 ml-1">Phone Number (Optional)</label>
                    <input
                        type="tel"
                        name="phone"
                        value={formData.phone}
                        onChange={handleChange}
                        placeholder="e.g. 555-0123"
                        className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all outline-none"
                    />
                </div>
            </div>
        </FormModal>
    );
}
