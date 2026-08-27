// IBD Patient Timeline Viewer — client-side rendering logic
// Data (ALL_EVENTS, FLARES) is injected by Python into window before this script runs.

var FIXED = [
    'imaging',
    'prescription',
    'physician_claim',
    'lab_test',
    'ambulatory_visit',
    'hospital_admission'
];

var LABELS = {
    'imaging':            'Diagnostic Imaging',
    'prescription':       'Prescription',
    'physician_claim':    'Physician Claim',
    'lab_test':           'Lab Test',
    'ambulatory_visit':   'Ambulatory Visit',
    'hospital_admission': 'Hospitalization'
};

var COLORS = {
    'imaging':            '#636EFA',
    'prescription':       '#EF553B',
    'physician_claim':    '#AB63FA',
    'lab_test':           '#19D3F3',
    'ambulatory_visit':   '#00CC96',
    'hospital_admission': '#FFA15A'
};

function filterEvents(filter) {
    if (filter === 'ibd')     return ALL_EVENTS.filter(function(e){ return  e.ibd_related; });
    if (filter === 'non_ibd') return ALL_EVENTS.filter(function(e){ return !e.ibd_related; });
    return ALL_EVENTS;
}

function buildHoverText(e) {
    var label = LABELS[e.event_type] || e.event_type || '';
    var t = (label ? '<b>event_type:</b> ' + label + '<br>' : '') +
            '<b>start:</b> ' + e.start_date.split('T')[0] +
            '<br><b>end:</b> ' + e.end_date.split('T')[0] + '<br>';
    try {
        var info = typeof e.event_info === 'string' ? JSON.parse(e.event_info) : e.event_info;
        Object.keys(info).forEach(function(k) {
            if (k === 'dummy') return;
            var v = String(info[k]);
            if (v.length > 40) {
                var chunks = [];
                for (var i = 0; i < v.length; i += 40) chunks.push(v.slice(i, i + 40));
                t += '<b>' + k + ':</b><br>' + chunks.join('<br>') + '<br>';
            } else {
                t += '<b>' + k + ':</b> ' + v + '<br>';
            }
        });
    } catch (err) {
        // Plain string event_info (e.g. "At: Hospital | Dx: ... | CMG: ...")
        var raw = e.event_info ? String(e.event_info).trim() : '';
        if (raw) {
            raw.split(' | ').forEach(function(part) {
                var ci = part.indexOf(': ');
                if (ci > 0) {
                    t += '<b>' + part.slice(0, ci) + ':</b> ' + part.slice(ci + 2) + '<br>';
                } else if (part) {
                    t += part + '<br>';
                }
            });
        }
    }
    if (e.source_dataset) t += '<b>source_dataset:</b> ' + e.source_dataset + '<br>';
    t += '<b>ibd_related:</b> ' + e.ibd_related;
    return t;
}

function processEvents(events) {
    var result = events.map(function(e) { return Object.assign({}, e); });

    result.forEach(function(e) {
        e._s = new Date(e.start_date).getTime();
        e._e = new Date(e.end_date).getTime();
        if (e._s === e._e) e._e += 86400000;
    });

    // Stagger same-day lab tests by 2 hours each so they don't overlap
    var labByDate = {};
    result.filter(function(e) { return e.event_type === 'lab_test'; })
          .forEach(function(e) {
              var k = e.start_date.split('T')[0];
              if (!labByDate[k]) labByDate[k] = [];
              labByDate[k].push(e);
          });
    Object.keys(labByDate).forEach(function(k) {
        var grp = labByDate[k];
        if (grp.length > 1) grp.forEach(function(e, i) {
            var offset = i * 7200000;
            e._s += offset;
            e._e += offset;
        });
    });

    return result;
}

// Move Plotly's modebar into the filter bar so it sits on the same row
function relocateModebar() {
    setTimeout(function() {
        var modebar   = document.querySelector('.js-plotly-plot .modebar-container');
        var filterBar = document.getElementById('filter-bar');
        if (modebar && filterBar && modebar.parentElement !== filterBar) {
            filterBar.appendChild(modebar);
        }
    }, 80);
}

var _chartReady = false;
var _relayoutBound = false;
var _clampingZoom = false;
var MAX_VIEW_WIDTH = null;
var DEFAULT_MIN = null, DEFAULT_MAX = null;
var _currentFilter = 'all';

// The chart lives inside an iframe (srcdoc, same-origin as the parent app),
// so it can read the parent's dark/light choice straight off <html data-theme>
// instead of needing its own separate toggle or a postMessage round trip.
function themeColors() {
    var dark = false;
    try { dark = window.parent.document.documentElement.getAttribute('data-theme') === 'dark'; } catch (e) {}
    return dark
        ? { bg: 'rgba(0,0,0,0)', font: '#dbe8e4', grid: 'rgba(219,232,228,.14)', line: 'rgba(219,232,228,.3)' }
        : { bg: '#ffffff', font: '#152826', grid: '#eef3f1', line: '#d7e1de' };
}

// Zooming in is unrestricted, but zooming OUT (clicking "-", scrolling out,
// drag-zoom, Autoscale, Reset axes) can't go past the default view the chart
// first loaded with — past that the bars are too compressed to read, so
// snap back to the default instead of letting the view keep widening.
//
// The same clamp-and-track pattern is applied to the Y axis (event-type
// rows) further down, for the row-zoom +/- buttons.
function clampMaxZoom(eventData) {
    if (_clampingZoom || !eventData) return;

    var patch = {};
    var needsRelayout = false;

    if (eventData['xaxis.autorange'] === true && MAX_VIEW_WIDTH !== null) {
        // Autoscale/Reset axes resets via Plotly's own fit-to-ALL-data
        // autorange, which includes any stray outlier dates (e.g. a 1970
        // record) — centering a normal-width window on THAT range's
        // midpoint can land in decades of empty space with no bars in
        // sight at all, even though the DOM still has them. The default
        // view (tMin/tMax below) was already computed to exclude such
        // outliers via percentiles, so just snap straight back to it —
        // that's the one range guaranteed to actually show the data.
        patch['xaxis.range[0]'] = DEFAULT_MIN;
        patch['xaxis.range[1]'] = DEFAULT_MAX;
        CURRENT_X_MIN = DEFAULT_MIN; CURRENT_X_MAX = DEFAULT_MAX;
        needsRelayout = true;
    } else {
        var hasXMin = Object.prototype.hasOwnProperty.call(eventData, 'xaxis.range[0]');
        var hasXMax = Object.prototype.hasOwnProperty.call(eventData, 'xaxis.range[1]');
        if (hasXMin && hasXMax && MAX_VIEW_WIDTH !== null) {
            var xr0 = new Date(eventData['xaxis.range[0]']).getTime();
            var xr1 = new Date(eventData['xaxis.range[1]']).getTime();
            var xWidth = xr1 - xr0;
            if (xWidth > MAX_VIEW_WIDTH) {
                var xCenter = (xr0 + xr1) / 2;
                patch['xaxis.range[0]'] = xCenter - MAX_VIEW_WIDTH / 2;
                patch['xaxis.range[1]'] = xCenter + MAX_VIEW_WIDTH / 2;
                CURRENT_X_MIN = patch['xaxis.range[0]']; CURRENT_X_MAX = patch['xaxis.range[1]'];
                needsRelayout = true;
            } else {
                CURRENT_X_MIN = xr0; CURRENT_X_MAX = xr1;
            }
        }
    }

    if (eventData['yaxis.autorange'] === true) {
        patch['yaxis.range[0]'] = DEFAULT_Y_MIN;
        patch['yaxis.range[1]'] = DEFAULT_Y_MAX;
        CURRENT_Y_MIN = DEFAULT_Y_MIN; CURRENT_Y_MAX = DEFAULT_Y_MAX;
        needsRelayout = true;
    } else {
        var hasYMin = Object.prototype.hasOwnProperty.call(eventData, 'yaxis.range[0]');
        var hasYMax = Object.prototype.hasOwnProperty.call(eventData, 'yaxis.range[1]');
        if (hasYMin && hasYMax) {
            var yr0 = eventData['yaxis.range[0]'];
            var yr1 = eventData['yaxis.range[1]'];
            var yWidth = yr1 - yr0;
            var maxYWidth = DEFAULT_Y_MAX - DEFAULT_Y_MIN;
            if (yWidth > maxYWidth) {
                var yCenter = (yr0 + yr1) / 2;
                patch['yaxis.range[0]'] = yCenter - maxYWidth / 2;
                patch['yaxis.range[1]'] = yCenter + maxYWidth / 2;
                CURRENT_Y_MIN = patch['yaxis.range[0]']; CURRENT_Y_MAX = patch['yaxis.range[1]'];
                needsRelayout = true;
            } else {
                CURRENT_Y_MIN = yr0; CURRENT_Y_MAX = yr1;
            }
        }
    }

    if (needsRelayout) {
        _clampingZoom = true;
        Plotly.relayout('plot', patch).then(function() { _clampingZoom = false; });
    }
}

// Row (Y-axis) zoom — the six event-type rows sit on a plain numeric axis
// (see YPOS in renderChart) instead of Plotly's categorical axis, purely so
// "+"/"-" can zoom that axis's RANGE the same way native scroll/drag-zoom
// already works on the X (time) axis: shrinking/growing the visible range
// centered on wherever it currently sits, rather than changing each bar's
// own thickness inside a fixed-height row slot (the old approach, which
// left the container's total height unchanged and just made bars skinnier
// — visible as growing blank gaps around each row instead of an actual
// zoom). DEFAULT_Y_MIN/MAX is exactly the six rows with half-a-row margin
// top and bottom, so "zoomed all the way out" has no leftover blank space,
// and it's also the ceiling clampMaxZoom enforces above.
var DEFAULT_Y_MIN = null, DEFAULT_Y_MAX = null;
var CURRENT_Y_MIN = null, CURRENT_Y_MAX = null;
var CURRENT_X_MIN = null, CURRENT_X_MAX = null;
var MIN_Y_RANGE_WIDTH = 1.2;

function adjustYZoom(factor) {
    if (CURRENT_Y_MIN === null || CURRENT_Y_MAX === null) return;
    var center = (CURRENT_Y_MIN + CURRENT_Y_MAX) / 2;
    var maxWidth = DEFAULT_Y_MAX - DEFAULT_Y_MIN;
    var width = Math.max(MIN_Y_RANGE_WIDTH, Math.min(maxWidth, (CURRENT_Y_MAX - CURRENT_Y_MIN) * factor));

    var newMin = center - width / 2;
    var newMax = center + width / 2;
    // Keep the window inside the data extent — slide it back in rather than
    // clipping asymmetrically if the center-preserving width change would
    // push either edge past the default bounds.
    if (newMin < DEFAULT_Y_MIN) { newMax += (DEFAULT_Y_MIN - newMin); newMin = DEFAULT_Y_MIN; }
    if (newMax > DEFAULT_Y_MAX) { newMin -= (newMax - DEFAULT_Y_MAX); newMax = DEFAULT_Y_MAX; }
    newMin = Math.max(DEFAULT_Y_MIN, newMin);
    newMax = Math.min(DEFAULT_Y_MAX, newMax);

    CURRENT_Y_MIN = newMin;
    CURRENT_Y_MAX = newMax;
    Plotly.relayout('plot', { 'yaxis.range[0]': newMin, 'yaxis.range[1]': newMax });
}

// Numeric position for each category. Plotly's own categorical axis (the
// old approach) placed FIXED[0] at the BOTTOM and FIXED[last] at the TOP —
// matched here directly (YPOS = array index) rather than reversed, so a
// plain numeric axis reproduces the exact same row order. Needed as numeric
// (not categorical) purely so the row-zoom +/- buttons and native drag/
// scroll-zoom on Y have an actual range to operate on.
var YPOS = {};
FIXED.forEach(function(et, i) { YPOS[et] = i; });

function renderChart(filter) {
    var events = processEvents(filterEvents(filter));
    var ref    = ALL_EVENTS.length ? new Date(ALL_EVENTS[0].start_date).getTime() : Date.now();

    var traces = FIXED.map(function(et) {
        var te    = events.filter(function(e) { return e.event_type === et; });
        var dummy = te.length === 0;
        var ypos  = YPOS[et];
        return {
            type:          'bar',
            orientation:   'h',
            name:          LABELS[et] || et,
            x:             dummy ? [0]   : te.map(function(e) { return e._e - e._s; }),
            base:          dummy ? [ref] : te.map(function(e) { return e._s; }),
            y:             dummy ? [ypos] : te.map(function() { return ypos; }),
            customdata:    dummy ? ['']  : te.map(function(e) { return buildHoverText(e); }),
            hovertemplate: dummy ? '<extra></extra>' : '%{customdata}<extra></extra>',
            textposition:  'none',
            marker:        { color: COLORS[et] || '#888', opacity: dummy ? 0 : 1 },
            width:         dummy ? 0 : 0.8,
            showlegend:    false
        };
    });

    var shapes = FLARES.map(function(f) {
        return {
            type: 'rect', xref: 'x', yref: 'paper',
            x0: f.start_date, x1: f.end_date,
            y0: 0, y1: 1,
            fillcolor: 'red', opacity: 0.3,
            layer: 'below', line: { width: 0 }
        };
    });

    var sMs  = ALL_EVENTS.map(function(e) { return new Date(e.start_date).getTime(); });
    var eMs  = ALL_EVENTS.map(function(e) { return new Date(e.end_date).getTime(); });

    // Default view should focus on where the real data lives — a single stray
    // outlier date (e.g. a 1970 record) shouldn't stretch the whole axis and
    // squeeze everything else into a sliver. Use the 2nd/98th percentile for
    // the initial range. This also becomes the zoom-out ceiling below.
    function percentileMs(arr, p) {
        var s = arr.slice().sort(function(a, b) { return a - b; });
        var idx = (s.length - 1) * p;
        var lo = Math.floor(idx), hi = Math.ceil(idx);
        return lo === hi ? s[lo] : s[lo] + (s[hi] - s[lo]) * (idx - lo);
    }
    var allMs = sMs.concat(eMs);
    var tMin = allMs.length ? percentileMs(allMs, 0.02) - 864000000 : ref - 864000000;
    var tMax = allMs.length ? percentileMs(allMs, 0.98) + 864000000 : ref + 864000000;

    // Zooming out can't go past the default view width — beyond this the
    // bars are too compressed to read. Zooming in stays unrestricted.
    MAX_VIEW_WIDTH = tMax - tMin;
    DEFAULT_MIN = tMin;
    DEFAULT_MAX = tMax;
    // Preserve whatever the user already had zoomed in to (drag/scroll or
    // the +/- buttons) across re-renders (filter switch, theme toggle) —
    // only fall back to the full default range the very first time.
    if (CURRENT_X_MIN === null || CURRENT_X_MAX === null) {
        CURRENT_X_MIN = tMin; CURRENT_X_MAX = tMax;
    }

    // Six rows plus half a row of margin above/below — the widest the Y
    // range is ever allowed to be, so "fully zoomed out" always shows
    // exactly the six rows with no leftover blank space.
    DEFAULT_Y_MIN = -0.5;
    DEFAULT_Y_MAX = FIXED.length - 0.5;
    if (CURRENT_Y_MIN === null || CURRENT_Y_MAX === null) {
        CURRENT_Y_MIN = DEFAULT_Y_MIN; CURRENT_Y_MAX = DEFAULT_Y_MAX;
    }

    var theme = themeColors();
    var layout = {
        xaxis: { type: 'date', title: 'Time', range: [CURRENT_X_MIN, CURRENT_X_MAX],
                 gridcolor: theme.grid, linecolor: theme.line, zerolinecolor: theme.line,
                 tickfont: { color: theme.font }, titlefont: { color: theme.font } },
        yaxis: {
            // standoff + automargin push the title clear of the tick labels
            // instead of the two crowding together — without automargin, a
            // fixed left margin (see config.margin.l below) isn't wide
            // enough for the longer labels ("Physician Claim") to leave the
            // title any breathing room, so it ends up wedged between words.
            title:      { text: 'Event Type', standoff: 24, font: { color: theme.font } },
            automargin: true,
            range:      [CURRENT_Y_MIN, CURRENT_Y_MAX],
            tickmode:   'array',
            tickvals:   FIXED.map(function(et) { return YPOS[et]; }),
            ticktext:   FIXED.map(function(et) { return LABELS[et] || et; }),
            gridcolor: theme.grid, linecolor: theme.line, zerolinecolor: theme.line,
            tickfont: { color: theme.font }
        },
        barmode:       'overlay',
        showlegend:    false,
        autosize:      true,
        margin:        { l: 120, r: 20, t: 16, b: 40 },
        shapes:        shapes,
        hovermode:     'closest',
        bargap:        0.1,
        bargroupgap:   0.0,
        font:          { color: theme.font },
        plot_bgcolor:  theme.bg,
        paper_bgcolor: theme.bg
    };

    var config = {
        responsive:             true,
        displayModeBar:         true,
        // Built-in zoomIn2d/zoomOut2d zoom the TIME (x) axis, which drag/
        // scroll already covers — replaced with custom +/- buttons that
        // zoom the Y (event-type row) axis instead, centered on wherever
        // the chart is currently focused.
        modeBarButtonsToRemove: ['select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d'],
        modeBarButtonsToAdd: [
            {
                name: 'Zoom in on rows',
                icon: Plotly.Icons.zoom_plus,
                click: function() { adjustYZoom(0.7); }
            },
            {
                name: 'Zoom out on rows',
                icon: Plotly.Icons.zoom_minus,
                click: function() { adjustYZoom(1 / 0.7); }
            }
        ]
    };

    if (!_chartReady) {
        Plotly.newPlot('plot', traces, layout, config);
        _chartReady = true;
        relocateModebar();
    } else {
        Plotly.react('plot', traces, layout, config);
    }

    if (!_relayoutBound) {
        document.getElementById('plot').on('plotly_relayout', clampMaxZoom);
        _relayoutBound = true;
    }
}

// Filter button handler — called by onclick in the HTML
window.setF = function(filter) {
    document.querySelectorAll('.fbtn').forEach(function(b) { b.className = 'fbtn off'; });
    var idx = { all: 0, ibd: 1, non_ibd: 2 };
    document.querySelectorAll('.fbtn')[idx[filter]].className = 'fbtn on';
    _currentFilter = filter;
    renderChart(filter);
};

// Called by the parent page right after it flips light/dark, so the chart's
// own colours (which Plotly bakes into the SVG rather than styling via CSS)
// re-render to match instead of staying stuck in the old theme.
window.ptvApplyTheme = function() {
    if (_chartReady) renderChart(_currentFilter);
};

// Load Plotly from the CDN script already in <head> — NEVER borrow
// window.parent.Plotly. Once Labelling Mode's gr.Plot() component has run,
// window.parent.Plotly exists but is internally bound to the PARENT page's
// document, not this iframe's — using it makes Plotly.newPlot('plot', ...)
// fail with "No DOM element with id 'plot' exists on the page" even though
// #plot is right here, because Plotly's own internals resolve against the
// wrong document. Every render must use a Plotly instance loaded inside
// THIS document.
function initPlotly() {
    if (typeof Plotly !== 'undefined') {
        renderChart('all');
        return;
    }

    // CDN in <head> may still be loading — poll for up to 10 s
    var attempts = 0;
    var iv = setInterval(function() {
        if (typeof Plotly !== 'undefined') {
            clearInterval(iv);
            renderChart('all');
        } else if (++attempts > 100) {
            clearInterval(iv);
            document.getElementById('plot').innerHTML =
                '<p style="color:#ef4444;padding:20px;">Could not load chart library ' +
                '(no internet access). Contact your administrator.</p>';
        }
    }, 100);
}

initPlotly();
