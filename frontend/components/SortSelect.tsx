'use client';

interface SortOption {
    label: string;
    value: string;
}

interface SortSelectProps {
    sortBy: string;
    order: string;
    options: SortOption[];
    onSortChange: (field: string, order: string) => void;
}

export default function SortSelect({ sortBy, order, options, onSortChange }: SortSelectProps) {
    return (
        <div className="flex gap-2">
            <select
                value={sortBy}
                onChange={(e) => onSortChange(e.target.value, order)}
                className="p-2 border rounded"
            >
                {options.map((option) => (
                    <option key={option.value} value={option.value}>
                        {option.label}
                    </option>
                ))}
            </select>

            <select
                value={order}
                onChange={(e) => onSortChange(sortBy, e.target.value)}
                className="p-2 border rounded"
            >
                <option value="asc">Ascending</option>
                <option value="desc">Descending</option>
            </select>
        </div>
    );
}
