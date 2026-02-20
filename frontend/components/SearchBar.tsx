'use client';

import { useState, useEffect } from 'react';

interface SearchBarProps {
    initialValue: string;
    onSearch: (value: string) => void;
    placeholder?: string;
}

export default function SearchBar({ initialValue, onSearch, placeholder }: SearchBarProps) {
    const [value, setValue] = useState(initialValue);

    useEffect(() => {
        setValue(initialValue);
    }, [initialValue]);

    useEffect(() => {
        const timeoutId = setTimeout(() => {
            onSearch(value);
        }, 300); // 300ms debounce

        return () => clearTimeout(timeoutId);
    }, [value, onSearch]);

    return (
        <div className="relative">
            <input
                type="text"
                placeholder={placeholder || "Search books..."}
                className="p-2 pl-8 border rounded w-full md:w-64"
                value={value}
                onChange={(e) => setValue(e.target.value)}
            />
            <svg
                className="w-4 h-4 absolute left-2.5 top-3 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
            >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
        </div>
    );
}
