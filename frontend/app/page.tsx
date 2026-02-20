import Link from 'next/link'

export default function Home() {
  return (
    <div>
      <div className="text-center mb-16">
        <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 sm:text-5xl md:text-6xl">
          <span className="block xl:inline">Modern Library</span>{' '}
          <span className="block text-blue-600 xl:inline">Management</span>
        </h1>
        <p className="mt-3 max-w-md mx-auto text-base text-gray-500 sm:text-lg md:mt-5 md:text-xl md:max-w-3xl">
          Efficiently manage your book inventory, members, and borrowing records with our streamlined dashboard.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <DashboardCard
          href="/books"
          title="Books Inventory"
          description="Manage books catalog, check availability, and add new volumes."
          color="blue"
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
            </svg>
          }
        />

        <DashboardCard
          href="/members"
          title="Members"
          description="Register new members, view profiles, and manage active memberships."
          color="green"
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
            </svg>
          }
        />

        <DashboardCard
          href="/borrows"
          title="Active Borrows"
          description="Track active borrows, process returns, and monitor overdue items."
          color="purple"
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8">
              <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 7.5h-.75A2.25 2.25 0 004.5 9.75v7.5a2.25 2.25 0 002.25 2.25h7.5a2.25 2.25 0 002.25-2.25v-7.5a2.25 2.25 0 00-2.25-2.25h-.75m0-3l-3-3m0 0l-3 3m3-3v11.25" />
            </svg>
          }
        />
      </div>
    </div>
  )
}

interface DashboardCardProps {
  href: string;
  title: string;
  description: string;
  color: 'blue' | 'green' | 'purple';
  icon: React.ReactNode;
}

function DashboardCard({ href, title, description, color, icon }: DashboardCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-700 hover:bg-blue-100 border-blue-100',
    green: 'bg-green-50 text-green-700 hover:bg-green-100 border-green-100',
    purple: 'bg-purple-50 text-purple-700 hover:bg-purple-100 border-purple-100',
  };

  return (
    <Link
      href={href}
      className={`relative flex flex-col items-start p-8 rounded-2xl shadow-sm border transition-all duration-200 hover:shadow-md ${colorClasses[color] || 'bg-white'}`}
    >
      <div className="mb-4">
        {icon}
      </div>
      <h3 className="text-xl font-bold mb-2">{title}</h3>
      <p className="text-sm opacity-80 mb-4">{description}</p>
      <span className="mt-auto font-medium text-sm flex items-center">
        Access Module
        <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
        </svg>
      </span>
    </Link>
  )
}
