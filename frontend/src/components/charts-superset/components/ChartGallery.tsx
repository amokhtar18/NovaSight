import { useMemo, useState } from 'react';
import { Search, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ChartCategory } from '../types/Base';
import { getChartMetadataRegistry } from '../registries';
import type { ChartMetadata } from '../models/ChartMetadata';

export interface ChartGalleryProps {
  /** Currently selected viz_type key (e.g. VizType.Bar). */
  value?: string;
  /** Fired when the user picks a chart. */
  onChange?: (vizType: string, metadata: ChartMetadata) => void;
  /** Hide deprecated plugins from the gallery. Defaults to true. */
  hideDeprecated?: boolean;
  className?: string;
}

interface CatalogItem {
  key: string;
  metadata: ChartMetadata;
}

const CATEGORY_ORDER: string[] = [
  ChartCategory.KPI,
  ChartCategory.Trend,
  ChartCategory.Evolution,
  ChartCategory.Ranking,
  ChartCategory.Part,
  ChartCategory.Correlation,
  ChartCategory.Distribution,
  ChartCategory.Flow,
  ChartCategory.Map,
  ChartCategory.Table,
  ChartCategory.Other,
];

/**
 * Visual chart-type picker. Faithful in spirit to Superset's
 * `ChartTypeGallery`: groups every registered plugin by category, supports
 * free-text search across name / tags / description.
 */
export function ChartGallery({
  value,
  onChange,
  hideDeprecated = true,
  className,
}: ChartGalleryProps) {
  const [query, setQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState<string | 'All'>('All');

  const all = useMemo<CatalogItem[]>(
    () =>
      getChartMetadataRegistry()
        .entries()
        .map(([key, metadata]) => ({ key, metadata }))
        .filter(({ metadata }) => !hideDeprecated || !metadata.deprecated),
    [hideDeprecated],
  );

  const categoriesPresent = useMemo<string[]>(() => {
    const set = new Set<string>();
    for (const { metadata } of all) {
      if (metadata.category) set.add(metadata.category);
    }
    const ordered = CATEGORY_ORDER.filter((c) => set.has(c));
    const remainder = Array.from(set).filter((c) => !CATEGORY_ORDER.includes(c));
    return [...ordered, ...remainder.sort()];
  }, [all]);

  const filtered = useMemo<CatalogItem[]>(() => {
    const q = query.trim().toLowerCase();
    return all.filter(({ metadata, key }) => {
      if (activeCategory !== 'All' && metadata.category !== activeCategory)
        return false;
      if (!q) return true;
      const haystack = [
        metadata.name,
        metadata.description,
        metadata.category ?? '',
        key,
        ...metadata.tags,
      ]
        .join(' ')
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [all, query, activeCategory]);

  const grouped = useMemo<Array<[string, CatalogItem[]]>>(() => {
    const buckets = new Map<string, CatalogItem[]>();
    for (const item of filtered) {
      const cat = item.metadata.category ?? 'Other';
      if (!buckets.has(cat)) buckets.set(cat, []);
      buckets.get(cat)!.push(item);
    }
    for (const list of buckets.values()) {
      list.sort((a, b) => a.metadata.name.localeCompare(b.metadata.name));
    }
    const ordered = CATEGORY_ORDER.filter((c) => buckets.has(c)).map(
      (c): [string, CatalogItem[]] => [c, buckets.get(c)!],
    );
    const remainder = Array.from(buckets.keys())
      .filter((c) => !CATEGORY_ORDER.includes(c))
      .sort()
      .map((c): [string, CatalogItem[]] => [c, buckets.get(c)!]);
    return [...ordered, ...remainder];
  }, [filtered]);

  return (
    <div className={cn('flex h-full flex-col gap-4', className)}>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search charts (name, tag, description, viz_type)…"
            className="w-full rounded-md border border-input bg-background py-2 pl-9 pr-3 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
          />
        </div>
        <div className="text-xs text-muted-foreground">
          {filtered.length} of {all.length}
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        <CategoryPill
          label="All"
          active={activeCategory === 'All'}
          onClick={() => setActiveCategory('All')}
        />
        {categoriesPresent.map((cat) => (
          <CategoryPill
            key={cat}
            label={cat}
            active={activeCategory === cat}
            onClick={() => setActiveCategory(cat)}
          />
        ))}
      </div>

      <div className="flex-1 overflow-y-auto pr-1">
        {grouped.length === 0 && (
          <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
            No charts match “{query}”.
          </div>
        )}
        {grouped.map(([category, items]) => (
          <section key={category} className="mb-6">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {category}
            </h3>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
              {items.map(({ key, metadata }) => (
                <ChartCard
                  key={key}
                  vizType={key}
                  metadata={metadata}
                  selected={value === key}
                  onClick={() => onChange?.(key, metadata)}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function CategoryPill({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-full border px-3 py-1 text-xs transition-colors',
        active
          ? 'border-primary bg-primary text-primary-foreground'
          : 'border-input bg-background hover:bg-accent hover:text-accent-foreground',
      )}
    >
      {label}
    </button>
  );
}

function ChartCard({
  vizType,
  metadata,
  selected,
  onClick,
}: {
  vizType: string;
  metadata: ChartMetadata;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={metadata.description || metadata.name}
      className={cn(
        'group relative flex flex-col items-start gap-2 rounded-lg border bg-card p-3 text-left transition-all',
        'hover:-translate-y-0.5 hover:border-primary/60 hover:shadow-md',
        selected && 'border-primary ring-2 ring-primary/30',
      )}
    >
      {selected && (
        <CheckCircle2
          className="absolute right-2 top-2 h-4 w-4 text-primary"
          aria-hidden
        />
      )}
      <div className="flex h-20 w-full items-center justify-center rounded-md bg-gradient-to-br from-muted/40 to-muted/10">
        <span className="text-2xl font-semibold text-muted-foreground/40">
          {metadata.name.charAt(0)}
        </span>
      </div>
      <div className="w-full">
        <div className="truncate text-sm font-medium">{metadata.name}</div>
        <div className="truncate font-mono text-[10px] text-muted-foreground">
          {vizType}
        </div>
      </div>
      {metadata.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {metadata.tags.slice(0, 2).map((tag) => (
            <span
              key={tag}
              className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </button>
  );
}

export default ChartGallery;
