import React, { lazy, Suspense, useState, useEffect, useCallback } from 'react';
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
import { CategoriesView } from './components/Catalog/CategoriesView';
import { flattenCategories } from './utils/formatters';

import { ProductDetail } from './components/Product/ProductDetail';
import { CartView } from './components/Cart/CartView';
import { CheckoutView } from './components/Checkout/CheckoutView';
import { ProfileView } from './components/Profile/ProfileView';
import { OrderDetailView } from './components/Order/OrderDetailView';

import { DropsSection } from './components/Drops/DropsSection';
import { DropDetail } from './components/Drops/DropDetail';
import { AdminView } from './components/Admin/AdminView';

const DevHub = lazy(() => import('./components/DevHub/DevHub'));

export const App = () => {
  // Navigation & View Routing
  const [currentView, setCurrentView] = useState(() => {
    if (typeof window !== 'undefined' && window.location.pathname.startsWith('/dev')) {
      return 'dev';
    }
    return 'catalog';
  }); // 'catalog' | 'product' | 'cart' | 'checkout' | 'auth' | 'order-detail' | 'dev' | 'drops' | 'drop-detail' | 'admin'

  const [selectedProductSlug, setSelectedProductSlug] = useState(null);
  const [selectedOrderId, setSelectedOrderId] = useState(null);
  const [selectedDropIdentifier, setSelectedDropIdentifier] = useState(null);
  const [selectedDropInfo, setSelectedDropInfo] = useState(null);
  const [profileTab, setProfileTab] = useState('profile'); // 'profile' | 'wishlist' | 'orders' | 'notifications'
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // Sync URL pathname with currentView
  useEffect(() => {
    const handlePopState = () => {
      if (window.location.pathname.startsWith('/dev')) {
        setCurrentView('dev');
      } else {
        setCurrentView('catalog');
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Update browser history when view changes manually
  useEffect(() => {
    if (currentView === 'dev') {
      if (window.location.pathname !== '/dev') {
        window.history.pushState({}, '', '/dev');
      }
    } else {
      if (window.location.pathname === '/dev') {
        window.history.pushState({}, '', '/');
      }
    }
  }, [currentView]);

  // Global Data & Catalog Filters
  const [categoriesData, setCategoriesData] = useState([]);
  const [brandsData, setBrandsData] = useState([]);
  const [activeCategoryId, setActiveCategoryId] = useState(null);
  const [activeBrandId, setActiveBrandId] = useState(null);
  const [activeSize, setActiveSize] = useState(null);
  const [activePriceFrom, setActivePriceFrom] = useState('');
  const [activePriceTo, setActivePriceTo] = useState('');
  const [activeSort, setActiveSort] = useState('created_at');
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

  useEffect(() => {
    const openAuth = () => {
      setProfileTab('wishlist');
      setCurrentView('auth');
    };
    window.addEventListener('flashmarket:auth-required', openAuth);
    return () => window.removeEventListener('flashmarket:auth-required', openAuth);
  }, []);

  // Initial load: Categories & Brands
  useEffect(() => {
    if (currentView === 'dev') return undefined;
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
    return undefined;
  }, [currentView]);

  // Fetch Catalog Products
  const loadCatalog = useCallback(async (replace = true, offsetToUse = 0) => {
    if (currentView === 'dev') return;
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
      if (activeSize) params.set('size', activeSize);
      if (activePriceFrom) params.set('price_from', activePriceFrom);
      if (activePriceTo) params.set('price_to', activePriceTo);

      if (activeSearch) {
        params.set('search', activeSearch);
        params.set('sort_by', 'relevance');
      } else if (activeSort) {
        if (activeSort.startsWith('price_')) {
          params.set('sort_by', 'price');
          params.set('sort_order', activeSort.endsWith('_asc') ? 'asc' : 'desc');
        } else {
          params.set('sort_by', activeSort);
        }
      }

      const data = await apiJson('/api/v1/products?' + params.toString());
      const items = Array.isArray(data) ? data : (data.items || []);
      const total = data.total || items.length || 0;

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
  }, [activeCategoryId, activeBrandId, activeSize, activePriceFrom, activePriceTo, activeSort, activeSearch, currentView]);

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

  const handleSearchChange = useCallback((query) => {
    setActiveSearch(query);
  }, []);

  const handleGoHome = () => {
    setCurrentView('catalog');
    setActiveCategoryId(null);
    setActiveBrandId(null);
    setActiveSize(null);
    setActivePriceFrom('');
    setActivePriceTo('');
    setActiveSort('created_at');
    setActiveSearch('');
    setSelectedDropInfo(null);
  };

  const handleOpenProduct = (slug, dropInfo = null) => {
    setSelectedProductSlug(slug);
    setSelectedDropInfo(dropInfo);
    setCurrentView('product');
  };

  const handleOpenDrop = (dropIdentifier) => {
    setSelectedDropIdentifier(dropIdentifier);
    setCurrentView('drop-detail');
  };

  const handleOpenOrder = (orderId) => {
    setSelectedOrderId(orderId);
    setCurrentView('order-detail');
  };

  const activeBrand = brandsData.find(b => b.id === activeBrandId);
  const activeCategory = activeCategoryId ? flattenCategories(categoriesData).find(c => c.id === activeCategoryId) : null;

  if (currentView === 'dev') {
    return (
      <Suspense fallback={<div className="min-h-screen bg-[#0B0B0C]" aria-busy="true" />}>
        <DevHub
          onBackToStore={() => {
            handleGoHome();
            window.history.pushState({}, '', '/');
          }}
        />
      </Suspense>
    );
  }

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
        currentView={currentView}
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
              activeCategory={activeCategory}
              resetCategoryFilter={() => handleFilterCategory(null)}
            />

            <DropsSection
              onSelectDrop={handleOpenDrop}
              onViewAllDrops={() => setCurrentView('drops')}
            />

            <BrandsGallery
              brandsData={brandsData}
              onSelectBrand={handleSelectBrand}
              activeCategoryId={activeCategoryId}
              activeBrandId={activeBrandId}
            />

            <CatalogControls
              brandsData={brandsData}
              activeBrandId={activeBrandId}
              onSelectBrandSelect={handleSelectBrand}
              activeSize={activeSize}
              onSelectSize={setActiveSize}
              priceFrom={activePriceFrom}
              priceTo={activePriceTo}
              onPriceFromChange={setActivePriceFrom}
              onPriceToChange={setActivePriceTo}
              activeSort={activeSort}
              onSelectSort={setActiveSort}
              onSearchChange={handleSearchChange}
            />

            <ProductGrid
              productsList={productsList}
              loading={loadingCatalog}
              error={errorCatalog}
              onRetry={() => loadCatalog(true, 0)}
              onOpenProduct={(slug) => handleOpenProduct(slug, null)}
              hasMore={catalogOffset + CATALOG_LIMIT < catalogTotal}
              loadingMore={loadingMore}
              onLoadMore={handleLoadMore}
            />
          </>
        )}

        {currentView === 'categories' && (
          <CategoriesView
            categoriesData={categoriesData}
            activeCategoryId={activeCategoryId}
            onSelectCategory={(catId) => {
              handleFilterCategory(catId);
              setCurrentView('catalog');
            }}
            onBack={() => setCurrentView('catalog')}
          />
        )}

        {currentView === 'drops' && (
          <div className="max-w-[1280px] mx-auto my-6 md:my-8 px-3.5 md:px-6">
            <button className="text-[11px] font-bold uppercase mb-6 cursor-pointer text-text-muted hover:text-black" onClick={() => setCurrentView('catalog')}>
              ← Назад в каталог
            </button>
            <DropsSection
              onSelectDrop={handleOpenDrop}
              showAll
            />
          </div>
        )}

        {currentView === 'drop-detail' && (
          <DropDetail
            dropIdentifier={selectedDropIdentifier}
            onOpenProductWithDrop={(slug, dropInfo) => handleOpenProduct(slug, dropInfo)}
            onBack={() => setCurrentView('catalog')}
          />
        )}

        {currentView === 'product' && (
          <ProductDetail
            productSlug={selectedProductSlug}
            dropInfo={selectedDropInfo}
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
            onOpenProduct={(slug) => handleOpenProduct(slug, null)}
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

        {currentView === 'admin' && (
          <AdminView
            onBack={() => setCurrentView('catalog')}
          />
        )}
      </main>

      <Toast />
    </div>
  );
};
