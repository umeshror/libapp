"use client"
import React from 'react';
import { PopularBook } from '../../types';
import { Book as BookIcon, Trophy } from 'lucide-react';
import Link from 'next/link';

interface PopularBooksProps {
    data: PopularBook[];
}

export default function PopularBooks({ data }: PopularBooksProps) {
    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="p-4 border-b border-gray-50 flex items-center justify-between bg-gray-50/50">
                <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                    <Trophy size={18} className="text-amber-500" />
                    Popular Books
                </h3>
                <span className="text-xs text-gray-400 font-medium uppercase tracking-wider">All Time</span>
            </div>
            <div className="divide-y divide-gray-50">
                {data.length === 0 ? (
                    <div className="p-8 text-center text-gray-400 text-sm italic">
                        No borrow data yet
                    </div>
                ) : (
                    data.map((book, idx) => (
                        <Link
                            key={book.book_id}
                            href={`/books/${book.book_id}`}
                            className="flex items-center gap-4 p-4 hover:bg-blue-50/30 transition-colors group"
                        >
                            <div className="flex-shrink-0 w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center text-blue-600 group-hover:bg-blue-100 transition-colors">
                                <BookIcon size={20} />
                            </div>
                            <div className="flex-grow min-w-0">
                                <h4 className="text-sm font-semibold text-gray-900 truncate group-hover:text-blue-600 transition-colors">
                                    {book.title}
                                </h4>
                                <p className="text-xs text-gray-500 truncate">{book.author}</p>
                            </div>
                            <div className="text-right">
                                <p className="text-sm font-bold text-gray-900">{book.borrow_count}</p>
                                <p className="text-[10px] text-gray-400 uppercase font-medium">Borrows</p>
                            </div>
                        </Link>
                    ))
                )}
            </div>
        </div>
    );
}
