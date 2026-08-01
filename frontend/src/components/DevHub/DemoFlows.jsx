import React, { useMemo } from 'react';

const RECIPES = [
  { title: 'Browse a live drop', serviceIds: ['drops', 'catalog', 'inventory'], access: 'Public discovery flow' },
  { title: 'Manage a wishlist', serviceIds: ['auth', 'wishlist'], access: 'Signed-in customer flow' },
  { title: 'Reserve and purchase', serviceIds: ['inventory', 'orders', 'payments'], access: 'Transactional flow' },
];

export const DemoFlows = ({ endpoints, onSelectEndpoint }) => {
  const recipes = useMemo(() => RECIPES.map((recipe) => ({
    ...recipe,
    steps: recipe.serviceIds.map((serviceId) => endpoints.find((endpoint) => endpoint.serviceId === serviceId && (endpoint.method === 'GET' || endpoint.method === 'POST'))).filter(Boolean),
  })).filter((recipe) => recipe.steps.length > 0), [endpoints]);
  return (
    <section className="border-b border-zinc-800 bg-[#0B0B0C] py-16">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-10"><div className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-[#BFF532]">Contract recipes</div><h2 className="mt-2 text-3xl font-black uppercase text-white sm:text-4xl">Follow the business flow.</h2><p className="mt-3 max-w-2xl text-sm text-zinc-500">Each step links to an operation present in the generated contract. Recipes do not execute or invent business data.</p></div>
        <div className="grid gap-px border border-zinc-800 bg-zinc-800 lg:grid-cols-3">
          {recipes.map((recipe, recipeIndex) => (
            <article key={recipe.title} className="bg-zinc-950 p-6">
              <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-600">Recipe {String(recipeIndex + 1).padStart(2, '0')} · {recipe.access}</div>
              <h3 className="mt-4 text-xl font-black uppercase text-white">{recipe.title}</h3>
              <ol className="mt-6 space-y-2">{recipe.steps.map((endpoint, index) => <li key={endpoint.id}><button onClick={() => onSelectEndpoint(endpoint)} className="grid w-full grid-cols-[22px_44px_1fr] items-center gap-2 border-t border-zinc-800 py-3 text-left font-mono text-[10px] hover:text-[#BFF532]"><span className="text-zinc-700">{index + 1}</span><span className="font-bold text-zinc-400">{endpoint.method}</span><span className="truncate text-zinc-300">{endpoint.path}</span></button></li>)}</ol>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};
