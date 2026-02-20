"use client"
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { DailyBorrowCount, DailyActiveMember } from '../../types';

interface BorrowTrendChartProps {
    data: DailyBorrowCount[] | DailyActiveMember[];
    title: string;
    dataKey: string;
    color: string;
}

export default function BorrowTrendChart({ data, title, dataKey, color }: BorrowTrendChartProps) {
    if (!data || data.length === 0) {
        return <div className="h-64 flex items-center justify-center text-gray-500">No data available</div>;
    }

    return (
        <div className="bg-white p-4 rounded-lg shadow">
            <h3 className="text-lg font-semibold mb-4">{title}</h3>
            <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="count" stroke={color} name={dataKey} />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
