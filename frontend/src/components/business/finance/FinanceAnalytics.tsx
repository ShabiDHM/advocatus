// FILE: src/components/business/finance/FinanceAnalytics.tsx
// PHOENIX PROTOCOL - FINANCE ANALYTICS V7.0 (CENTRALIZED COLORS)
// V7.0: Zero ngjyra hardcoded. Të gjitha referencat nga CSS variables.

import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import { TrendingUp, BarChart2, FileText } from 'lucide-react';
import { AnalyticsDashboardData, TopProductItem } from '../../../data/types';
import { useTranslation } from 'react-i18next';

interface FinanceAnalyticsProps {
    data: AnalyticsDashboardData;
}

export const FinanceAnalytics: React.FC<FinanceAnalyticsProps> = ({ data }) => {
    const { t } = useTranslation();

    // Chart colors — referojnë CSS variables për konsistencë dark/light
    const productColors = [
        'var(--chart-1)',
        'var(--chart-2)',
        'var(--chart-3)',
        'var(--chart-4)',
        'var(--chart-5)',
    ];

    return (
        <div className="space-y-6">
            {/* Sales Trend Chart */}
            <div className="glass-panel border border-main rounded-2xl p-4">
                <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2">
                    <TrendingUp size={16} className="text-primary-start" /> {t('finance.analytics.salesTrend')}
                </h4>
                <div className="h-64 w-full min-h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={data.sales_trend}>
                            <defs>
                                <linearGradient id="colorSales" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="var(--chart-blue)" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="var(--chart-blue)" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                            <XAxis 
                                dataKey="date" 
                                stroke="var(--text-muted)" 
                                fontSize={12} 
                                tickFormatter={(str) => str.slice(5)} 
                                tick={{ fill: 'var(--text-muted)' }} 
                            />
                            <YAxis 
                                stroke="var(--text-muted)" 
                                fontSize={12} 
                                tick={{ fill: 'var(--text-muted)' }} 
                                width={40} 
                            />
                            <Tooltip 
                                contentStyle={{ 
                                    backgroundColor: 'var(--bg-card)', 
                                    borderColor: 'var(--border-main)', 
                                    color: 'var(--text-primary)', 
                                    borderRadius: '12px',
                                    boxShadow: 'var(--shadow-md)'
                                }} 
                                formatter={(value: any) => [`€${Number(value).toFixed(2)}`, t('finance.income')]} 
                                labelStyle={{ color: 'var(--text-muted)', marginBottom: '4px' }} 
                            />
                            <Area 
                                type="monotone" 
                                dataKey="amount" 
                                stroke="var(--chart-blue)" 
                                strokeWidth={3} 
                                fillOpacity={1} 
                                fill="url(#colorSales)" 
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-2">
                {/* Top Products Chart */}
                <div className="glass-panel border border-main rounded-2xl p-4">
                    <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2">
                        <BarChart2 size={16} className="text-success-start" /> {t('finance.analytics.topProducts')}
                    </h4>
                    <div className="h-64 w-full min-h-[250px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={data.top_products} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" horizontal={true} vertical={false} />
                                <XAxis type="number" stroke="var(--text-muted)" fontSize={12} hide />
                                <YAxis 
                                    dataKey="product_name" 
                                    type="category" 
                                    stroke="var(--text-muted)" 
                                    fontSize={12} 
                                    width={100} 
                                    tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} 
                                />
                                <Tooltip 
                                    contentStyle={{ 
                                        backgroundColor: 'var(--bg-card)', 
                                        borderColor: 'var(--border-main)', 
                                        color: 'var(--text-primary)', 
                                        borderRadius: '12px',
                                        boxShadow: 'var(--shadow-md)'
                                    }} 
                                    formatter={(value: any) => [`€${Number(value).toFixed(2)}`, t('finance.analytics.tableValue')]} 
                                />
                                <Bar dataKey="total_revenue" fill="var(--chart-green)" radius={[0, 4, 4, 0]} barSize={20}>
                                    {data.top_products.map((_: TopProductItem, index: number) => (
                                        <Cell key={`cell-${index}`} fill={productColors[index % productColors.length]} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Product Details Table */}
                <div className="glass-panel border border-main rounded-2xl p-4 flex flex-col">
                    <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2">
                        <FileText size={16} className="text-primary-start" /> {t('finance.analytics.productDetails')}
                    </h4>
                    <div className="overflow-y-auto max-h-64 custom-finance-scroll pr-2 flex-1">
                        <table className="w-full text-sm text-left text-text-secondary">
                            <thead className="text-xs text-text-muted uppercase bg-surface/30 sticky top-0 backdrop-blur-sm">
                                <tr>
                                    <th className="px-3 py-2 rounded-tl-lg">{t('finance.analytics.tableProduct')}</th>
                                    <th className="px-3 py-2 text-right">{t('finance.analytics.tableQty')}</th>
                                    <th className="px-3 py-2 text-right rounded-tr-lg">{t('finance.analytics.tableValue')}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-main">
                                {data.top_products.map((p: TopProductItem, i: number) => (
                                    <tr key={i} className="hover:bg-surface/20 transition-colors">
                                        <td className="px-3 py-2 font-medium text-text-primary truncate max-w-[120px]" title={p.product_name}>
                                            {p.product_name}
                                        </td>
                                        <td className="px-3 py-2 text-right font-mono text-text-muted">{p.total_quantity}</td>
                                        <td className="px-3 py-2 text-right font-bold text-success-start">€{p.total_revenue.toFixed(2)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
};