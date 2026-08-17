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
import { flattenCategories } from './utils/formatters';

import { DropsSection } from './components/Drops/DropsSection';
import { usePaginatedResource } from './hooks/usePaginatedResource';

import { parseRoute, formatRouteUrl } from './utils/router';

const lazyNamed = (loader, exportName) => lazy(() => loader().then(module => ({ default: module[exportName] })));

import ArchitectureView from './components/Architecture/ArchitectureView';
const DevHub = lazy(() => import('./components/DevHub/DevHub'));
const CategoriesView = lazyNamed(() => import('./components/Catalog/CategoriesView'), 'CategoriesView');
const ProductDetail = lazyNamed(() => import('./components/Product/ProductDetail'), 'ProductDetail');
const CartView = lazyNamed(() => import('./components/Cart/CartView'), 'CartView');
const CheckoutView = lazyNamed(() => import('./components/Checkout/CheckoutView'), 'CheckoutView');
const ProfileView = lazyNamed(() => import('./components/Profile/ProfileView'), 'ProfileView');
const OrderDetailView = lazyNamed(() => import('./components/Order/OrderDetailView'), 'OrderDetailView');
const DropDetail = lazyNamed(() => import('./components/Drops/DropDetail'), 'DropDetail');
const AdminView = lazyNamed(() => import('./components/Admin/AdminView'), 'AdminView');

export const App = () => {
  // Navigation & View Routing from current URL
  const initialRoute = parseRoute();
  const [currentView, setCurrentView] = useState(initialRoute.view);
  const isDeveloperView = currentView === 'dev';

  const [selectedProductSlug, setSelectedProductSlug] = useState(initialRoute.productSlug || null);
  const [selectedOrderId, setSelectedOrderId] = useState(initialRoute.orderId || null);
  const [selectedDropIdentifier, setSelectedDropIdentifier] = useState(initialRoute.dropIdentifier || null);
  const [selectedDropInfo, setSelectedDropInfo] = useState(null);
  const [profileTab, setProfileTab] = useState(initialRoute.profileTab || 'profile');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // Sync browser back/forward buttons (popstate) with state
  useEffect(() => {
    const handlePopState = () => {
      const route = parseRoute(window.location.pathname);
      setCurrentView(route.view);
      setSelectedProductSlug(route.productSlug || null);
      setSelectedDropIdentifier(route.dropIdentifier || null);
      setSelectedOrderId(route.orderId || null);
      if (route.profileTab) {
        setProfileTab(route.profileTab);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Sync state changes with browser URL and history
  useEffect(() => {
    const targetUrl = formatRouteUrl({
      view: currentView,
      productSlug: selectedProductSlug,
      dropIdentifier: selectedDropIdentifier,
      orderId: selectedOrderId,
      profileTab,
    });

    if (window.location.pathname !== targetUrl) {
      window.history.pushState({}, '', targetUrl);
    }
  }, [currentView, selectedProductSlug, selectedDropIdentifier, selectedOrderId, profileTab]);

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
    if (isDeveloperView) return undefined;
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
  }, [isDeveloperView]);

  // Fetch Catalog Products
  const fetchCatalogPage = useCallback(async ({ limit, offset, signal }) => {
    const params = new URLSearchParams();
    params.set('limit', limit);
    params.set('offset', offset);
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

    return apiJson('/api/v1/products?' + params.toString(), { signal });
  }, [activeCategoryId, activeBrandId, activeSize, activePriceFrom, activePriceTo, activeSort, activeSearch]);

  const {
    items: productsList,
    loading: loadingCatalog,
    loadingMore,
    error: errorCatalog,
    hasMore: catalogHasMore,
    reload: reloadCatalog,
    loadMore: handleLoadMore
  } = usePaginatedResource({ fetchPage: fetchCatalogPage, pageSize: CATALOG_LIMIT });

  const catalogEnabled = !isDeveloperView;
  useEffect(() => {
    if (catalogEnabled) reloadCatalog();
  }, [catalogEnabled, activeCategoryId, activeBrandId, activeSize, activePriceFrom, activePriceTo, activeSort, activeSearch, reloadCatalog]);

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
    setSelectedProductSlug(null);
    setSelectedDropIdentifier(null);
    setSelectedOrderId(null);
    setSelectedDropInfo(null);
    setCurrentView('catalog');
    setActiveCategoryId(null);
    setActiveBrandId(null);
    setActiveSize(null);
    setActivePriceFrom('');
    setActivePriceTo('');
    setActiveSort('created_at');
    setActiveSearch('');
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
      <main className="flex-1 flex flex-col">
        <Suspense fallback={<div className="spinner" aria-label="Загрузка страницы" />}>
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
              error={productsList.length === 0 ? errorCatalog?.message : null}
              loadMoreError={productsList.length > 0 ? errorCatalog : null}
              onRetry={reloadCatalog}
              onOpenProduct={(slug) => handleOpenProduct(slug, null)}
              hasMore={catalogHasMore}
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

        {currentView === 'architecture' && (
          <ArchitectureView
            onBack={() => setCurrentView('catalog')}
          />
        )}
        </Suspense>
      </main>

      <Toast />
    </div>
  );
};
