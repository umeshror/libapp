"use client"
import React from 'react';
import { RecentActivity as RecentActivityType } from '../../types';
import { ArrowUpRight, ArrowDownLeft, Clock } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface RecentActivityProps {
    data: RecentActivityType[];
}

export default function RecentActivity({ data }: RecentActivityProps) {
    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="p-4 border-b border-gray-50 flex items-center justify-between bg-gray-50/50">
                <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                    <Clock size={18} className="text-blue-500" />
                    Recent Activity
                </h3>
                <span className="text-xs text-gray-400 font-medium uppercase tracking-wider">Live Feed</span>
            </div>
            <div className="divide-y divide-gray-50 max-h-[400px] overflow-y-auto custom-scrollbar">
                {data.length === 0 ? (
                    <div className="p-8 text-center text-gray-400 text-sm italic">
                        No recent activity
                    </div>
                ) : (
                    data.map((activity) => (
                        <div key={activity.id} className="p-4 hover:bg-gray-50 transition-colors flex gap-3">
                            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${activity.type === 'borrow'
                                    ? 'bg-orange-50 text-orange-600'
                                    : 'bg-green-50 text-green-600'
                                }`}>
                                {activity.type === 'borrow'
                                    ? <ArrowUpRight size={16} />
                                    : <ArrowDownLeft size={16} />
                                }
                            </div>
                            <div className="flex-grow min-w-0">
                                <p className="text-sm text-gray-900 leading-tight">
                                    <span className="font-semibold">{activity.member_name}</span>
                                    {activity.type === 'borrow' ? ' borrowed ' : ' returned '}
                                    <span className="font-medium text-blue-600">{activity.book_title}</span>
                                </p>
                                <p className="text-[11px] text-gray-400 mt-1 flex items-center gap-1">
                                    <Clock size={10} />
                                    {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                                </p>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
