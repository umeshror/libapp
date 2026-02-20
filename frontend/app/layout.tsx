import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Link from 'next/link'
import Providers from './providers'
import { Toaster } from 'sonner'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
    title: 'Library Management System',
    description: 'Modern library management for books and members.',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en" className="h-full bg-gray-50 antialiased">
            <body className={`${inter.className} h-full flex flex-col`}>
                <Providers>
                    <Toaster richColors position="top-right" />
                    <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
                        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                            <div className="flex justify-between h-16">
                                <div className="flex">
                                    <div className="flex-shrink-0 flex items-center">
                                        <Link href="/" className="flex items-center gap-2">
                                            <div className="bg-blue-600 text-white p-1.5 rounded-lg">
                                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-6 h-6">
                                                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                                                </svg>
                                            </div>
                                            <span className="font-bold text-xl tracking-tight text-gray-900">LibApp</span>
                                        </Link>
                                    </div>
                                    <div className="hidden sm:ml-8 sm:flex sm:space-x-8">
                                        <NavLink href="/dashboard">Dashboard</NavLink>
                                        <NavLink href="/books">Books</NavLink>
                                        <NavLink href="/members">Members</NavLink>
                                        <NavLink href="/borrows">Borrows</NavLink>
                                    </div>
                                </div>
                                <div className="flex items-center">
                                    <div className="text-sm text-gray-500 italic">Admin Portal</div>
                                </div>
                            </div>
                        </div>
                    </nav>
                    <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-10">
                        {children}
                    </main>
                    <footer className="bg-white border-t border-gray-200 mt-auto">
                        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
                            <p className="text-center text-sm text-gray-400">&copy; 2026 Library Management System. All rights reserved.</p>
                        </div>
                    </footer>
                </Providers>
            </body>
        </html>
    )
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
    return (
        <Link
            href={href}
            className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:border-blue-500 hover:text-gray-900 transition-colors duration-200"
        >
            {children}
        </Link>
    )
}
