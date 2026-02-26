'use client';

import React, { useState, useRef } from 'react';
import FormModal from './FormModal';
import { Upload, FileText, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { BulkOperationResponse } from '../types';

interface CSVImportModalProps {
    isOpen: boolean;
    onClose: () => void;
    onImport: (file: File) => Promise<BulkOperationResponse>;
    title: string;
    templateUrl?: string;
}

export default function CSVImportModal({
    isOpen,
    onClose,
    onImport,
    title,
    templateUrl,
}: CSVImportModalProps) {
    const [file, setFile] = useState<File | null>(null);
    const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
    const [result, setResult] = useState<BulkOperationResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setStatus('idle');
            setError(null);
        }
    };

    const handleSubmit = async () => {
        if (!file) return;
        try {
            setStatus('uploading');
            const data = await onImport(file);
            setResult(data);
            setStatus('success');
        } catch (err: any) {
            setError(err.message || 'Import failed');
            setStatus('error');
        }
    };

    const handleReset = () => {
        setFile(null);
        setStatus('idle');
        setResult(null);
        setError(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    return (
        <FormModal
            isOpen={isOpen}
            onClose={() => { onClose(); handleReset(); }}
            onSave={handleSubmit}
            title={title}
            isLoading={status === 'uploading'}
            isSaveDisabled={!file || status === 'success'}
            saveLabel="Start Import"
        >
            <div className="space-y-6">
                {status === 'idle' && (
                    <div
                        onClick={() => fileInputRef.current?.click()}
                        className="border-2 border-dashed border-slate-200 rounded-2xl p-8 flex flex-col items-center justify-center bg-slate-50 hover:bg-slate-100 hover:border-indigo-300 transition-all cursor-pointer group"
                    >
                        <input
                            type="file"
                            ref={fileInputRef}
                            onChange={handleFileChange}
                            className="hidden"
                            accept=".csv"
                        />
                        <div className="p-4 bg-white rounded-full shadow-sm group-hover:scale-110 transition-transform mb-4">
                            <Upload className="w-8 h-8 text-indigo-600" />
                        </div>
                        <p className="text-sm font-bold text-slate-700">Click to upload CSV</p>
                        <p className="text-xs text-slate-400 mt-1">Maximum file size: 5MB</p>
                    </div>
                )}

                {file && status !== 'success' && (
                    <div className="flex items-center gap-4 p-4 bg-indigo-50 border border-indigo-100 rounded-xl">
                        <div className="p-2 bg-white rounded-lg">
                            <FileText className="w-6 h-6 text-indigo-600" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-bold text-slate-900 truncate">{file.name}</p>
                            <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                        </div>
                        <button onClick={handleReset} className="text-xs font-bold text-indigo-600 hover:text-indigo-700">Change</button>
                    </div>
                )}

                {status === 'success' && result && (
                    <div className="space-y-4">
                        <div className="flex flex-col items-center text-center p-6 bg-emerald-50 border border-emerald-100 rounded-2xl">
                            <CheckCircle2 className="w-12 h-12 text-emerald-600 mb-2" />
                            <h3 className="text-lg font-bold text-emerald-900">Import Complete</h3>
                            <p className="text-sm text-emerald-700">Successfully processed {result.successful} of {result.total_records} records.</p>
                        </div>

                        {result.failed > 0 && (
                            <div className="p-4 bg-amber-50 border border-amber-100 rounded-xl">
                                <p className="text-sm font-bold text-amber-900 mb-2 flex items-center gap-2">
                                    <AlertCircle className="w-4 h-4" />
                                    {result.failed} records failed
                                </p>
                                <ul className="text-xs text-amber-700 space-y-1 max-h-32 overflow-y-auto">
                                    {result.errors.map((err, i) => (
                                        <li key={i}>• {err}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                )}

                {status === 'error' && (
                    <div className="p-4 bg-red-50 border border-red-100 rounded-xl flex items-start gap-3">
                        <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
                        <div>
                            <p className="text-sm font-bold text-red-900">Error Occurred</p>
                            <p className="text-xs text-red-700">{error}</p>
                        </div>
                    </div>
                )}

                {templateUrl && status === 'idle' && (
                    <div className="text-center">
                        <a href={templateUrl} className="text-xs font-bold text-slate-400 hover:text-indigo-600 transition-colors uppercase tracking-widest">
                            Download CSV Template
                        </a>
                    </div>
                )}
            </div>
        </FormModal>
    );
}
