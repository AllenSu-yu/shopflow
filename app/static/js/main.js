// 通用 JavaScript 函數

// 更新購物車數量
async function updateCartCount() {
    const token = localStorage.getItem('token');
    if (!token) {
        const cartCount = document.getElementById('cart-count');
        if (cartCount) cartCount.textContent = '0';
        return;
    }
    
    try {
        const response = await fetch('/api/cart', {
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
    // 只清除前台相關的 token 和用戶資訊
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    // 重定向到首頁
    window.location.href = '/';
}

// 後台登出功能
function adminLogout() {
    // 只清除後台相關的 token 和用戶資訊
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    // 重定向到後台登入頁
    window.location.href = '/admin/login';
}

// 檢查用戶登入狀態（用於模板）
function checkAuth() {
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('user');
    return {
        isAuthenticated: !!token,
        user: user ? JSON.parse(user) : null
    };
}

// 處理認證錯誤（401），清除 token 並引導用戶登入
function handleAuthError(response, errorMessage) {
    if (response && response.status === 401) {
        // 清除本地儲存的認證資訊
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        
        // 顯示錯誤訊息並引導用戶登入
        const message = errorMessage || '您的登入已過期，請重新登入';
        if (confirm(message + '\n\n是否前往登入頁面？')) {
            window.location.href = '/login';
        }
        return true; // 表示已處理認證錯誤
    }
    return false; // 不是認證錯誤
}
