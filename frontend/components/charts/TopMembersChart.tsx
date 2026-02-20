"use client"
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { TopMember } from '../../types';

interface TopMembersChartProps {
    data: TopMember[];
}

export default function TopMembersChart({ data }: TopMembersChartProps) {
    if (!data || data.length === 0) {
        return <div className="h-64 flex items-center justify-center text-gray-500">No data available</div>;
    }

    return (
        <div className="bg-white p-4 rounded-lg shadow">
            <h3 className="text-lg font-semibold mb-4">Top Active Members</h3>
            <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" />
                        <YAxis type="category" dataKey="name" width={100} />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="borrow_count" fill="#8884d8" name="Borrows" />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
