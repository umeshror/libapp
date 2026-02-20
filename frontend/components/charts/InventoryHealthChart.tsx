"use client"
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';
import { InventoryHealth } from '../../types';

interface InventoryHealthChartProps {
    data: InventoryHealth;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28'];

export default function InventoryHealthChart({ data }: InventoryHealthChartProps) {
    if (!data) return null;

    const chartData = [
        { name: 'Low Stock', value: data.low_stock_books },
        { name: 'Never Borrowed', value: data.never_borrowed_books },
        { name: 'Unavailable', value: data.fully_unavailable_books },
    ];

    // Filter out zero values to avoid ugly empty segments? Or keep them.
    const validData = chartData.filter(d => d.value > 0);

    if (validData.length === 0) {
        return <div className="h-64 flex items-center justify-center text-gray-500">No data available</div>;
    }

    return (
        <div className="bg-white p-4 rounded-lg shadow">
            <h3 className="text-lg font-semibold mb-4">Inventory Health Distribution</h3>
            <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie
                            data={validData}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            label={({ name, percent }: { name?: string, percent?: number }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                            outerRadius={80}
                            fill="#8884d8"
                            dataKey="value"
                        >
                            {validData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                        </Pie>
                        <Tooltip />
                    </PieChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
