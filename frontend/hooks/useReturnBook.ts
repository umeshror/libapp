'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { returnBook } from '@/lib/api';

interface UseReturnBookOptions {
    onSuccess?: (data: any) => void;
    onError?: (error: Error) => void;
}

export function useReturnBook(options: UseReturnBookOptions = {}) {
    const queryClient = useQueryClient();

    const mutation = useMutation({
        mutationFn: (borrowId: string) => returnBook(borrowId),
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['borrows'] });
            queryClient.invalidateQueries({ queryKey: ['books'] });
            queryClient.invalidateQueries({ queryKey: ['members'] });

            toast.success('Book returned successfully');

            if (options.onSuccess) {
                options.onSuccess(data);
            }
        },
        onError: (err: Error) => {
            const message = err.message || 'Failed to return book';
            toast.error(message);

            if (options.onError) {
                options.onError(err);
            }
        },
    });

    return {
        returnBook: mutation.mutate,
        isPending: mutation.isPending,
        error: mutation.error,
    };
}
