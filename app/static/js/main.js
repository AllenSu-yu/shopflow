// 通用 JavaScript 函數

// 更新購物車數量
async function updateCartCount() {
    // 從 URL 取得 store_slug
    const pathParts = window.location.pathname.split('/');
    let storeSlug = '';
    if (pathParts[1] === 'shop' && pathParts[2] && pathParts[2] !== 'admin') {
        storeSlug = pathParts[2];
    }
    
    if (!storeSlug) return;

    const token = localStorage.getItem(`customer_token_${storeSlug}`);
    if (!token) {
        const cartCount = document.getElementById('cart-count');
        if (cartCount) cartCount.textContent = '0';
        return;
    }
    
    try {
        // 從 URL 取得 store_slug
        const pathParts = window.location.pathname.split('/');
        let storeSlug = '';
        if (pathParts[1] === 'shop' && pathParts[2] && pathParts[2] !== 'admin') {
            storeSlug = pathParts[2];
        }
        
        if (!storeSlug) return;

        const response = await fetch(`/api/shop/${storeSlug}/cart`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const cart = await response.json();
            const cartCount = document.getElementById('cart-count');
            if (cartCount) {
                // 安全地計算總商品數量
                const totalItems = (cart.items && Array.isArray(cart.items)) 
                    ? cart.items.reduce((sum, item) => sum + (item.quantity || 0), 0)
                    : 0;
                cartCount.textContent = totalItems;
            }
        } else if (response.status === 401) {
            // 認證失敗時，清除購物車數量顯示
            const cartCount = document.getElementById('cart-count');
            if (cartCount) cartCount.textContent = '0';
            // 不顯示錯誤提示，因為這是在背景更新購物車數量
        }
    } catch (error) {
        console.error('更新購物車數量失敗:', error);
    }
}

// 前台登出功能
function logout() {
    // 從 URL 取得 store_slug
    const pathParts = window.location.pathname.split('/');
    if (pathParts[1] === 'shop' && pathParts[2] && pathParts[2] !== 'admin') {
        const storeSlug = pathParts[2];
        localStorage.removeItem(`customer_token_${storeSlug}`);
        localStorage.removeItem(`customer_user_${storeSlug}`);
        // 重定向到該商店首頁
        window.location.href = `/shop/${storeSlug}`;
    } else {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/';
    }
}

// 後台登出功能
function adminLogout() {
    // 只清除後台相關的 token 和用戶資訊
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    // 重定向到後台登入頁
    window.location.href = '/shop/admin/login';
}

// 檢查用戶登入狀態（用於模板）
function checkAuth() {
    // 從 URL 取得 store_slug
    const pathParts = window.location.pathname.split('/');
    let storeSlug = '';
    if (pathParts[1] === 'shop' && pathParts[2] && pathParts[2] !== 'admin') {
        storeSlug = pathParts[2];
    }
    
    if (!storeSlug) return { isAuthenticated: false, user: null };

    const token = localStorage.getItem(`customer_token_${storeSlug}`);
    const user = localStorage.getItem(`customer_user_${storeSlug}`);
    return {
        isAuthenticated: !!token,
        user: user ? JSON.parse(user) : null
    };
}

// 處理認證錯誤（401），清除 token 並引導用戶登入
function handleAuthError(response, errorMessage) {
    if (response && response.status === 401) {
        // 清除本地儲存的認證資訊
        // 清除本地儲存的認證資訊
        const pathParts = window.location.pathname.split('/');
        if (pathParts[1] === 'shop' && pathParts[2] && pathParts[2] !== 'admin') {
            const storeSlug = pathParts[2];
            localStorage.removeItem(`customer_token_${storeSlug}`);
            localStorage.removeItem(`customer_user_${storeSlug}`);
        } else {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
        }
        
        // 顯示錯誤訊息並引導用戶登入
        const message = errorMessage || '您的登入已過期，請重新登入';
        if (confirm(message + '\n\n是否前往登入頁面？')) {
            const pathParts = window.location.pathname.split('/');
            if (pathParts[1] === 'shop' && pathParts[2] && pathParts[2] !== 'admin') {
                const storeSlug = pathParts[2];
                window.location.href = `/shop/${storeSlug}/login`;
            } else {
                window.location.href = '/login';
            }
        }
        return true; // 表示已處理認證錯誤
    }
    return false; // 不是認證錯誤
}
