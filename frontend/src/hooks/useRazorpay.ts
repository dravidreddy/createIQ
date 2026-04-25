import { useCallback, useRef } from 'react';

declare global {
    interface Window {
        Razorpay: any;
    }
}

/**
 * Hook to dynamically load the Razorpay Checkout script and open the payment modal.
 */
export function useRazorpay() {
    const scriptLoadedRef = useRef(false);

    const loadScript = useCallback((): Promise<boolean> => {
        if (scriptLoadedRef.current || window.Razorpay) {
            scriptLoadedRef.current = true;
            return Promise.resolve(true);
        }

        return new Promise((resolve) => {
            const script = document.createElement('script');
            script.src = 'https://checkout.razorpay.com/v1/checkout.js';
            script.async = true;
            script.onload = () => {
                scriptLoadedRef.current = true;
                resolve(true);
            };
            script.onerror = () => resolve(false);
            document.body.appendChild(script);
        });
    }, []);

    const openCheckout = useCallback(async (options: {
        key: string;
        order_id: string;
        amount: number;
        currency: string;
        name: string;
        description: string;
        handler: (response: any) => void;
        prefill?: { email?: string; name?: string };
        theme?: { color?: string };
    }) => {
        const loaded = await loadScript();
        if (!loaded) {
            throw new Error('Razorpay SDK failed to load');
        }

        const rzp = new window.Razorpay(options);
        rzp.open();
    }, [loadScript]);

    return { openCheckout };
}
