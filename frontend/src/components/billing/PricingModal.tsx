import React, { useState, useEffect } from 'react';
import { billingApi } from '../../services/api';
import { useRazorpay } from '../../hooks/useRazorpay';
import { useAuthStore } from '../../store/authStore';
import { X, Coins, Sparkles, Zap, Crown, Loader2, CheckCircle2 } from 'lucide-react';
import toast from 'react-hot-toast';

interface PricingModalProps {
    isOpen: boolean;
    onClose: () => void;
}

interface CreditPackage {
    id: string;
    credits: number;
    amount_paise: number;
    label: string;
    price: string;
}

const PACKAGE_ICONS: Record<string, React.ReactNode> = {
    starter: <Coins className="w-6 h-6" />,
    popular: <Zap className="w-6 h-6" />,
    pro: <Crown className="w-6 h-6" />,
};

const PACKAGE_COLORS: Record<string, string> = {
    starter: 'from-blue-500/20 to-blue-600/10 border-blue-500/30',
    popular: 'from-accent/20 to-accent/10 border-accent/40',
    pro: 'from-purple-500/20 to-purple-600/10 border-purple-500/30',
};

export function PricingModal({ isOpen, onClose }: PricingModalProps) {
    const [packages, setPackages] = useState<CreditPackage[]>([]);
    const [loading, setLoading] = useState(false);
    const [purchasingId, setPurchasingId] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);
    const { openCheckout } = useRazorpay();
    const { user, refreshUser } = useAuthStore();

    useEffect(() => {
        if (isOpen) {
            loadPackages();
            setSuccess(false);
        }
    }, [isOpen]);

    const loadPackages = async () => {
        setLoading(true);
        try {
            const res = await billingApi.getPackages();
            setPackages(res.data?.packages || []);
        } catch (e) {
            toast.error('Failed to load packages');
        } finally {
            setLoading(false);
        }
    };

    const handlePurchase = async (pkg: CreditPackage) => {
        setPurchasingId(pkg.id);
        try {
            // 1. Create order on backend
            const orderRes = await billingApi.createOrder(pkg.id);
            const orderData = orderRes.data;

            // 2. Open Razorpay Checkout
            await openCheckout({
                key: orderData.key_id,
                order_id: orderData.order_id,
                amount: orderData.amount,
                currency: 'INR',
                name: 'CreatorIQ',
                description: `${pkg.label} Credit Pack`,
                prefill: {
                    email: user?.email || '',
                    name: user?.display_name || '',
                },
                theme: { color: '#6C63FF' },
                handler: async (response: any) => {
                    // 3. Verify payment on backend
                    try {
                        const verifyRes = await billingApi.verifyPayment({
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_signature: response.razorpay_signature,
                        });

                        if (verifyRes.data?.status === 'success') {
                            setSuccess(true);
                            toast.success(`${pkg.credits} credits added!`);
                            // Refresh user data to update credit display
                            if (refreshUser) await refreshUser();
                        }
                    } catch (e) {
                        toast.error('Payment verification failed');
                    }
                },
            });
        } catch (e) {
            toast.error('Failed to initiate payment');
        } finally {
            setPurchasingId(null);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

            {/* Modal */}
            <div className="relative bg-bg border border-white/10 rounded-[2rem] shadow-2xl w-full max-w-2xl mx-4 overflow-hidden animate-in zoom-in duration-300">
                {/* Header */}
                <div className="p-8 pb-4 flex items-center justify-between">
                    <div>
                        <h2 className="text-2xl font-display font-bold">Top Up Credits</h2>
                        <p className="text-text-secondary text-sm mt-1">
                            Current balance: <span className="text-accent font-semibold">{user?.credits ?? 0} credits</span>
                        </p>
                    </div>
                    <button onClick={onClose} className="p-2 text-text-secondary hover:text-text-primary transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Success State */}
                {success ? (
                    <div className="p-12 flex flex-col items-center gap-4 animate-in zoom-in">
                        <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center">
                            <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                        </div>
                        <h3 className="text-xl font-display font-bold">Payment Successful!</h3>
                        <p className="text-text-secondary text-center">Your credits have been added to your account.</p>
                        <button onClick={onClose} className="btn-primary py-2 px-6 mt-4">
                            Continue Creating
                        </button>
                    </div>
                ) : (
                    /* Packages Grid */
                    <div className="p-8 pt-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {loading ? (
                            <div className="col-span-3 py-12 flex justify-center">
                                <Loader2 className="w-8 h-8 text-accent animate-spin" />
                            </div>
                        ) : (
                            packages.map((pkg) => (
                                <div
                                    key={pkg.id}
                                    className={`relative p-6 rounded-2xl border bg-gradient-to-b ${PACKAGE_COLORS[pkg.id] || 'border-white/10'} transition-all hover:scale-[1.02] cursor-pointer group`}
                                    onClick={() => handlePurchase(pkg)}
                                >
                                    {pkg.id === 'popular' && (
                                        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-accent text-bg text-[10px] font-bold uppercase tracking-widest rounded-full">
                                            Most Popular
                                        </div>
                                    )}
                                    <div className="flex flex-col items-center gap-4 text-center">
                                        <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center text-accent group-hover:scale-110 transition-transform">
                                            {PACKAGE_ICONS[pkg.id] || <Coins className="w-6 h-6" />}
                                        </div>
                                        <div>
                                            <div className="text-3xl font-display font-bold">{pkg.credits}</div>
                                            <div className="text-xs text-text-secondary uppercase tracking-widest">credits</div>
                                        </div>
                                        <div className="text-lg font-semibold">{pkg.price}</div>
                                        <button
                                            disabled={purchasingId === pkg.id}
                                            className="w-full py-2 px-4 rounded-xl bg-white/5 border border-white/10 text-sm font-medium hover:bg-white/10 transition-all disabled:opacity-50"
                                        >
                                            {purchasingId === pkg.id ? (
                                                <Loader2 className="w-4 h-4 animate-spin mx-auto" />
                                            ) : (
                                                'Buy Now'
                                            )}
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                )}

                {/* Footer */}
                <div className="px-8 pb-6 text-center">
                    <p className="text-[10px] text-text-secondary/50 font-mono">
                        1 pipeline run = 10 credits • Payments powered by Razorpay • Secure checkout
                    </p>
                </div>
            </div>
        </div>
    );
}
