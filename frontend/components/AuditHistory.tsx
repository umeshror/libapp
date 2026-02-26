'use client';

import React from 'react';
import { AuditLogEntry } from '../types';
import { Clock, User, ArrowRight, Database } from 'lucide-react';

interface AuditHistoryProps {
    logs: AuditLogEntry[];
    isLoading?: boolean;
}

export default function AuditHistory({ logs, isLoading }: AuditHistoryProps) {
    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center p-12 space-y-4">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                <p className="text-sm text-slate-500">Loading audit trail...</p>
            </div>
        );
    }

    if (!logs || logs.length === 0) {
        return (
            <div className="p-12 text-center bg-slate-50 rounded-3xl border border-dashed border-slate-200">
                <Database className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500 font-medium">No system activity recorded yet.</p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {logs.map((log) => (
                <div key={log.id} className="bg-white border border-slate-100 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <div className={`p-2 rounded-lg ${log.action === 'create' ? 'bg-emerald-50 text-emerald-600' :
                                    log.action === 'update' ? 'bg-indigo-50 text-indigo-600' :
                                        log.action === 'delete' ? 'bg-rose-50 text-rose-600' :
                                            'bg-amber-50 text-amber-600'
                                }`}>
                                <Clock className="w-4 h-4" />
                            </div>
                            <div>
                                <h4 className="text-sm font-bold text-slate-900 uppercase tracking-tight">
                                    {log.action}
                                </h4>
                                <p className="text-xs text-slate-400 font-medium">
                                    {new Date(log.created_at).toLocaleString()}
                                </p>
                            </div>
                        </div>
                        {log.actor_id && (
                            <div className="flex items-center gap-2 px-3 py-1 bg-slate-50 rounded-full border border-slate-100">
                                <User className="w-3 h-3 text-slate-400" />
                                <span className="text-[10px] font-bold text-slate-600 uppercase tracking-wider">{log.actor_id}</span>
                            </div>
                        )}
                    </div>

                    {log.action === 'update' && log.old_state && log.new_state && (
                        <div className="space-y-2 mt-4">
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Changes Detected</p>
                            <div className="grid gap-2">
                                {Object.keys(log.new_state).map((key) => {
                                    const oldVal = log.old_state[key];
                                    const newVal = log.new_state[key];
                                    if (oldVal !== newVal && key !== 'updated_at') {
                                        return (
                                            <div key={key} className="flex items-center gap-3 text-xs p-2 bg-slate-50 rounded-lg border border-slate-100/50">
                                                <span className="font-bold text-slate-500 min-w-[80px]">{key}:</span>
                                                <span className="text-rose-500 line-through truncate max-w-[100px]">{String(oldVal)}</span>
                                                <ArrowRight className="w-3 h-3 text-slate-300 shrink-0" />
                                                <span className="text-emerald-600 font-bold truncate">{String(newVal)}</span>
                                            </div>
                                        );
                                    }
                                    return null;
                                })}
                            </div>
                        </div>
                    )}

                    {log.action === 'create' && (
                        <div className="mt-4 p-3 bg-emerald-50/50 border border-emerald-100 rounded-xl">
                            <p className="text-[10px] font-bold text-emerald-700 uppercase tracking-widest mb-1">Initial State</p>
                            <p className="text-xs text-emerald-600 font-medium">Record successfully initialized in system.</p>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}
