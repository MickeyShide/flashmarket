import React, { useState, useEffect, useCallback } from 'react';
import { apiJson } from './services/api';
import { CATALOG_LIMIT } from './config/constants';

import { TopAnnouncement } from './components/Layout/TopAnnouncement';
import { Header } from './components/Layout/Header';
import { CategoryNav } from './components/Layout/CategoryNav';
import { Toast } from './components/Layout/Toast';

import { BrandActiveBanner } from './components/Catalog/BrandActiveBanner';
import { BrandsGallery } from './components/Catalog/BrandsGallery';
import { CatalogControls } from './components/Catalog/CatalogControls';
import { ProductGrid } from './components/Catalog/ProductGrid';

import { ProductDetail } from './components/Product/ProductDetail';
import { CartView } from './components/Cart/CartView';
import { CheckoutView } from './components/Checkout/CheckoutView';
import { ProfileView } from './components/Profile/ProfileView';
import { OrderDetailView } from './components/Order/OrderDetailView';

export const App = () => {
  // Navigation & View Routing
  const [currentView, setCurrentView] = useState('catalog'); // 'catalog' | 'product' | 'cart' | 'checkout' | 'auth' | 'order-detail'
  const [selectedProductSlug, setSelectedProductSlug] = useState(null);
  const [selectedOrderId, setSelectedOrderId] = useState(null);
  const [profileTab, setProfileTab] = useState('profile'); // 'profile' | 'orders' | 'notifications'
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // Global Data & Catalog Filters
  const [categoriesData, setCategoriesData] = useState([]);
  const [brandsData, setBrandsData] = useState([]);
  const [activeCategoryId, setActiveCategoryId] = useState(null);
  const [activeBrandId, setActiveBrandId] = useState(null);
  const [activeStatus, setActiveStatus] = useState(null);
  const [activeSearch, setActiveSearch] = useState('');

  // Catalog State & Pagination
  const [productsList, setProductsList] = useState([]);
  const [catalogOffset, setCatalogOffset] = useState(0);
  const [catalogTotal, setCatalogTotal] = useState(0);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [errorCatalog, setErrorCatalog] = useState(null);

  // Scroll to top on view change
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [currentView]);

  // Initial load: Categories & Brands
  useEffect(() => {
    async function initData() {
      try {
        const [cats, bnd] = await Promise.all([
          apiJson('/api/v1/categories').catch(() => []),
          apiJson('/api/v1/brands').catch(() => [])
        ]);
        setCategoriesData(cats);
        setBrandsData(bnd);
      } catch (err) {
        console.error('Initial data load error:', err);
      }
    }
    initData();
  }, []);

  // Fetch Catalog Products
  const loadCatalog = useCallback(async (replace = true, offsetToUse = 0) => {
    if (replace) {
      setLoadingCatalog(true);
      setErrorCatalog(null);
    } else {
      setLoadingMore(true);
    }

    try {
      const params = new URLSearchParams();
      params.set('limit', CATALOG_LIMIT);
      params.set('offset', offsetToUse);
      if (activeCategoryId) params.set('category_id', activeCategoryId);
      if (activeBrandId) params.set('brand_id', activeBrandId);
      if (activeStatus) params.set('status', activeStatus);
      if (activeSearch) params.set('search', activeSearch);

      const data = await apiJson('/api/v1/products?' + params.toString());
      const items = data.items || [];
      const total = data.total || 0;

      setCatalogTotal(total);

      if (replace) {
        setProductsList(items);
        setCatalogOffset(0);
      } else {
        setProductsList(prev => [...prev, ...items]);
        setCatalogOffset(offsetToUse);
      }
    } catch (err) {
      if (replace) {
        setErrorCatalog(err.message);
      }
    } finally {
      setLoadingCatalog(false);
      setLoadingMore(false);
    }
  }, [activeCategoryId, activeBrandId, activeStatus, activeSearch]);

  // Re-fetch catalog on filter changes
  useEffect(() => {
    loadCatalog(true, 0);
  }, [loadCatalog]);

  // Load More Handler
  const handleLoadMore = () => {
    const nextOffset = catalogOffset + CATALOG_LIMIT;
    loadCatalog(false, nextOffset);
  };

  // Filter actions
  const handleFilterCategory = (catId) => {
    setCurrentView('catalog');
    setActiveCategoryId(catId);
  };

  const handleSelectBrand = (brandId) => {
    setCurrentView('catalog');
    setActiveBrandId(brandId);
  };

  const handleResetBrandFilter = () => {
    setActiveBrandId(null);
  };

  const handleFilterStatus = (status) => {
    setActiveStatus(status);
  };

  const handleSearchChange = (query) => {
    setActiveSearch(query);
  };

  const handleGoHome = () => {
    setCurrentView('catalog');
    setActiveCategoryId(null);
    setActiveBrandId(null);
    setActiveStatus(null);
    setActiveSearch('');
  };

  const handleOpenProduct = (slug) => {
    setSelectedProductSlug(slug);
    setCurrentView('product');
  };

  const handleOpenOrder = (orderId) => {
    setSelectedOrderId(orderId);
    setCurrentView('order-detail');
  };

  const activeBrand = brandsData.find(b => b.id === activeBrandId);

  return (
    <div className="min-h-screen flex flex-col bg-bg-primary text-text-main font-sans">
      <TopAnnouncement />
      <Header
        currentView={currentView}
        setCurrentView={setCurrentView}
        toggleMobileNav={() => setMobileNavOpen(prev => !prev)}
        goHome={handleGoHome}
        switchProfileTab={setProfileTab}
      />
      <CategoryNav
        categoriesData={categoriesData}
        activeCategoryId={activeCategoryId}
        activeBrandId={activeBrandId}
        filterCategory={handleFilterCategory}
        mobileNavOpen={mobileNavOpen}
        closeMobileNav={() => setMobileNavOpen(false)}
        setCurrentView={setCurrentView}
        switchProfileTab={setProfileTab}
      />

      {/* Main Content Area */}
      <main className="flex-1">
        {currentView === 'catalog' && (
          <>
            <BrandActiveBanner
              activeBrand={activeBrand}
              resetBrandFilter={handleResetBrandFilter}
            />

            <BrandsGallery
              brandsData={brandsData}
              onSelectBrand={handleSelectBrand}
              activeCategoryId={activeCategoryId}
            />

            <CatalogControls
              brandsData={brandsData}
              activeBrandId={activeBrandId}
              onSelectBrandSelect={handleSelectBrand}
              activeStatus={activeStatus}
              onFilterStatus={handleFilterStatus}
              onSearchChange={handleSearchChange}
            />

            <ProductGrid
              productsList={productsList}
              loading={loadingCatalog}
              error={errorCatalog}
              onRetry={() => loadCatalog(true, 0)}
              onOpenProduct={handleOpenProduct}
              hasMore={catalogOffset + CATALOG_LIMIT < catalogTotal}
              loadingMore={loadingMore}
              onLoadMore={handleLoadMore}
            />
          </>
        )}

        {currentView === 'product' && (
          <ProductDetail
            productSlug={selectedProductSlug}
            onBack={() => setCurrentView('catalog')}
          />
        )}

        {currentView === 'cart' && (
          <CartView
            onBack={() => setCurrentView('catalog')}
            onGoToCatalog={() => setCurrentView('catalog')}
            onGoToCheckout={() => setCurrentView('checkout')}
          />
        )}

        {currentView === 'checkout' && (
          <CheckoutView
            onBack={() => setCurrentView('cart')}
            onCheckoutSuccess={() => {
              setCurrentView('auth');
              setProfileTab('orders');
            }}
            onGoToAuth={() => setCurrentView('auth')}
          />
        )}

        {currentView === 'auth' && (
          <ProfileView
            activeTab={profileTab}
            setActiveTab={setProfileTab}
            onSelectOrder={handleOpenOrder}
            onBack={() => setCurrentView('catalog')}
          />
        )}

        {currentView === 'order-detail' && (
          <OrderDetailView
            orderId={selectedOrderId}
            onBack={() => {
              setCurrentView('auth');
              setProfileTab('orders');
            }}
          />
        )}
      </main>

      <Toast />
    </div>
  );
};
