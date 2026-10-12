"""Skeleton partials — one per page. Served as HTML fragments via /api/skeleton/{page}.

Each skeleton uses the same DOM structure (with matching IDs) as the final rendered
page so JS can populate them in place without re-parsing.

ponytail: skeletons are static HTML strings generated at import. If a page layout
changes, update the corresponding function AND make sure the matching IDs match
what the page's JS expects to populate.
"""


def _repeat(html: str, count: int) -> str:
    return "".join(html for _ in range(count))


# ── About ──
ABOUT = (
    # Profile as fastfetch terminal panel
    '<div class="term mb-10">'
    '<div class="term-bar"><span class="term-dot red"></span><span class="term-dot yellow"></span><span class="term-dot green"></span><span class="term-title"></span></div>'
    '<div class="term-body" style="min-height:16rem">'
    '<div class="ff-panel">'
    '<div class="ff-logo bg-slate-700 animate-pulse"></div>'
    '<div class="ff-info">'
    '<div class="h-5 w-44 bg-slate-700 rounded mb-2 animate-pulse"></div>'
    '<div class="h-3 w-64 bg-slate-700 rounded mb-2 animate-pulse"></div>'
    '<div class="h-3 w-52 bg-slate-700 rounded mb-2 animate-pulse"></div>'
    '<div class="h-3 w-60 bg-slate-700 rounded mb-2 animate-pulse"></div>'
    '<div class="h-3 w-48 bg-slate-700 rounded mb-2 animate-pulse"></div>'
    '<div class="h-3 w-56 bg-slate-700 rounded animate-pulse"></div>'
    '</div></div></div></div>'

    # Contributions section
    '<div id="contrib-section" class="mb-10 animate-pulse" style="display:none">'
    '<div class="h-5 w-48 bg-slate-700 rounded mb-3"></div>'
    '<div class="bg-slate-800/40 rounded-xl border border-slate-700/50 p-4 sm:p-5 overflow-x-auto">'
    '<div class="contrib-graph" id="contrib-graph"></div>'
    '<div class="flex items-center justify-end gap-2 mt-3 text-xs text-slate-500">'
    '<span>Less</span>'
    '<span class="contrib-legend contrib-level-0"></span>'
    '<span class="contrib-legend contrib-level-1"></span>'
    '<span class="contrib-legend contrib-level-2"></span>'
    '<span class="contrib-legend contrib-level-3"></span>'
    '<span class="contrib-legend contrib-level-4"></span>'
    '<span>More</span>'
    '</div></div></div>'

    # GitHub repos
    '<div id="github-projects"></div>'
)

# ── Homepage ──
HOMEPAGE = (
    '<div class="mb-10 bg-slate-800/50 rounded-xl border border-slate-700 p-6 sm:p-8 animate-pulse">'
    '<div class="flex items-center gap-4 mb-4">'
    '<div class="w-10 h-10 bg-slate-700 rounded-lg"></div>'
    '<div class="h-8 w-64 bg-slate-700 rounded"></div></div>'
    '<div class="space-y-2">'
    '<div class="h-4 w-full bg-slate-700 rounded"></div>'
    '<div class="h-4 w-3/4 bg-slate-700 rounded"></div></div></div>'

    '<div class="bg-slate-800/40 rounded-xl border border-slate-700/50 p-5 animate-pulse mb-8">'
    '<div class="flex items-center justify-between">'
    '<div class="space-y-2">'
    '<div class="h-5 w-40 bg-slate-700 rounded"></div>'
    '<div class="h-3 w-56 bg-slate-700 rounded"></div></div>'
    '<div class="h-8 w-16 bg-slate-700 rounded"></div></div></div>'

    '<div class="grid gap-4 sm:gap-5 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 mb-8">'
    + _repeat(
        '<div class="bg-slate-800/40 rounded-xl border border-slate-700/50 p-5 animate-pulse">'
        '<div class="w-8 h-8 bg-slate-700 rounded mb-3"></div>'
        '<div class="h-5 w-24 bg-slate-700 rounded mb-2"></div>'
        '<div class="h-3 w-full bg-slate-700 rounded"></div></div>', 3) +
    '</div>'
)

# ── Notes ──
NOTES = (
    '<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-5 animate-pulse">'
    '<div class="flex items-center gap-2">'
    '<div class="w-6 h-6 bg-slate-700 rounded"></div>'
    '<div class="h-7 w-16 bg-slate-700 rounded"></div>'
    '</div>'
    '<div class="w-full sm:w-64 h-10 bg-slate-700 rounded-lg"></div>'
    '</div>'

    # Filter bar
    '<div class="flex items-center gap-3 mb-5 animate-pulse">'
    '<div class="w-32 h-10 bg-slate-700 rounded-lg"></div>'
    '<div class="ml-auto flex gap-1">'
    '<div class="w-20 h-9 bg-slate-700 rounded-lg"></div>'
    '<div class="w-16 h-9 bg-slate-700 rounded-lg"></div>'
    '</div></div>'

    '<div class="grid gap-4 grid-cols-1 sm:grid-cols-2">'
    + _repeat(
        '<div class="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5 animate-pulse flex flex-col">'
        '<div class="flex-1">'
        '<div class="h-5 w-40 bg-slate-700 rounded mb-3"></div>'
        '<div class="h-4 w-full bg-slate-700 rounded mb-1.5"></div>'
        '<div class="h-4 w-2/3 bg-slate-700 rounded mb-3"></div>'
        '</div>'
        '<div class="flex items-end justify-between mt-3">'
        '<div class="flex gap-1.5">'
        '<div class="w-12 h-5 bg-slate-700 rounded"></div>'
        '<div class="w-16 h-5 bg-slate-700 rounded"></div>'
        '</div>'
        '<div class="w-32 h-3 bg-slate-700 rounded"></div>'
        '</div></div>',
        4) +
    '</div>'
)

# ── Reviews ──
REVIEWS = (
    '<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-5 animate-pulse">'
    '<div class="flex items-center gap-2">'
    '<div class="w-6 h-6 bg-slate-700 rounded"></div>'
    '<div class="h-9 w-24 bg-slate-700 rounded"></div>'
    '</div>'
    '<div class="w-full sm:w-64 h-10 bg-slate-700 rounded-lg"></div>'
    '</div>'

    # Filter bar: category dropdown + sort
    '<div class="flex items-center gap-3 mb-5 animate-pulse">'
    '<div class="w-32 h-10 bg-slate-700 rounded-lg"></div>'
    '<div class="ml-auto flex gap-2">'
    '<div class="w-20 h-9 bg-slate-700 rounded-lg"></div>'
    '<div class="w-20 h-9 bg-slate-700 rounded-lg"></div>'
    '</div></div>'

    '<div class="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">'
    + _repeat(
        '<div class="bg-slate-800 rounded-xl border border-slate-700 p-4 animate-pulse">'
        '<div class="flex items-start gap-3">'
        '<div class="w-16 h-22 sm:w-20 sm:h-28 bg-slate-700 rounded-lg shrink-0"></div>'
        '<div class="min-w-0 flex-1">'
        '<div class="h-5 w-32 bg-slate-700 rounded mb-2"></div>'
        '<div class="h-4 w-24 bg-slate-700 rounded mb-2"></div>'
        '<div class="h-4 w-20 bg-slate-700 rounded mb-1.5"></div>'
        '<div class="h-3 w-16 bg-slate-700 rounded"></div>'
        '</div></div></div>',
        6) +
    '</div>'
)


SKELETONS = {
    "": HOMEPAGE,
    "about": ABOUT,
    "notes": NOTES,
    "reviews": REVIEWS,
    "note": NOTES,  # single note page shares notes skeleton
}