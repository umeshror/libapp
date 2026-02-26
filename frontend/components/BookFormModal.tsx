'use client';

import React, { useState, useEffect } from 'react';
import FormModal from './FormModal';
import { Book } from '../types';

interface BookFormModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (data: Partial<Book>) => void;
    book?: Book | null;
    isLoading?: boolean;
}

export default function BookFormModal({
    isOpen,
    onClose,
    onSave,
    book = null,
    isLoading = false,
}: BookFormModalProps) {
    const [formData, setFormData] = useState({
        title: '',
        author: '',
        isbn: '',
        total_copies: 1,
    });

    useEffect(() => {
        if (book) {
            setFormData({
                title: book.title,
                author: book.author,
                isbn: book.isbn,
                total_copies: book.total_copies,
            });
        } else {
            setFormData({
                title: '',
                author: '',
                isbn: '',
                total_copies: 1,
            });
        }
    }, [book, isOpen]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData((prev) => ({
            ...prev,
            [name]: name === 'total_copies' ? parseInt(value) || 0 : value,
        }));
    };

    const isInvalid = !formData.title || !formData.author || !formData.isbn || formData.total_copies < 1;

    return (
        <FormModal
            isOpen={isOpen}
            onClose={onClose}
            onSave={() => onSave(formData)}
            title={book ? 'Edit Book' : 'Add New Book'}
            isLoading={isLoading}
            isSaveDisabled={isInvalid}
            saveLabel={book ? 'Update Book' : 'Create Book'}
        >
            <div className="space-y-4">
                <div className="space-y-1.5">
                    <label className="text-sm font-bold text-slate-700 ml-1">Title</label>
                    <input
                        type="text"
                        name="title"
                        value={formData.title}
                        onChange={handleChange}
                        placeholder="e.g. Clean Code"
                        className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all outline-none"
                    />
                </div>

                <div className="space-y-1.5">
                    <label className="text-sm font-bold text-slate-700 ml-1">Author</label>
                    <input
                        type="text"
                        name="author"
                        value={formData.author}
                        onChange={handleChange}
                        placeholder="e.g. Robert C. Martin"
                        className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all outline-none"
                    />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                        <label className="text-sm font-bold text-slate-700 ml-1">ISBN</label>
                        <input
                            type="text"
                            name="isbn"
                            value={formData.isbn}
                            onChange={handleChange}
                            placeholder="e.g. 978-0132350884"
                            className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all outline-none"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-sm font-bold text-slate-700 ml-1">Total Copies</label>
                        <input
                            type="number"
                            name="total_copies"
                            min="1"
                            value={formData.total_copies}
                            onChange={handleChange}
                            className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all outline-none"
                        />
                    </div>
                </div>
            </div>
        </FormModal>
    );
}
