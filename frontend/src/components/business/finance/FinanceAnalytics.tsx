// FILE: src/components/business/finance/FinanceAnalytics.tsx
// PHOENIX PROTOCOL - FINANCE ANALYTICS V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Converted to semantic classes: bg-canvas, glass-panel, border-main, text-text-primary, text-text-secondary, text-text-muted.
// 2. Chart colors use semantic variables (primary-start, success-start, etc.).
// 3. Tooltip styling uses semantic glass-panel.
// 4. Preserved all analytics functionality.

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

    const productColors = [
        '#34d399', // success-start
        '#60a5fa', // primary-start variant
        '#fbbf24', // warning-start
        '#f87171', // danger-start
        '#a78bfa', // secondary-start
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
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                            <XAxis 
                                dataKey="date" 
                                stroke="#6b7280" 
                                fontSize={12} 
                                tickFormatter={(str) => str.slice(5)} 
                                tick={{ fill: '#9ca3af' }} 
                            />
                            <YAxis 
                                stroke="#6b7280" 
                                fontSize={12} 
                                tick={{ fill: '#9ca3af' }} 
                                width={40} 
                            />
                            <Tooltip 
                                contentStyle={{ 
                                    backgroundColor: 'var(--bg-canvas)', 
                                    borderColor: 'var(--border-main)', 
                                    color: 'var(--text-primary)', 
                                    borderRadius: '12px',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
                                }} 
                                formatter={(value: any) => [`€${Number(value).toFixed(2)}`, t('finance.income')]} 
                                labelStyle={{ color: '#9ca3af', marginBottom: '4px' }} 
                            />
                            <Area 
                                type="monotone" 
                                dataKey="amount" 
                                stroke="#3b82f6" 
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
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" horizontal={true} vertical={false} />
                                <XAxis type="number" stroke="#6b7280" fontSize={12} hide />
                                <YAxis 
                                    dataKey="product_name" 
                                    type="category" 
                                    stroke="#9ca3af" 
                                    fontSize={12} 
                                    width={100} 
                                    tick={{ fill: '#e5e7eb', fontSize: 12 }} 
                                />
                                <Tooltip 
                                    contentStyle={{ 
                                        backgroundColor: 'var(--bg-canvas)', 
                                        borderColor: 'var(--border-main)', 
                                        color: 'var(--text-primary)', 
                                        borderRadius: '12px',
                                        boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
                                    }} 
                                    formatter={(value: any) => [`€${Number(value).toFixed(2)}`, t('finance.analytics.tableValue')]} 
                                />
                                <Bar dataKey="total_revenue" fill="#10b981" radius={[0, 4, 4, 0]} barSize={20}>
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