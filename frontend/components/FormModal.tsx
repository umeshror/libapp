'use client';

import React, { ReactNode } from 'react';
import { X, Loader2 } from 'lucide-react';

interface FormModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: () => void;
    title: string;
    children: ReactNode;
    isLoading?: boolean;
    saveLabel?: string;
    isSaveDisabled?: boolean;
}

export default function FormModal({
    isOpen,
    onClose,
    onSave,
    title,
    children,
    isLoading = false,
    saveLabel = 'Save Changes',
    isSaveDisabled = false,
}: FormModalProps) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
            <div
                className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden border border-slate-200 animate-in zoom-in-95 duration-200"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                    <h2 className="text-xl font-bold text-slate-800">{title}</h2>
                    <button
                        onClick={onClose}
                        className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-slate-100 rounded-lg transition-all"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Body */}
                <div className="px-6 py-6 max-h-[70vh] overflow-y-auto">
                    {children}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 bg-slate-50/50 border-t border-slate-100 flex items-center justify-end gap-3">
                    <button
                        onClick={onClose}
                        disabled={isLoading}
                        className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-all disabled:opacity-50"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onSave}
                        disabled={isLoading || isSaveDisabled}
                        className="flex items-center gap-2 px-6 py-2 bg-indigo-600 text-white text-sm font-bold rounded-xl hover:bg-indigo-700 shadow-lg shadow-indigo-100 transition-all disabled:opacity-50 disabled:shadow-none"
                    >
                        {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                        {saveLabel}
                    </button>
                </div>
            </div>
        </div>
    );
}
