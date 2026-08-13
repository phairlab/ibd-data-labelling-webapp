# ============================================================================
# PATIENT TIMELINE VIEWER - MAIN APPLICATION INTERFACE
# ============================================================================
#
# This is the main entry point for the Patient Timeline Viewer application.
# It creates a Gradio web interface for doctors to view patient medical timelines
# and add/manage disease flare periods.
#
# The application supports:
# - Multiple patient access groups (command-line controlled)
# - Timeline visualization with event filtering
# - Monthly flare labelling system
# - Data export capabilities
#
# Usage: python main.py [group-a|group-b|group-c|custom|admin|dev] [options]
# ============================================================================

import gradio as gr
import argparse
import os
import sys
from patient_timeline_webapp import PatientTimelineApp
from monthly_labelling import add_monthly_labelling_methods
from timeline_visualization import create_main_timeline, create_monthly_timeline

# Global app instance - will be initialized with command line arguments
app = None

def parse_arguments():
    """
    Parse command line arguments to determine patient access permissions.

    This function sets up different patient groups to control which patients
    each user/team can access. This is useful for:
    - Research teams working on specific cohorts
    - Clinical teams with different responsibilities
    - Limiting access for security/privacy reasons

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description='Patient Timeline Viewer with Patient Group Access Control')

    # Create subcommands for different patient access groups
    subparsers = parser.add_subparsers(dest='command', help='Available patient groups')

    # GROUP A: Patients 1-100 (e.g., for Research Team A)
    group_a = subparsers.add_parser('group-a', help='Access patients 1-100')
    group_a.add_argument('--start', type=int, default=1, help='Start patient ID (default: 1)')
    group_a.add_argument('--end', type=int, default=100, help='End patient ID (default: 100)')
    group_a.add_argument('--rmt23345-dir', type=str, default=None, dest='rmt23345_dir',
                         help='Directory containing cleaned RMT23345_*.csv files')

    # GROUP B: Patients 101-200 (e.g., for Research Team B)
    group_b = subparsers.add_parser('group-b', help='Access patients 101-200')
    group_b.add_argument('--start', type=int, default=101, help='Start patient ID (default: 101)')
    group_b.add_argument('--end', type=int, default=200, help='End patient ID (default: 200)')
    group_b.add_argument('--rmt23345-dir', type=str, default=None, dest='rmt23345_dir',
                         help='Directory containing cleaned RMT23345_*.csv files')

    # GROUP C: Patients 201-300 (e.g., for Clinical Team)
    group_c = subparsers.add_parser('group-c', help='Access patients 201-300')
    group_c.add_argument('--start', type=int, default=201, help='Start patient ID (default: 201)')
    group_c.add_argument('--end', type=int, default=300, help='End patient ID (default: 300)')
    group_c.add_argument('--rmt23345-dir', type=str, default=None, dest='rmt23345_dir',
                         help='Directory containing cleaned RMT23345_*.csv files')

    # CUSTOM RANGE: For specific research projects or temporary access
    custom = subparsers.add_parser('custom', help='Access custom patient range')
    custom.add_argument('--start', type=int, required=True, help='Start patient ID')
    custom.add_argument('--end', type=int, required=True, help='End patient ID')
    custom.add_argument('--name', type=str, default='Custom', help='Group name for display')
    custom.add_argument('--rmt23345-dir', type=str, default=None, dest='rmt23345_dir',
                        help='Directory containing cleaned RMT23345_*.csv files')

    # ADMIN ACCESS: All patients (for administrators/supervisors)
    admin = subparsers.add_parser('admin', help='Access all patients (admin mode)')
    admin.add_argument('--rmt23345-dir', type=str, default=None, dest='rmt23345_dir',
                       help='Directory containing cleaned RMT23345_*.csv files')

    return parser.parse_args()

def create_app_with_args():
    """
    Create PatientTimelineApp instance based on command line arguments.

    This function interprets the parsed command line arguments and creates
    the appropriate app instance with the correct patient access permissions.

    Returns:
        PatientTimelineApp: Configured app instance
    """
    args = parse_arguments()

    # Create app instance based on which command was used
    if args.command == 'group-a':
        pr = None if args.rmt23345_dir else (args.start, args.end)
        return PatientTimelineApp(patient_range=pr, group_name="Group A",
                                  rmt23345_data_dir=args.rmt23345_dir)
    elif args.command == 'group-b':
        pr = None if args.rmt23345_dir else (args.start, args.end)
        return PatientTimelineApp(patient_range=pr, group_name="Group B",
                                  rmt23345_data_dir=args.rmt23345_dir)
    elif args.command == 'group-c':
        pr = None if args.rmt23345_dir else (args.start, args.end)
        return PatientTimelineApp(patient_range=pr, group_name="Group C",
                                  rmt23345_data_dir=args.rmt23345_dir)
    elif args.command == 'custom':
        pr = None if args.rmt23345_dir else (args.start, args.end)
        return PatientTimelineApp(patient_range=pr, group_name=args.name,
                                  rmt23345_data_dir=args.rmt23345_dir)
    elif args.command == 'admin':
        return PatientTimelineApp(patient_range=None, group_name="Admin (All Patients)",
                                  rmt23345_data_dir=args.rmt23345_dir)
    else:
        # No valid command provided - show help and exit
        print("No command specified. Available commands:")
        print("  python main.py group-a    # Access patients 1-100")
        print("  python main.py group-b    # Access patients 101-200")
        print("  python main.py group-c    # Access patients 201-300")
        print("  python main.py custom --start 1 --end 50 --name 'My Group'")
        print("  python main.py admin      # Access all patients")
        sys.exit(1)


# ============================================================================
# NEW-UI PALETTE + LAYOUT
# Sidebar navigation + card-based pages, matching the approved mockups.
# Colours only where the mockup differs from real data are adapted — actual
# numbers below are always computed live from PatientTimelineApp, never
# fabricated.
# ============================================================================

NEW_UI_CSS = """
<style>
/* style-only HTML blocks must take zero space in the layout flow, otherwise
   they push content below them down while the fixed sidebar stays pinned
   at the true top — causing the page titles to sit lower than the brand. */
.style-inject{ display:block !important; padding:0 !important; margin:0 !important;
  min-height:0 !important; height:0 !important; border:none !important; overflow:hidden !important; }

/* ---- force a LIGHT theme no matter the OS/browser preference ---- */
:root, .dark { color-scheme: light !important; }
:root, gradio-app, .gradio-container, .dark, .dark .gradio-container{
  --body-background-fill:#eef4f1 !important;
  --background-fill-primary:#eef4f1 !important;
  --background-fill-secondary:#eef4f1 !important;
  --block-background-fill:transparent !important;
  --panel-background-fill:transparent !important;
  --input-background-fill:#ffffff !important;
  --border-color-primary:#dbe6e1 !important;
  --body-text-color:#152826 !important;
  --body-text-color-subdued:#5a6b67 !important;
  --block-title-text-color:#152826 !important;
  --block-label-text-color:#152826 !important;
  --button-primary-background-fill:#00726f !important;
  --button-primary-background-fill-hover:#00524f !important;
  --button-primary-text-color:#ffffff !important;
  --button-secondary-background-fill:#ffffff !important;
  --button-secondary-border-color:#c7d6d0 !important;
  --color-accent:#00726f !important;
  --color-accent-soft:#dcefec !important;
  --link-text-color:#00726f !important;
  --checkbox-background-color-selected:#00726f !important;
  --slider-color:#00726f !important;
}
.gradio-container, body, gradio-app, .dark body, .dark gradio-app{background:#eef4f1 !important;}
.gradio-container input, .gradio-container textarea, .gradio-container select{
  background:#ffffff !important; color:#152826 !important;
}
.gradio-container h1, .gradio-container h2, .gradio-container h3,
.gradio-container .prose, .gradio-container .prose *,
.gradio-container p, .gradio-container label, .gradio-container span{
  color:#152826 !important;
}
.gradio-container button.primary, .gradio-container button.primary *{ color:#ffffff !important; }

/* ---- page frame ---- */
.gradio-container{max-width:100% !important; padding:0 !important;}
/* Gradio wraps everything in <main class="fillable app"> capped at 1920px
   with margin:auto — invisible on screens <=1920px wide, but on wider
   monitors it centers the whole app and leaves dead space on both sides
   (masked on the left by the fixed sidebar, visible as a gap on the right). */
.gradio-container main.fillable, .gradio-container > main{
  max-width:100% !important; width:100% !important; margin:0 !important;
}

/* ---- fixed left sidebar (pine-teal, subtle depth gradient) ---- */
/* Gradio's built-in mobile breakpoint (max-width:640px) can reflow things
   unexpectedly — force our sidebar/page structure to hold regardless. */
@media (max-width:640px){
  #sidebar{position:fixed !important; display:flex !important; width:288px !important;}
  #page_overview, #page_timeline, #page_label, #page_guide{margin-left:288px !important;}
}
#sidebar{
  position:fixed !important; top:0; left:0; width:288px; height:100vh;
  background:linear-gradient(165deg,#2f5b55 0%,#254842 60%,#1f3d38 100%) !important;
  padding:14px 18px !important;
  gap:4px !important; overflow-y:auto; z-index:40; min-width:288px !important;
  border-right:1px solid #1c3733;
  box-shadow:2px 0 10px rgba(0,0,0,.08);
}
#sidebar, #sidebar *{ color:#dbe8e4 !important; }
#brand{display:flex; align-items:center; gap:10px; font-weight:700;
  font-size:18px; margin-bottom:6px; color:#ffffff !important;}
#brand .logo{width:30px; height:30px; border-radius:8px; background:#3f6f68;
  display:flex; align-items:center; justify-content:center; font-size:16px;}
#sidebar .nav-section, #sidebar .ctx-title{font-size:11px; letter-spacing:.09em;
  color:#9dbcb6 !important; font-weight:600; margin:16px 4px 6px; text-transform:uppercase;}
#sidebar button.nav-btn{
  justify-content:flex-start !important; text-align:left !important;
  background:transparent !important; border:none !important; box-shadow:none !important;
  color:#dbe8e4 !important; font-weight:500 !important; border-radius:10px !important;
  padding:10px 12px !important; margin:0 !important; min-height:0 !important; width:100%;
}
#sidebar button.nav-btn:hover{background:rgba(255,255,255,.09) !important;}
#sidebar button.nav-btn.primary{background:#ffffff !important; color:#152826 !important;
  font-weight:600 !important;}
#sidebar button.nav-btn.primary *{color:#152826 !important;}
#sidebar .ctx-card{margin-top:14px; background:rgba(255,255,255,.07);
  border-radius:12px; padding:14px;}
#sidebar .ctx-main{color:#ffffff !important; font-weight:600; margin-top:4px;}
#sidebar .ctx-sub{color:#b9d0cb !important; font-size:12px; margin-top:2px;}
#sidebar .legend-row{display:flex; align-items:center; gap:8px; padding:4px 0; font-size:13px;}
#sidebar .legend-dot{width:10px; height:10px; border-radius:3px; flex-shrink:0;}
#sidebar .progress-bar{background:rgba(255,255,255,.15); border-radius:6px; height:6px;
  margin-top:8px; overflow:hidden;}
#sidebar .progress-fill{background:#4fae8b; height:100%;}

/* ---- content pages: leave room for the sidebar, and CONTAIN to viewport ---- */
html, body{overflow-x:hidden !important;}
.gradio-container{overflow-x:hidden !important; width:100% !important;}
#page_overview, #page_timeline, #page_label, #page_guide{
  margin-left:288px !important;
  width:calc(100% - 288px) !important;
  max-width:calc(100% - 288px) !important;
  box-sizing:border-box !important;
  padding:14px 32px 14px !important;
}
#page_overview *, #page_timeline *, #page_label *, #page_guide *{ box-sizing:border-box !important; }
.card-divider{border-top:1px solid #eaf0ed; margin:16px 0 14px;}
/* the title is the FIRST line of content (matches the sidebar brand being the
   first line of sidebar content) — the eyebrow rides inline as a badge instead
   of sitting above the title, which is what previously threw off alignment */
.page-head{font-size:28px; font-weight:800; color:#0f2624 !important;
  display:flex; align-items:center; gap:12px; margin-bottom:16px; margin-top:0;
  letter-spacing:-.02em;}
.page-head .pg-dot{width:10px; height:10px; border-radius:50%;
  background:#33a68c; display:inline-block; box-shadow:0 0 0 4px rgba(51,166,140,.18);}
.page-badge{font-size:11px; font-weight:700; letter-spacing:.08em; text-transform:uppercase;
  color:#00726f !important; background:#dcefec; padding:4px 10px; border-radius:20px;}
/* Timeline Viewer page fills exactly the visible viewport height (no more,
   no less) so the chart + side panel row stretch together to use the
   available space and the page never needs to scroll. Because align-items:
   stretch makes chart-col and panel-col match each other's height either
   way. */
.timeline-row{display:flex !important; width:100% !important; gap:14px !important; align-items:stretch !important;
  flex-wrap:wrap !important;}
.timeline-row .ui-card{padding:14px !important; box-sizing:border-box !important;}
/* chart-col is the ONLY item that grows — it always absorbs 100% of whatever
   space panel-col (fixed width) doesn't use. Don't rely on flex-grow ratios
   redistributing around a max-width cap — that leaves dead space in Chrome. */
.chart-col{flex:1 1 auto !important; min-width:0 !important; max-width:none !important;
  display:flex !important; flex-direction:column !important; box-sizing:border-box !important;}
.chart-col > .block{flex:1 1 auto !important; min-height:0 !important; display:flex !important; flex-direction:column !important;}
.chart-col > .block iframe{flex:1 1 auto !important; height:100% !important;}
.panel-col{flex:0 0 500px !important; width:500px !important; min-width:420px !important; max-width:500px !important;
  box-sizing:border-box !important;
  display:flex !important; flex-direction:column !important; gap:14px !important;}
.panel-row{display:flex !important; width:100% !important; gap:14px !important; align-items:stretch !important;}
/* align-items:stretch on .panel-row only stretches the outer Gradio wrapper —
   the visible .ui-card div nested inside it still sizes to its own content
   unless we explicitly cascade flex:1 down through every wrapper level. */
.panel-cell{flex:1 1 0 !important; min-width:0 !important; display:flex !important; flex-direction:column !important;}
/* Gradio nests HTML content as .block > .html-container > .prose > .ui-card —
   flex:1 has to cascade through EVERY one of those known wrapper classes or
   the chain breaks and .ui-card falls back to its own content height. */
.panel-cell > *,
.panel-cell .html-container,
.panel-cell .prose{
  flex:1 1 auto !important; display:flex !important; flex-direction:column !important;
  min-height:0 !important; height:auto !important;
}
.panel-cell .ui-card{flex:1 1 auto !important;}

/* Timeline Viewer top row: Patient ID / Load Timeline / Chart Status side by
   side, all the same height. The button has no label line above it like the
   dropdown/textbox do, so it needs to stretch to fill its column instead of
   sizing to its own short natural height. */
.controls-row{display:flex !important; align-items:stretch !important; gap:14px !important; width:100% !important;}
.controls-row > .column{display:flex !important; flex-direction:column !important;}
.load-btn-col{justify-content:flex-end !important;}
.load-btn-col .block{flex:1 1 auto !important; display:flex !important;}
.load-btn{flex:1 1 auto !important; height:100% !important;}
.btn-light-teal{background:#dcefec !important; color:#00504f !important; border:1px solid #b9dcd6 !important;}
.btn-light-teal:hover{background:#cbe6e1 !important;}

/* Labelling Mode: Labelling Period / Flare Assessment / Edit Existing Label /
   Saved Labels side by side in one row, then the graph full-width below. */
.label-row{display:flex !important; width:100% !important; gap:14px !important;
  align-items:stretch !important; flex-wrap:wrap !important; margin-bottom:14px !important;}
.label-row > .ui-card{display:flex !important; flex-direction:column !important; padding:16px !important;}
.lbl-period{flex:2 1 220px !important; min-width:200px !important;}
.lbl-flare{flex:3 1 280px !important; min-width:260px !important;}
.lbl-edit{flex:2 1 220px !important; min-width:200px !important;}
.lbl-saved{flex:3 1 260px !important; min-width:240px !important;}

/* User Guide: style the rendered markdown to match the app's theme.
   Flow the sections into columns instead of one long narrow strip so the
   page uses the full width of the screen. */
.guide-card{max-width:100% !important; padding:32px 40px !important;}
/* .guide-card itself is a flex container (Gradio Column default) — multicol
   has no effect on flex children, so target the actual markdown text wrapper
   nested inside it instead. */
.guide-card .prose{column-count:2 !important; column-gap:48px !important; column-rule:1px solid #eaf0ed !important;}
.guide-card h2{column-span:all !important; font-size:22px !important; font-weight:800 !important;
  color:#0f2624 !important; margin:0 0 18px !important; letter-spacing:-.01em;}
.guide-card h3{font-size:16px !important; font-weight:700 !important; color:#00504f !important;
  margin:26px 0 10px !important; padding-bottom:6px !important; border-bottom:2px solid #dcefec !important;
  break-after:avoid !important;}
.guide-card h3:first-of-type{margin-top:0 !important;}
.guide-card p, .guide-card li{font-size:14px !important; line-height:1.65 !important; color:#28423d !important;}
.guide-card ul{margin:6px 0 14px !important; padding-left:22px !important; break-inside:avoid !important;}
.guide-card li{margin-bottom:4px !important;}
.guide-card pre{break-inside:avoid !important;}
.guide-card strong{color:#152826 !important;}
.guide-card code{background:#eef4f1 !important; color:#00504f !important; padding:1px 6px !important;
  border-radius:4px !important; font-size:12.5px !important;}
.guide-card pre{background:#152826 !important; border-radius:8px !important; padding:14px 16px !important;
  overflow-x:auto !important; margin:10px 0 16px !important;}
.gradio-container .guide-card pre code, .gradio-container .guide-card pre code *{
  background:transparent !important; color:#dcefec !important; padding:0 !important;
}
.panel-cell.ui-card{display:flex !important; flex-direction:column !important; justify-content:flex-start !important;}
@media (max-width:820px){
  .chart-col, .panel-col{flex:1 1 100% !important; max-width:100% !important;}
}
@media (max-width:520px){
  .panel-row{flex-wrap:wrap !important;}
}

/* ---- cards ---- */
.ui-card{background:#ffffff !important; border:1px solid #dfe8e4 !important;
  border-radius:14px !important; padding:20px !important;
  box-shadow:0 1px 3px rgba(21,64,58,.06), 0 1px 2px rgba(21,64,58,.04) !important;}
.card-title{font-weight:700; color:#0f2624 !important; margin-bottom:14px; font-size:16px;
  display:flex; align-items:center; gap:8px; letter-spacing:-.01em;}
.card-title .icon-chip{display:inline-flex; align-items:center; justify-content:center;
  width:26px; height:26px; border-radius:8px; background:#dcefec; font-size:14px;}
.info-row{display:flex; justify-content:space-between; padding:8px 0;
  border-bottom:1px solid #eef3f1; font-size:14px; color:#152826 !important;}
.info-row:last-child{border-bottom:none;}
.info-row .count{color:#00726f !important; font-weight:700;}
.muted{color:#8a9a96 !important; font-size:13px; padding:6px 0;}

/* ---- stat tiles (Data Overview) — tonal accent bar per tile ---- */
.stat-row{display:grid; grid-template-columns:repeat(4, 1fr); gap:16px; margin-bottom:16px;}
.stat-tile{padding:18px 20px !important; position:relative; overflow:hidden; min-height:80px;
  background:linear-gradient(180deg,#ffffff 0%,#f7fbfa 100%) !important;}
.stat-tile::before{content:""; position:absolute; top:0; left:0; right:0; height:4px;
  background:linear-gradient(90deg,#00726f,#4fae8b);}
.stat-label{font-size:13px; color:#5a6b67 !important; margin-bottom:8px; font-weight:600;
  text-transform:uppercase; letter-spacing:.04em;}
.stat-value{font-size:32px; font-weight:800; color:#0f2624 !important; letter-spacing:-.02em;}
.card-grid-2{display:grid; grid-template-columns:1fr 1fr; gap:18px;}
.card-grid-3{display:flex !important; gap:16px !important; align-items:stretch !important;}
.card-grid-3 > .ui-card{flex:1 1 0 !important; display:flex !important; flex-direction:column !important; min-height:0;}
.card-cta{margin-top:auto !important; padding-top:10px;}

/* ---- flare period rows ---- */
.flare-row{border-left:3px solid #d1495b; background:#fdf4f4; border-radius:0 8px 8px 0;
  padding:7px 0 7px 12px; margin-bottom:8px;}
.flare-date{display:block; font-weight:600; color:#152826 !important; font-size:13px;}
.flare-label{display:block; color:#5a6b67 !important; font-size:12px;}

/* ---- flare category checkbox grid (Labelling Mode) ---- */
.category-grid .wrap{display:grid !important; grid-template-columns:1fr 1fr; gap:8px !important;}
.category-grid label{border:1px solid #d7e1de !important; border-radius:10px !important;
  padding:9px 10px !important; background:#fff !important; justify-content:flex-start !important;}
.category-grid input:checked + span{color:#006867 !important; font-weight:600;}

/* ---- section title underline retint (legacy labelling CSS) ---- */
.section-title{color:#152826 !important; border-bottom-color:#006867 !important;}
.gr-form:focus-within, .clean-month-dropdown .gr-form:focus-within{
  border-color:#006867 !important; box-shadow:0 0 0 3px rgba(0,104,103,.12) !important;
}
</style>
"""

SIDEBAR_BRAND_HTML = "<div id='brand'><span class='logo'>⚡</span> Patient Timeline</div>"

# Remove the 'dark' class Gradio/browser may add on load, so the app always
# renders in the light/turquoise theme regardless of OS colour-scheme.
FORCE_LIGHT_JS = """
() => {
    document.documentElement.classList.remove('dark');
    document.body.classList.remove('dark');
    document.querySelectorAll('.dark').forEach(el => el.classList.remove('dark'));
}
"""


# ----------------------------------------------------------------------
# HTML card builders — always read LIVE data off `app`, nothing fabricated.
# ----------------------------------------------------------------------

def _stat_tile(label, value):
    return (f"<div class='ui-card stat-tile'><div class='stat-label'>{label}</div>"
            f"<div class='stat-value'>{value}</div></div>")

def overview_stats_html():
    s = app.get_overview_stats()
    date_range = f"{s['date_range_years']} yr" if s['date_range_years'] else "—"
    tiles = [
        ("Total records", f"{s['total_records']:,}"),
        ("Patients", f"{s['patients']}"),
        ("IBD-related", f"{s['ibd_pct']}%"),
        ("Date range", date_range),
    ]
    return "<div class='stat-row'>" + "".join(_stat_tile(l, v) for l, v in tiles) + "</div>"

def dataset_info_html():
    s = app.get_overview_stats()
    date_range = f"{s['date_min']} – {s['date_max']}" if s['date_min'] else "—"
    rows = [
        ("Records", f"{s['total_records']:,}"),
        ("Patients", f"{s['patients']}"),
        ("Date range", date_range),
        ("Avg / patient", f"{s['avg_per_patient']}"),
        ("Access group", app.group_name),
    ]
    body = "".join(f"<div class='info-row'><span>{k}</span><span>{v}</span></div>" for k, v in rows)
    return f"<div class='ui-card'><div class='card-title'><span class='icon-chip'>📋</span>Dataset info</div>{body}</div>"

def event_breakdown_html():
    items = app.get_event_breakdown()
    if not items:
        body = "<div class='muted'>No data loaded</div>"
    else:
        body = "".join(f"<div class='info-row'><span>{n}</span><span class='count'>{c}</span></div>"
                        for n, c in items[:8])
    return f"<div class='ui-card'><div class='card-title'><span class='icon-chip'>📊</span>Event breakdown</div>{body}</div>"

def sidebar_dataset_ctx_html():
    status = "Data loaded" if app.combined_data is not None else "No data loaded"
    return (f"<div class='ctx-card'><div class='ctx-title'>Dataset</div>"
            f"<div class='ctx-main'>{app.group_name}</div>"
            f"<div class='ctx-sub'>{status}</div></div>")

def patient_panel_html():
    stats = app.get_patient_panel_stats()
    if not stats:
        return "<div class='ui-card'><div class='card-title'><span class='icon-chip'>🧑‍⚕️</span>Patient info</div><div class='muted'>No patient loaded</div></div>"
    rows = [
        ("Records", f"{stats['records']:,}"),
        ("Follow-up", f"{stats['followup_years']} yr"),
        ("IBD events", f"{stats['ibd_pct']}%"),
        ("Flares", stats['flares']),
    ]
    body = "".join(f"<div class='info-row'><span>{k}</span><span>{v}</span></div>" for k, v in rows)
    return (f"<div class='ui-card'><div class='card-title'><span class='icon-chip'>🧑‍⚕️</span>Patient info</div>"
            f"<div style='font-weight:600;margin-bottom:8px;color:#00726f;'>Patient #{stats['patient_id']}</div>{body}</div>")

def event_counts_html():
    items = app.get_event_breakdown(app.current_patient_data)
    pid = app.current_patient_id
    heading = (f"<div style='font-weight:600;margin-bottom:8px;color:#00726f;'>Patient #{pid}</div>"
               if pid is not None else "")
    if not items:
        body = "<div class='muted'>No events</div>"
    else:
        body = "".join(f"<div class='info-row'><span>{n}</span><span class='count'>{c}</span></div>" for n, c in items)
    return f"<div class='ui-card'><div class='card-title'><span class='icon-chip'>📊</span>Event counts</div>{heading}{body}</div>"

def flare_periods_html():
    entries = app.get_flare_periods_list()
    if not entries:
        body = "<div class='muted'>No flare periods</div>"
    else:
        body = "".join(
            f"<div class='flare-row'><span class='flare-date'>{e['date_str']}</span>"
            f"<span class='flare-label'>{e['label']}</span></div>" for e in entries
        )
    return f"<div class='ui-card'><div class='card-title'><span class='icon-chip'>🔥</span>Flare periods</div>{body}</div>"

def sidebar_patient_ctx_html():
    if app.current_patient_id is None:
        return "<div class='ctx-card'><div class='ctx-title'>Patient</div><div class='ctx-sub'>No patient loaded</div></div>"
    return (f"<div class='ctx-card'><div class='ctx-title'>Patient</div>"
            f"<div class='ctx-main'>Patient #{app.current_patient_id}</div>"
            f"<div class='ctx-sub'>IBD Cohort</div></div>")

def sidebar_legend_html():
    from timeline_visualization import get_label_mapping
    colors = {
        'Lab Test': '#6b8fd6', 'Hospital Admission': '#8b6bd6', 'Physician Claim': '#5bb8c9',
        'Ambulatory Visit': '#5cae7f', 'Prescription': '#d9a441', 'Imaging': '#d65b8f',
    }
    rows = "".join(
        f"<div class='legend-row'><span class='legend-dot' style='background:{c}'></span>{name}</div>"
        for name, c in colors.items()
    )
    return f"<div class='ctx-card'><div class='ctx-title'>Legend</div>{rows}</div>"

def session_card_html():
    prog = app.get_labelling_progress()
    pid = app.current_patient_id if app.current_patient_id is not None else "—"
    pct = int(100 * prog['labelled'] / prog['total']) if prog['total'] else 0
    return (
        f"<div class='ctx-card'><div class='ctx-title'>Session</div>"
        f"<div class='ctx-main'>Patient #{pid}</div>"
        f"<div class='ctx-sub'>{prog['labelled']} / {prog['total']} months labelled</div>"
        f"<div class='progress-bar'><div class='progress-fill' style='width:{pct}%'></div></div></div>"
        f"<div class='ctx-card'><div class='ctx-title'>Flare summary</div>"
        f"<div class='info-row'><span>Flares found</span><span>{prog['flares']}</span></div>"
        f"<div class='info-row'><span>No flare</span><span>{prog['no_flare']}</span></div></div>"
    )


def create_interface():
    """
    Create the main Gradio web interface for the Patient Timeline Viewer.

    Builds the interface with a left sidebar (navigation + context) and four
    pages: Data Overview, Timeline Viewer, Labelling Mode, User Guide.

    Returns:
        gr.Blocks: Configured Gradio interface
    """

    with gr.Blocks(
        title=f"Patient Timeline Viewer - {app.group_name}",
        theme=gr.themes.Soft(
            font=[gr.themes.GoogleFont("Inter"), "Arial", "Roboto"],
            primary_hue="teal",
            neutral_hue="slate",
        ),
        js=FORCE_LIGHT_JS,
    ) as demo:

        # ====================================================================
        # CUSTOM CSS STYLING (legacy — still used by Labelling Mode controls)
        # ====================================================================
        gr.HTML(elem_classes=["style-inject"], value="""
            <style>
            .clean-control-column { padding-right: 20px !important; }
            .clean-control-column > * { margin-bottom: 12px !important; }
            .clean-control-column .section-title { margin-top: 10px !important; margin-bottom: 8px !important; }
            .clean-control-column .section-title:first-child { margin-top: 0 !important; }
            .clean-month-dropdown { margin-bottom: 12px !important; }
            .month-nav-row { display: flex !important; gap: 8px !important; margin-bottom: 16px !important; }
            .month-nav-button { flex: 1 !important; border-radius: 8px !important; padding: 8px 12px !important;
                font-size: 14px !important; font-weight: 500 !important; }
            .timeline-nav { margin-bottom: 12px !important; padding: 8px 0 !important; display: flex !important;
                align-items: center !important; gap: 12px !important; }
            .timeline-nav button { border-radius: 8px !important; padding: 8px 16px !important; font-size: 14px !important;
                font-weight: 500 !important; }
            .labelling-top-row { align-items: flex-start !important; margin-bottom: 25px !important; }
            .labelling-top-row .section-title { margin-top: 0 !important; }
            .gradio-button { border-radius: 8px !important; font-weight: 500 !important; transition: all 0.2s ease !important; }
            .gr-plot { border-radius: 10px !important; border: 1px solid #e5e7eb !important; overflow: hidden !important; }
            .gradio-group { border: none !important; background: none !important; padding: 0 !important; margin: 0 !important; }
            </style>
            """
        )

        # New-UI palette + sidebar/page layout CSS
        gr.HTML(NEW_UI_CSS, elem_classes=["style-inject"])

        # ====================================================================
        # LEFT SIDEBAR — brand, navigation, per-page context
        # ====================================================================
        with gr.Column(elem_id="sidebar", min_width=288):
            gr.HTML(SIDEBAR_BRAND_HTML)
            gr.HTML("<div class='nav-section'>Navigation</div>")
            nav_overview = gr.Button("Data Overview",   elem_classes=["nav-btn"], variant="primary")
            nav_timeline = gr.Button("Timeline Viewer", elem_classes=["nav-btn"], variant="secondary")
            nav_label    = gr.Button("Labelling Mode",  elem_classes=["nav-btn"], variant="secondary")
            nav_guide    = gr.Button("User Guide",      elem_classes=["nav-btn"], variant="secondary")

            ctx_overview = gr.HTML(sidebar_dataset_ctx_html(), visible=True)
            ctx_timeline_patient = gr.HTML(sidebar_patient_ctx_html(), visible=False)
            ctx_timeline_legend  = gr.HTML(sidebar_legend_html(), visible=False)
            ctx_label = gr.HTML(session_card_html(), visible=False)

        # ====================================================================
        # PAGE: DATA OVERVIEW
        # ====================================================================
        with gr.Column(elem_id="page_overview", elem_classes=["page"], visible=True) as page_overview:
            gr.HTML("<div class='page-head'><span class='pg-dot'></span>Data Overview"
                    "<span class='page-badge'>Cohort Summary</span></div>")

            stat_tiles = gr.HTML(overview_stats_html())

            with gr.Row(elem_classes=["card-grid-3"], equal_height=False):
                # --- Card 1: Dataset info ---
                with gr.Column(elem_classes=["ui-card"]):
                    dataset_info_card = gr.HTML(dataset_info_html())
                    data_status = gr.Textbox(label="Status", value=app.get_data_status(), interactive=False, visible=False)
                    reload_data_btn = gr.Button("↻ Reload Data", variant="primary", elem_classes=["card-cta"])

                # --- Card 2: Load from config ---
                with gr.Column(elem_classes=["ui-card"]):
                    gr.HTML("<div class='card-title'><span class='icon-chip'>⚙️</span>Config info</div>"
                            "<div class='muted' style='margin-bottom:10px;'>Upload a <code>study_config.yaml</code> "
                            "with paths to your data files on this server.</div>")
                    upload_config = gr.UploadButton("↑ Upload study_config.yaml", file_types=[".yaml", ".yml"],
                                                     elem_classes=["btn-light-teal"])
                    config_name   = gr.Textbox(value="no file", show_label=False, interactive=False, max_lines=1, lines=1)
                    load_config_btn = gr.Button("Load Config & Data", variant="primary", elem_classes=["card-cta"])
                    config_status   = gr.Textbox(label="Status", value="", interactive=False, lines=1)

                # --- Card 3: Export data (with event breakdown table) ---
                with gr.Column(elem_classes=["ui-card"]):
                    event_breakdown_card = gr.HTML(event_breakdown_html())
                    gr.HTML("<div class='card-divider'></div>")
                    gr.HTML("<div class='card-title' style='margin-bottom:8px;'>"
                            "<span class='icon-chip'>⬇️</span>Export data</div>")
                    export_format = gr.Radio(["CSV", "Excel"], label="Format", value="CSV")
                    export_btn = gr.Button("⬇ Export Data", variant="primary", elem_classes=["card-cta"])
                    export_status = gr.Textbox(label="Export Status", value="", interactive=False)

        # ====================================================================
        # PAGE: TIMELINE VIEWER
        # ====================================================================
        with gr.Column(elem_id="page_timeline", elem_classes=["page"], visible=False) as page_timeline:
            gr.HTML("<div class='page-head'><span class='pg-dot'></span>Timeline Viewer"
                    "<span class='page-badge'>Patient History</span></div>")

            with gr.Row(elem_classes=["controls-row"]):
                with gr.Column(scale=2, min_width=200):
                    patient_dropdown = gr.Dropdown(
                        label="Patient ID",
                        choices=app.get_patient_choices(),
                        value=app.get_patient_choices()[0] if app.get_patient_choices() else None,
                        interactive=True
                    )
                with gr.Column(scale=1, min_width=170, elem_classes=["load-btn-col"]):
                    load_timeline_btn = gr.Button("▷ Load Timeline", variant="primary", elem_classes=["load-btn"])
                with gr.Column(scale=4):
                    chart_status = gr.Textbox(label="Chart Status", value="No chart loaded", interactive=False)

            with gr.Row(elem_classes=["timeline-row"]):
                with gr.Column(scale=3, min_width=0, elem_classes=["chart-col"]):
                    with gr.Column(elem_classes=["ui-card"]):
                        # Full width timeline — rendered client-side via Plotly.js.
                        # IBD filter buttons live inside the HTML component itself.
                        timeline_plot = gr.HTML(
                            value="<p style='color:#6b7280;padding:20px;text-align:center;'>"
                                  "Select a patient and click Load Timeline to view the chart.</p>"
                        )
                # 2x2 grid: Patient info / Event counts on top, Chart Information / Flare periods on bottom
                with gr.Column(scale=2, min_width=420, elem_classes=["panel-col"]):
                    with gr.Row(elem_classes=["panel-row"]):
                        with gr.Column(elem_classes=["panel-cell"], min_width=0):
                            patient_panel_card = gr.HTML(patient_panel_html())
                        with gr.Column(elem_classes=["panel-cell"], min_width=0):
                            event_counts_card = gr.HTML(event_counts_html())
                    with gr.Row(elem_classes=["panel-row"]):
                        with gr.Column(elem_classes=["panel-cell", "ui-card"], min_width=0):
                            chart_info = gr.Textbox(label="Chart Information", value="No patient data loaded",
                                                  lines=10, max_lines=14, interactive=False)
                        with gr.Column(elem_classes=["panel-cell"], min_width=0):
                            flare_periods_card = gr.HTML(flare_periods_html())

        # ====================================================================
        # PAGE: LABELLING MODE
        # ====================================================================
        with gr.Column(elem_id="page_label", elem_classes=["page"], visible=False) as page_label:
            gr.HTML("<div class='page-head'><span class='pg-dot'></span>Labelling Mode"
                    "<span class='page-badge'>Flare Assessment</span></div>")

            with gr.Row(elem_classes=["controls-row"]):
                with gr.Column(scale=2, min_width=200):
                    patient_dropdown_label = gr.Dropdown(
                        label="Patient ID",
                        choices=app.get_patient_choices(),
                        value=app.get_patient_choices()[0] if app.get_patient_choices() else None,
                        interactive=True
                    )
                with gr.Column(scale=1, min_width=170, elem_classes=["load-btn-col"]):
                    load_labelling_btn = gr.Button("▷ Load Patient", variant="primary", elem_classes=["load-btn"])
                with gr.Column(scale=4):
                    label_chart_status = gr.Textbox(
                        label="Chart Status",
                        value="Select and load a patient to begin labelling",
                        interactive=False
                    )

            # Four cards side by side: Labelling Period, Flare Assessment, Edit Existing Label, Saved Labels
            with gr.Row(elem_classes=["label-row"]):
                with gr.Column(elem_classes=["ui-card", "lbl-period"]):
                    gr.HTML("<div class='card-title'><span class='icon-chip'>🗓️</span>Labelling Period</div>")
                    month_dropdown = gr.Dropdown(
                        label="Select Month",
                        choices=[],
                        interactive=True,
                        elem_classes="clean-month-dropdown"
                    )
                    with gr.Row(elem_classes="month-nav-row"):
                        month_back_btn = gr.Button("◀ Previous Month",
                                                 size="sm", variant="secondary", elem_classes="month-nav-button")
                        month_forward_btn = gr.Button("Next Month ▶",
                                                    size="sm", variant="secondary", elem_classes="month-nav-button")

                with gr.Column(elem_classes=["ui-card", "lbl-flare"]):
                    gr.HTML("<div class='card-title'><span class='icon-chip'>🔥</span>Flare Assessment</div>")
                    flare_evidence = gr.Radio(
                        choices=["Yes", "No"],
                        label="Evidence of Flare",
                        value="No",
                        interactive=True
                    )
                    category_dropdown_label = gr.CheckboxGroup(
                        label="Category (Required if Yes)",
                        choices=[
                            "Ambulatory Visit", "Lab Test", "Prescription",
                            "Physician Claim", "Hospital Admission", "Imaging"
                        ],
                        value=[],
                        interactive=True,
                        elem_classes=["category-grid"],
                    )
                    reason_input_label = gr.Textbox(
                        label="Reason (Optional)",
                        placeholder="Enter reason for flare",
                        lines=2
                    )
                    with gr.Row():
                        save_label_btn = gr.Button("💾 Save Label", variant="primary", scale=1)
                        clear_label_btn = gr.Button("Clear Label", variant="secondary", scale=1)

                with gr.Column(elem_classes=["ui-card", "lbl-edit"]):
                    gr.HTML("<div class='card-title'><span class='icon-chip'>✏️</span>Edit Existing Label</div>")
                    edit_month_dropdown = gr.Dropdown(
                        label="Select Month to Edit",
                        choices=[],
                        interactive=True
                    )
                    with gr.Row():
                        load_edit_btn = gr.Button("Load for Edit", variant="secondary", scale=1)
                        delete_label_btn = gr.Button("🗑 Delete Label", variant="stop", scale=1)

                with gr.Column(elem_classes=["ui-card", "lbl-saved"]):
                    gr.HTML("<div class='card-title'><span class='icon-chip'>📋</span>Saved Labels</div>")
                    labels_info = gr.Textbox(
                        label="Labels Summary",
                        value="No labels saved yet",
                        interactive=False,
                        lines=8,
                        max_lines=12
                    )

            # Full-width graph below the card row
            with gr.Column(elem_classes=["ui-card"]):
                with gr.Row(elem_classes="timeline-nav"):
                    view_back_btn_visible = gr.Button("◀ Previous Month",
                                                    size="sm", variant="secondary")
                    gr.HTML("<div style='flex: 1;'></div>")
                    view_forward_btn_visible = gr.Button("Next Month ▶",
                                                       size="sm", variant="secondary")

                monthly_timeline_plot = gr.Plot()

            current_view_info_visible = gr.Textbox(
                label="Current View", value="", interactive=False, visible=False
            )

        # ====================================================================
        # PAGE: USER GUIDE  (content unchanged)
        # ====================================================================
        with gr.Column(elem_id="page_guide", elem_classes=["page"], visible=False) as page_guide:
            gr.HTML("<div class='page-head'><span class='pg-dot'></span>User Guide"
                    "<span class='page-badge'>Reference</span></div>")
            with gr.Column(elem_classes=["ui-card", "guide-card"]):
              gr.Markdown("""
## Patient Timeline Viewer — User Guide

### 1. Data Loading & Access Control
- **Command-Based Access**: Different commands provide access to different patient groups
- **Available Commands**:
  - `uv run python main.py group-a` - Access patients 1-100
  - `uv run python main.py group-b` - Access patients 101-200
  - `uv run python main.py group-c` - Access patients 201-300
  - `uv run python main.py custom --start X --end Y --name "Group Name"` - Custom range
  - `uv run python main.py admin` - Access all patients (admin mode)
- **Save Directories**: Group-specific folders (`groupa_saved_flares/`, `groupb_saved_flares/`, etc.)
- **Reload Data**: Use the "Reload Data" button to refresh data from the directory
- **Export Current Data**: Save the currently loaded data to CSV or Excel format

### 2. Running on Remote Server
**Terminal 1 - Start Application**:
```bash
uv run python main.py admin --rmt23345-dir /path/to/data
```

**Terminal 2 - SSH Tunnel**:
```bash
ssh -L 7860:localhost:7860 username@server-hostname
```

Access: Open browser to http://localhost:7860

### 3. Timeline Viewer & Event Filtering
- **Patient Selection**: Choose a patient from the dropdown (automatically populated from your assigned patient group)
- **IBD Event Filtering**: Use the buttons above the chart to filter events:
  - **"All Events"** - Show all medical events (default)
  - **"IBD Related Only"** - Show only IBD-related events (`ibd_related = True`)
  - **"Non-IBD Related Only"** - Show only non-IBD events (`ibd_related = False`)
- **Real-time Filtering**: Event filter changes apply immediately without reloading
- **Interactive Chart**: Hover over events for detailed information, zoom and pan as needed
- **Cross-Tab Flares**: Monthly flares created in Labelling Mode appear as highlighted periods on the timeline

### 4. Labelling Mode (Monthly Flare Labeling)
- **Patient Selection**: Choose a patient for monthly labeling
- **Month Navigation**: Select specific months using dropdown and navigation buttons
- **Monthly View**: Timeline shows selected month with navigation to view adjacent months
- **Evidence Classification**: Mark each month as having flare evidence (Yes/No)
- **Category Selection**: If evidence exists, select relevant medical event categories
- **Reason Documentation**: Optional text field for additional details
- **Efficient Navigation**: Dropdown only shows months with events for faster labeling
- **Auto-Reset Form**: Form clears automatically when switching months

### 5. Monthly Timeline Features
- **Focused View**: Shows one month at a time with context from adjacent periods
- **Navigation Controls**: Move view forward/backward while maintaining labeling target
- **Visual Highlighting**: Selected month highlighted for easy reference
- **Persistent Labels**: All monthly labels saved automatically per patient group directories
- **Flare Highlighting**: Months with Evidence=Yes show a highlighted background
- **Enhanced JSON Format**: Labels include metadata, timestamps, and readable category names
- **Rich Hover Information**: All flare details available on hover in both tabs
- **Cross-Tab Synchronization**: Monthly flares automatically appear in Timeline Viewer

### 6. Lab Test Visualization
- **Multiple Same-Day Tests**: When multiple lab tests occur on the same day, they appear as separate adjacent bars with 2-hour time offsets
- **Visual Separation**: Each lab test maintains its original duration but gets a small time offset for visibility
- **Individual Hover Data**: Each lab test bar shows its own specific details in the hover tooltip

### 7. Advanced Features
- **Command-Line Access Control**: Different teams can access different patient cohorts
- **Automatic Data Loading**: No need to manually upload files - data is loaded from the specified directory
- **Group-Specific Save Directories**: Labels saved to separate folders per access group
- **Rich Hover Information**: View detailed event information with smart text wrapping for long descriptions
- **Colour-Coded Events**: Different event types (lab tests, prescriptions, visits, etc.) have distinct colours, and always in same Y-axis order
- **Export Capabilities**: Save charts as images using Plotly's built-in tools
- **Real-time Chart Updates**: All filtering and flare changes update the chart immediately

### 8. Data Format Requirements
The app expects CSV files with "events" in the filename containing:

**Required columns:**
- `patient_id`: Unique identifier for each patient (integer)
- `start_date`: Event start date (YYYY-MM-DD format)
- `end_date`: Event end date (YYYY-MM-DD format)
- `event_type`: Type of medical event (string)
- `ibd_related`: Boolean flag indicating if event is IBD-related (True/False)

**Optional columns:**
- `event_info`: JSON string with additional details (displayed in hover tooltips)
- `source_dataset`: Data source identifier (e.g., "CLAIMS", "LAB", "DAD")
- Any additional columns will be displayed in hover information if part of `event_info`

### 9. Command Line Examples
```bash
# Research team accessing early patients
uv run python main.py group-a

# Clinical team accessing different cohort
uv run python main.py group-b

# Custom analysis group
uv run python main.py custom --start 150 --end 250 --name "Cohort Study"

# Administrator viewing all patients
uv run python main.py admin
```

### 10. Troubleshooting
- **No patients visible**: Check that your command provides access to patients in the data range
- **Missing events**: Verify the IBD filter setting matches what you want to see
- **Overlapping lab tests**: The app automatically separates same-day lab tests - if still overlapping, try refreshing the chart
- **Flare not saving**: Ensure dates are in YYYY-MM-DD format and end date is after start date, check group directory permissions (groupa_saved_flares/, etc.)
- **Data not loading**: Check that the data directory exists and contains CSV files with "events" in the filename
- **Monthly flares not showing**: Ensure you're viewing the correct patient and the timeline is refreshed
- **Permission denied**: Ensure group directories have proper permissions (chmod 2775)
- **SSH tunnel not working**: Verify both terminals are running and port numbers match
""")

        # ====================================================================
        # EVENT HANDLERS - DATA OVERVIEW PAGE
        # ====================================================================

        def reload_data_wrapped():
            status, dd_update, info = app.reload_data()
            return status, dd_update, info, overview_stats_html(), dataset_info_html(), event_breakdown_html(), sidebar_dataset_ctx_html()

        reload_data_btn.click(
            reload_data_wrapped,
            outputs=[data_status, patient_dropdown, chart_info, stat_tiles, dataset_info_card, event_breakdown_card, ctx_overview]
        )

        export_btn.click(
            app.export_data,
            inputs=[export_format],
            outputs=[export_status]
        )

        def load_config_wrapped(config_file):
            cfg_status, status, dd_update, info = app.load_config_file(config_file)
            return cfg_status, status, dd_update, info, overview_stats_html(), dataset_info_html(), event_breakdown_html(), sidebar_dataset_ctx_html()

        load_config_btn.click(
            load_config_wrapped,
            inputs=[upload_config],
            outputs=[config_status, data_status, patient_dropdown, chart_info, stat_tiles, dataset_info_card, event_breakdown_card, ctx_overview]
        )

        def _fname(f):
            if f is None:
                return "no file"
            p = f if isinstance(f, str) else f.name
            return os.path.basename(p)

        upload_config.upload(_fname, inputs=upload_config, outputs=config_name)

        # ====================================================================
        # EVENT HANDLERS - TIMELINE VIEWER PAGE
        # ====================================================================

        def load_timeline_wrapped(patient_id):
            html, status, info = app.load_patient_timeline_html(patient_id)
            return (html, status, info, patient_panel_html(), event_counts_html(),
                    flare_periods_html(), sidebar_patient_ctx_html(), sidebar_legend_html())

        load_timeline_btn.click(
            load_timeline_wrapped,
            inputs=[patient_dropdown],
            outputs=[timeline_plot, chart_status, chart_info, patient_panel_card, event_counts_card,
                     flare_periods_card, ctx_timeline_patient, ctx_timeline_legend]
        )

        patient_dropdown.change(
            load_timeline_wrapped,
            inputs=[patient_dropdown],
            outputs=[timeline_plot, chart_status, chart_info, patient_panel_card, event_counts_card,
                     flare_periods_card, ctx_timeline_patient, ctx_timeline_legend]
        )

        # ====================================================================
        # EVENT HANDLERS - LABELLING MODE PAGE
        # ====================================================================

        current_view_info = gr.Textbox(label="Current View", value="", interactive=False, visible=False)
        view_back_btn = gr.Button("◀ Previous Month", variant="secondary", visible=False)
        view_forward_btn = gr.Button("Next Month ▶", variant="secondary", visible=False)

        def load_labelling_wrapped(patient_id):
            status, month_update, view_info, labels = app.load_patient_for_labelling(patient_id)
            return status, month_update, view_info, labels, session_card_html()

        load_labelling_btn.click(
            load_labelling_wrapped,
            inputs=[patient_dropdown_label],
            outputs=[label_chart_status, month_dropdown, current_view_info_visible, labels_info, ctx_label]
        )

        def navigate_month_back(month):
            new_month = app.navigate_month(month, "back")
            edit_choices = app.get_monthly_labels_list()
            return new_month, gr.update(choices=edit_choices), "No", [], "", session_card_html()

        def navigate_month_forward(month):
            new_month = app.navigate_month(month, "forward")
            edit_choices = app.get_monthly_labels_list()
            return new_month, gr.update(choices=edit_choices), "No", [], "", session_card_html()

        def update_month_view(month):
            app.current_view_offset = 0
            if month:
                fig, status, view_info = app.update_monthly_view(month, 0)
                edit_choices = app.get_monthly_labels_list()
                return fig, status, view_info, gr.update(choices=edit_choices), "No", [], "", session_card_html()
            return None, "No month selected", "", gr.update(choices=[]), "No", [], "", session_card_html()

        month_back_btn.click(
            navigate_month_back,
            inputs=[month_dropdown],
            outputs=[month_dropdown, edit_month_dropdown, flare_evidence, category_dropdown_label, reason_input_label, ctx_label]
        )

        month_forward_btn.click(
            navigate_month_forward,
            inputs=[month_dropdown],
            outputs=[month_dropdown, edit_month_dropdown, flare_evidence, category_dropdown_label, reason_input_label, ctx_label]
        )

        month_dropdown.change(
            update_month_view,
            inputs=[month_dropdown],
            outputs=[monthly_timeline_plot, label_chart_status, current_view_info, edit_month_dropdown,
             flare_evidence, category_dropdown_label, reason_input_label, ctx_label]
        )

        view_back_btn_visible.click(
            lambda month: app.navigate_view(month, "back"),
            inputs=[month_dropdown],
            outputs=[monthly_timeline_plot, label_chart_status, current_view_info_visible]
        )

        view_forward_btn_visible.click(
            lambda month: app.navigate_view(month, "forward"),
            inputs=[month_dropdown],
            outputs=[monthly_timeline_plot, label_chart_status, current_view_info_visible]
        )

        view_back_btn.click(
            lambda month: app.navigate_view(month, "back"),
            inputs=[month_dropdown],
            outputs=[monthly_timeline_plot, label_chart_status, current_view_info]
        )

        view_forward_btn.click(
            lambda month: app.navigate_view(month, "forward"),
            inputs=[month_dropdown],
            outputs=[monthly_timeline_plot, label_chart_status, current_view_info]
        )

        def save_label_and_refresh(month, evidence, categories, reason):
            status, labels_info_txt = app.save_monthly_label(month, evidence, categories, reason)
            if month:
                fig, chart_status_txt, view_info = app.update_monthly_view(month, app.current_view_offset)
                edit_choices = app.get_monthly_labels_list()
                return status, labels_info_txt, fig, gr.update(choices=edit_choices), session_card_html()
            return status, labels_info_txt, None, gr.update(choices=[]), session_card_html()

        def clear_label_and_refresh(month):
            status, labels_info_txt = app.clear_monthly_label(month)
            if month:
                fig, chart_status_txt, view_info = app.update_monthly_view(month, app.current_view_offset)
                edit_choices = app.get_monthly_labels_list()
                return status, labels_info_txt, fig, gr.update(choices=edit_choices), session_card_html()
            return status, labels_info_txt, None, gr.update(choices=[]), session_card_html()

        save_label_btn.click(
            save_label_and_refresh,
            inputs=[month_dropdown, flare_evidence, category_dropdown_label, reason_input_label],
            outputs=[label_chart_status, labels_info, monthly_timeline_plot, edit_month_dropdown, ctx_label]
        )

        clear_label_btn.click(
            clear_label_and_refresh,
            inputs=[month_dropdown],
            outputs=[label_chart_status, labels_info, monthly_timeline_plot, edit_month_dropdown, ctx_label]
        )

        load_edit_btn.click(
            app.load_label_for_edit,
            inputs=[edit_month_dropdown],
            outputs=[flare_evidence, category_dropdown_label, reason_input_label, label_chart_status]
        )

        delete_label_btn.click(
            app.delete_monthly_label,
            inputs=[edit_month_dropdown],
            outputs=[label_chart_status, labels_info]
        ).then(
            lambda month: app.update_monthly_view(month, app.current_view_offset) if month else (None, "No month selected", ""),
            inputs=[month_dropdown],
            outputs=[monthly_timeline_plot, label_chart_status, current_view_info_visible]
        ).then(
            lambda: gr.update(choices=app.get_monthly_labels_list()),
            outputs=[edit_month_dropdown]
        ).then(
            lambda: session_card_html(),
            outputs=[ctx_label]
        )

        # ====================================================================
        # SIDEBAR NAVIGATION — switch pages, active nav highlight, per-page context
        # ====================================================================
        _pages = [page_overview, page_timeline, page_label, page_guide]
        _navs  = [nav_overview, nav_timeline, nav_label, nav_guide]
        # context cards shown per page: overview -> [ctx_overview]
        #   timeline -> [ctx_timeline_patient, ctx_timeline_legend]   label -> [ctx_label]
        _ctx_groups = [
            [ctx_overview],
            [ctx_timeline_patient, ctx_timeline_legend],
            [ctx_label],
            [],
        ]
        _all_ctx = [ctx_overview, ctx_timeline_patient, ctx_timeline_legend, ctx_label]

        def _make_nav(active_idx):
            def _switch():
                page_updates = [gr.update(visible=(i == active_idx)) for i in range(4)]
                nav_updates = [gr.update(variant=("primary" if i == active_idx else "secondary")) for i in range(4)]
                active_ctx = _ctx_groups[active_idx]
                ctx_updates = [gr.update(visible=(c in active_ctx)) for c in _all_ctx]
                return page_updates + nav_updates + ctx_updates
            return _switch

        for _i, _btn in enumerate(_navs):
            _btn.click(_make_nav(_i), outputs=_pages + _navs + _all_ctx)

    return demo

# ============================================================================
# MAIN EXECUTION
# ============================================================================
if __name__ == "__main__":
    app = create_app_with_args()
    add_monthly_labelling_methods(PatientTimelineApp)
    demo = create_interface()
    demo.launch()
