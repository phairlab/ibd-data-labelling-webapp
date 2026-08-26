import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import textwrap
from datetime import datetime, timezone
import yaml
from rmt23345_events import load_all_events


def _load_study_config(config_path: str = "study_config.yaml") -> dict:
    """Load study_config.yaml if it exists; return empty dict otherwise."""
    try:
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"[study_config] Warning: could not read {config_path}: {e}")
        return {}


class PatientTimelineApp:
    """
    Main application class for the Patient Timeline Viewer.
    
    This class manages patient medical event data, provides timeline visualizations,
    and allows doctors to mark flare periods in IBD patients. The app supports
    both date-based flare marking and monthly flare labeling.
    Key Features:
    - Load and filter patient medical event data
    - Create interactive timeline visualizations
    - Mark and save flare periods (date-based and monthly)
    - Support for different patient access groups
    - Export functionality for data and charts
    """
    
    def __init__(self, patient_range=None, group_name="Default", rmt23345_data_dir=None):
        """
        Initialize the Patient Timeline App.
        
        Args:
            patient_range (tuple, optional): (start_id, end_id) for patient filtering
            group_name (str): Name of the patient group for display purposes
        """
        # === Data Storage ===
        self.combined_data = None          # Main dataset containing all patient events
        self.current_patient_data = None   # Filtered data for currently selected patient
        self.current_patient_id = None     # ID of currently selected patient
        self.ranges = []                   # List of date-based flare periods: [(start_date, end_date, categories, reason), ...]
        self.fig = None                    # Current plotly figure object
        self.last_loaded_utc = None        # UTC datetime of the most recent successful data load
        
        # === UI State Management ===
        self.editing_flare_index = None    # Index of flare currently being edited (for future use)
        
        # === Patient Access Control ===
        # These settings control which patients this app instance can access
        self.patient_range = patient_range  # (start_id, end_id) tuple or None for all patients
        self.group_name = group_name       # Display name for this patient group

        # === RMT23345 Data Directory ===
        # If set, load events from cleaned RMT23345 CSVs instead of the default CSV
        self.rmt23345_data_dir = rmt23345_data_dir
        
        # === Navigation State ===
        # Used in labeling mode to track view offset from selected month
        self.current_view_offset = 0       # Integer offset for month navigation
        
        # === Initialization ===
        # Automatically load data when app starts
        self.auto_load_data()
    
    def auto_load_data(self):
        """
        Load patient data from the RMT23345 directory if one was specified.
        If no directory is given, combined_data stays None — the user must
        either provide --rmt23345-dir at startup or upload files via the UI.
        """
        if self.rmt23345_data_dir and os.path.isdir(self.rmt23345_data_dir):
            try:
                study_config = _load_study_config()
                if study_config:
                    enabled = study_config.get("sources", {}).get("enabled", [])
                    print(f"study_config.yaml: loading sources {enabled}")
                print(f"Loading from RMT23345 directory: {self.rmt23345_data_dir}")
                df = load_all_events(self.rmt23345_data_dir, config=study_config)
                if len(df) > 0:
                    df['start_date'] = pd.to_datetime(df['start_date'], utc=True, errors='coerce').dt.tz_localize(None)
                    df['end_date']   = pd.to_datetime(df['end_date'],   utc=True, errors='coerce').dt.tz_localize(None)
                    self.combined_data = df
                    self.last_loaded_utc = datetime.now(timezone.utc)
                    print(f"Loaded {len(df)} events from RMT23345 CSVs")
                    self.apply_patient_filter()
                else:
                    print("No events found in the specified directory.")
            except Exception as e:
                print(f"Failed to load RMT23345 data: {e}")
        else:
            print("No data directory specified. Use --rmt23345-dir")
    
    def apply_patient_filter(self):
        """no but my 
        Apply patient range filtering based on command line arguments.
        
        This method filters the loaded data to only include patients within
        the specified ID range. This is used for access control - different
        users/groups can be given access to different patient cohorts.
        
        The filtering is applied after data loading and logs the filtering results.
        """
        if self.combined_data is not None and self.patient_range is not None:
            start_id, end_id = self.patient_range
            
            # === Record Original Data Stats ===
            original_count = len(self.combined_data)
            original_patients = len(self.combined_data['patient_id'].unique())
            
            # === Apply Patient ID Filter ===
            # Filter to only include patients in the specified range
            self.combined_data = self.combined_data[
                (self.combined_data['patient_id'] >= start_id) & 
                (self.combined_data['patient_id'] <= end_id)
            ].copy()
            
            # === Record Filtered Data Stats ===
            filtered_count = len(self.combined_data)
            filtered_patients = len(self.combined_data['patient_id'].unique()) if filtered_count > 0 else 0
            
            # === Log Filtering Results ===
            print(f"Patient filtering applied ({self.group_name}):")
            print(f"  Range: Patient IDs {start_id} to {end_id}")
            print(f"  Records: {original_count} → {filtered_count}")
            print(f"  Patients: {original_patients} → {filtered_patients}")
    
    def get_data_status(self):
        """
        Get current data loading status for display in the UI.
        
        Returns:
            str: Formatted status string showing data loading state,
                 number of records, patients, and ID range if applicable
        """
        if self.combined_data is not None:
            patient_count = len(self.combined_data['patient_id'].unique())
            if self.patient_range:
                start_id, end_id = self.patient_range
                return f"Data loaded ({self.group_name}): {len(self.combined_data)} records for {patient_count} patients (IDs {start_id}-{end_id})"
            else:
                return f"Data loaded: {len(self.combined_data)} records for {patient_count} patients"
        else:
            return "No data loaded"
    
    def get_last_loaded_str(self):
        """UTC timestamp of the most recent successful data load, for display in the UI."""
        if self.last_loaded_utc is None:
            return "Never"
        return self.last_loaded_utc.strftime("%Y-%m-%d %H:%M UTC")

    def get_patient_choices(self):
        """
        Get list of available patient IDs for dropdown selection.
        
        Returns:
            list: List of patient IDs as strings, sorted numerically
        """
        if self.combined_data is not None:
            patient_ids = sorted(self.combined_data['patient_id'].unique())
            return [str(pid) for pid in patient_ids]
        else:
            return []
    
    def reload_data(self):
        """
        Reload data from the directory and update UI components.
        
        This method is called when the user clicks the "Reload Data" button.
        It re-runs the data loading process and updates the UI with new data.
        
        Returns:
            tuple: (status_message, updated_dropdown, status_for_chart_info)
        """
        import gradio as gr
        self.auto_load_data()
        patient_choices = self.get_patient_choices()
        status = self.get_data_status()
        return status, gr.update(choices=patient_choices, value=patient_choices[0] if patient_choices else None), status
    
    def export_data(self, format_choice):
        """
        Export current data to CSV or Excel format.
        
        Args:
            format_choice (str): Either "CSV" or "Excel"
            
        Returns:
            str: Status message indicating export success or failure
        """
        if self.combined_data is None:
            return "No data to export"
        
        try:
            # === Generate Timestamped Filename ===
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if format_choice == "CSV":
                filename = f"patient_data_{timestamp}.csv"
                self.combined_data.to_csv(filename, index=False)
            else:  # Excel
                filename = f"patient_data_{timestamp}.xlsx"
                self.combined_data.to_excel(filename, index=False)
            
            return f"Data exported to {filename}"
            
        except Exception as e:
            return f"Failed to export data: {str(e)}"
    
    def load_config_file(self, config_file):
        """
        Accept an uploaded study_config.yaml, read it, and load data from
        the file paths specified in its sources section. Paths may be absolute
        (pointing anywhere on the server) or relative (resolved against data_dir).

        Returns:
            tuple: (status_msg, data_status, patient_dropdown_update, chart_info)
        """
        import gradio as gr

        if config_file is None:
            return (
                "No config file selected.",
                self.get_data_status(),
                gr.update(),
                self.get_data_status(),
            )

        src = config_file if isinstance(config_file, str) else config_file.name

        try:
            with open(src, 'r') as f:
                uploaded_config = yaml.safe_load(f) or {}
        except Exception as e:
            return (
                f"Failed to read config file: {e}",
                self.get_data_status(),
                gr.update(),
                self.get_data_status(),
            )

        try:
            df = load_all_events(data_dir=self.rmt23345_data_dir, config=uploaded_config)
            if len(df) == 0:
                return (
                    "Config loaded but no events found. Check that the file paths in your YAML exist on this server.",
                    self.get_data_status(),
                    gr.update(),
                    self.get_data_status(),
                )
            df['start_date'] = pd.to_datetime(df['start_date'], utc=True, errors='coerce').dt.tz_localize(None)
            df['end_date']   = pd.to_datetime(df['end_date'],   utc=True, errors='coerce').dt.tz_localize(None)
            self.combined_data = df
            self.last_loaded_utc = datetime.now(timezone.utc)
            self.apply_patient_filter()
        except Exception as e:
            return (
                f"Error loading data from config: {e}",
                self.get_data_status(),
                gr.update(),
                self.get_data_status(),
            )

        patient_choices = self.get_patient_choices()
        data_status     = self.get_data_status()
        return (
            f"Loaded {len(self.combined_data):,} events for {len(patient_choices)} patients.",
            data_status,
            gr.update(choices=patient_choices, value=patient_choices[0] if patient_choices else None),
            data_status,
        )

    def load_patient_timeline(self, patient_id, ibd_filter="All Events"):
        """
        Load timeline for selected patient with IBD filtering.
        
        This is the main method for the Timeline Viewer tab. It loads data for
        a specific patient, applies IBD filtering, loads existing flares, and
        creates the timeline visualization.
        
        Args:
            patient_id (str): Patient ID to load
            ibd_filter (str): Filter type - "All Events", "IBD Related Only", or "Non-IBD Related Only"
            
        Returns:
            tuple: (plotly_figure, status_message, chart_info_text)
        """
        # === Validation ===
        if self.combined_data is None:
            return None, "Please load patient data first", ""
        
        if not patient_id:
            return None, "Please select a patient ID", ""
        
        try:
            # === Filter Data for Selected Patient ===
            patient_data = self.combined_data[
                self.combined_data['patient_id'] == int(patient_id)
            ].copy()
            
            # === Apply IBD Filtering ===
            # Filter events based on IBD-related flag
            if ibd_filter == "IBD Related Only":
                patient_data = patient_data[patient_data['ibd_related'] == True]
            elif ibd_filter == "Non-IBD Related Only":
                patient_data = patient_data[patient_data['ibd_related'] == False]
            # "All Events" requires no additional filtering
            
            # === Update Instance State ===
            self.current_patient_data = patient_data
            self.current_patient_id = int(patient_id)
            
            # === Load Existing Flare Data ===
            # Load any previously saved flare periods for this patient
            self.load_existing_flares()
            
            # === Create Timeline Visualization ===
            fig = self.create_timeline()
            info = self.get_chart_info()
            
            status_msg = f"Chart loaded for Patient {self.current_patient_id} ({ibd_filter})"
            
            return fig, status_msg, info
            
        except Exception as e:
            return None, f"Failed to load patient timeline: {str(e)}", ""
    
    def load_existing_flares(self):
        """
        Load existing flare periods from JSON file.
        
        Each patient's flare data is saved in a separate JSON file named
        'patient_{patient_id}_flares.json'. This method loads and parses
        that data, handling both old and new format flare records.
        
        Flare Format:
        - Old: {start_date, end_date, reason}
        - New: {start_date, end_date, categories, reason}
        """
        save_file = f'patient_{self.current_patient_id}_flares.json'
        self.ranges = []  # Reset flare list
        
        if os.path.exists(save_file):
            try:
                with open(save_file, 'r') as f:
                    saved_ranges = json.load(f)
                    
                    # === Parse Each Flare Record ===
                    for flare in saved_ranges:
                        flare_start = pd.to_datetime(flare['start_date'])
                        flare_end = pd.to_datetime(flare['end_date'])
                        
                        # === Handle Format Compatibility ===
                        # Support both old format (without categories) and new format (with categories)
                        if 'categories' in flare:
                            # New format with categories
                            categories = flare['categories']
                            reason = flare.get('reason', '')
                            self.ranges.append((flare_start, flare_end, categories, reason))
                        else:
                            # Old format compatibility - add empty categories
                            reason = flare.get('reason', '')
                            self.ranges.append((flare_start, flare_end, [], reason))
                            
            except Exception as e:
                print(f"Error loading flares: {e}")
    
    def load_patient_for_labelling(self, patient_id):
        """
        Load patient for labelling mode.
        
        This method prepares a patient's data for the monthly labelling interface.
        Unlike the timeline viewer, this loads ALL events (no IBD filtering) and
        prepares the month navigation system.
        
        Args:
            patient_id (str): Patient ID to load for labelling
            
        Returns:
            tuple: (status_message, month_dropdown_update, view_info, labels_info)
        """
        import gradio as gr
        if self.combined_data is None:
            return "Please load patient data first", gr.update(choices=[]), "", ""
        
        if not patient_id:
            return "Please select a patient ID", gr.update(choices=[]), "", ""
        
        try:
            # === Filter Data for Selected Patient ===
            # Load ALL events for labelling (no IBD filtering in labelling mode)
            patient_data = self.combined_data[
                self.combined_data['patient_id'] == int(patient_id)
            ].copy()
            
            # === Update Instance State ===
            self.current_patient_data = patient_data
            self.current_patient_id = int(patient_id)
            
            # === Reset Navigation State ===
            # Reset view offset when loading new patient
            self.current_view_offset = 0
            
            # === Get Available Months ===
            month_choices = self.get_patient_months()
            
            status_msg = f"Patient {self.current_patient_id} loaded for labelling"
            
            return status_msg, gr.update(choices=month_choices, value=month_choices[0] if month_choices else None), "", ""
            
        except Exception as e:
            return f"Failed to load patient: {str(e)}", gr.update(choices=[]), "", ""
    
    def get_patient_months(self):
        """
        Get list of available months for selected patient - ONLY months with events.
        
        This method identifies all months that contain at least one medical event
        for the current patient. It's used in the labelling mode to populate the
        month selection dropdown with only relevant months.
        
        For events that span multiple months, all months in the span are included.
        
        Returns:
            list: List of month strings in "Month YYYY" format (e.g., "January 2020")
        """
        if self.current_patient_data is None or len(self.current_patient_data) == 0:
            return []
        
        # === Collect Months with Events ===
        months_with_events = set()
        
        for _, row in self.current_patient_data.iterrows():
            # === Add Start Date Month ===
            start_month = row['start_date'].to_period('M')
            months_with_events.add(start_month)
            
            # === Add End Date Month ===
            # (if different from start month)
            end_month = row['end_date'].to_period('M')
            months_with_events.add(end_month)
            
            # === Add Months for Multi-Month Events ===
            # For events spanning multiple months, add all months in between
            if start_month != end_month:
                current_month = start_month
                while current_month <= end_month:
                    months_with_events.add(current_month)
                    current_month += 1
        
        # === Sort and Format Months ===
        months_sorted = sorted(months_with_events)
        
        # Convert to readable format: "January 2020", "February 2020", etc.
        month_strings = [f"{month.strftime('%B %Y')}" for month in months_sorted]
        return month_strings
    
    def get_all_patient_months(self):
        """
        Get list of ALL available months for selected patient - including empty months.
        
        This method generates all months between the first and last events,
        including months with no events. This is useful for comprehensive
        labelling where empty months might also need to be labeled.
        
        Returns:
            list: List of month strings including months without events
        """
        if self.current_patient_data is None or len(self.current_patient_data) == 0:
            return []
        
        # === Get Full Date Range ===
        min_date = self.current_patient_data['start_date'].min()
        max_date = self.current_patient_data['end_date'].max()
        
        # === Generate All Months in Range ===
        start_month = min_date.to_period('M')
        end_month = max_date.to_period('M')
        
        all_months = []
        current_month = start_month
        while current_month <= end_month:
            all_months.append(current_month)
            current_month += 1
        
        # === Format as Readable Strings ===
        month_strings = [f"{month.strftime('%B %Y')}" for month in all_months]
        return month_strings
    
    def navigate_month(self, current_month, direction):
        """
        Navigate to previous or next month - ONLY months with events.
        
        This method handles month navigation in the labelling interface,
        moving between months that actually contain medical events.
        
        Args:
            current_month (str): Currently selected month in "Month YYYY" format
            direction (str): "back" or "forward"
            
        Returns:
            str: New month selection or current month if navigation not possible
        """
        if not current_month:
            return current_month
        
        try:
            # === Get Available Months ===
            # Only get months with events for navigation
            month_choices = self.get_patient_months()
            
            # === Handle Month Not in List ===
            if current_month not in month_choices:
                # If current month is not in the filtered list, return the first available month
                return month_choices[0] if month_choices else None
            
            # === Navigate Between Months ===
            current_index = month_choices.index(current_month)
            
            if direction == "back" and current_index > 0:
                return month_choices[current_index - 1]
            elif direction == "forward" and current_index < len(month_choices) - 1:
                return month_choices[current_index + 1]
            else:
                # Can't navigate further in that direction
                return current_month
                
        except Exception as e:
            print(f"Error navigating month: {e}")
            return current_month
    
    def update_monthly_view(self, selected_month, view_offset=0):
        """
        Update the monthly timeline view - can show empty months.
        
        This method creates the monthly timeline visualization. The selected_month
        is what the user is labelling, while the view can be offset to show
        adjacent months for context.
        
        Args:
            selected_month (str): Month being labeled ("Month YYYY" format)
            view_offset (int): Offset from selected month for viewing (-1, 0, +1, etc.)
            
        Returns:
            tuple: (plotly_figure, status_message, view_month_string)
        """
        if not selected_month:
            return None, "No month selected", ""
        
        try:
            # === Import Timeline Creation Function ===
            # This function is defined in a separate module for better organization
            from timeline_visualization import create_monthly_timeline
            fig = create_monthly_timeline(self, selected_month, view_offset)
            
            # === Calculate Current View Month ===
            selected_period = pd.to_datetime(selected_month, format='%B %Y').to_period('M')
            view_period = selected_period + view_offset
            view_month_str = view_period.strftime('%B %Y')
            
            if fig:
                # === Check if View Month Has Events ===
                event_months = self.get_patient_months()
                
                # === Create Status Message ===
                if view_month_str in event_months:
                    status_msg = f"Showing timeline for {view_month_str} (Labelling: {selected_month})"
                else:
                    # Indicate when viewing a month with no events
                    status_msg = f"Showing timeline for {view_month_str} (NO EVENTS - Labelling: {selected_month})"
                
                return fig, status_msg, view_month_str
            else:
                return None, f"No data available for {view_month_str}", view_month_str
                
        except Exception as e:
            return None, f"Failed to update view: {str(e)}", ""
    
    def navigate_view(self, selected_month, direction):
        """
        Navigate the view forward or backward - can view ALL months including empty ones.
        
        This method changes which month is displayed in the timeline while keeping
        the same month selected for labelling. Users can view context around the
        month they're labelling.
        
        Args:
            selected_month (str): Month currently selected for labelling
            direction (str): "back" or "forward"
            
        Returns:
            tuple: (plotly_figure, status_message, view_month_string)
        """
        # === Update View Offset ===
        if direction == "back":
            self.current_view_offset -= 1
        elif direction == "forward":
            self.current_view_offset += 1
        
        # === Update View with New Offset ===
        return self.update_monthly_view(selected_month, self.current_view_offset)
    
    def create_timeline(self):
        """
        Create the plotly timeline figure.
        
        This method delegates to an external function for creating the main
        timeline visualization. The actual implementation is in timeline_visualization.py
        for better code organization.
        
        Returns:
            plotly.graph_objects.Figure: The timeline chart
        """
        from timeline_visualization import create_main_timeline
        return create_main_timeline(self)
    
    def get_chart_info(self):
        """
        Get chart information as a structured HTML card for display in the UI.

        Shows total events, date range, and a monthly-flare count as labelled
        fields, matching the styling of the other info cards (patient panel /
        event counts / flare periods). The actual flare-by-flare breakdown
        (date-based and monthly) lives in the Flare Periods card instead —
        repeating that full list here was redundant, so this card just gives
        the count. The event-type breakdown is left out too, since it's
        already shown in the adjacent Event Counts card in the same grid.

        Returns:
            str: HTML for the Chart Information card.
        """
        from html import escape

        _info_icon = ("<svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' "
                      "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
                      "<circle cx='12' cy='12' r='9'/><line x1='12' y1='11' x2='12' y2='16'/>"
                      "<circle cx='12' cy='7.5' r='0.75' fill='currentColor' stroke='none'/></svg>")

        if self.current_patient_data is None:
            return (f"<div class='ui-card'><div class='card-title'>"
                    f"<span class='icon-chip'>{_info_icon}</span>Chart information</div>"
                    f"<div class='muted'>No patient data loaded</div></div>")

        total_events = len(self.current_patient_data)
        date_range = (f"{self.current_patient_data['start_date'].min().date()} "
                      f"to {self.current_patient_data['end_date'].max().date()}")

        monthly_labels = self.load_monthly_labels()
        monthly_flare_count = sum(1 for v in monthly_labels.values() if v.get('evidence') == 'Yes')

        body = (
            f"<div class='info-row'><span>Total events</span><span>{total_events:,}</span></div>"
            f"<div class='info-row'><span>Date range</span><span>{escape(date_range)}</span></div>"
            f"<div class='info-row'><span>Monthly flares</span><span class='count'>{monthly_flare_count}</span></div>"
        )

        return (f"<div class='ui-card'><div class='card-title'>"
                f"<span class='icon-chip'>{_info_icon}</span>Chart information</div>"
                f"{body}</div>")

    def load_patient_timeline_html(self, patient_id):
        """
        Load timeline as client-side HTML/JS (Plotly.js) — no IBD filter round-trip.

        Returns:
            tuple: (html_string, status_message, chart_info_text)
        """
        if self.combined_data is None:
            placeholder = "<p style='color:#6b7280;padding:20px;'>Please load patient data first.</p>"
            return placeholder, "Please load patient data first", ""

        if not patient_id:
            placeholder = "<p style='color:#6b7280;padding:20px;'>Please select a patient ID.</p>"
            return placeholder, "Please select a patient ID", ""

        try:
            try:
                pid = int(patient_id)
            except (ValueError, TypeError):
                pid = patient_id

            patient_data = self.combined_data[
                self.combined_data['patient_id'].astype(str) == str(pid)
            ].copy()

            self.current_patient_data = patient_data
            self.current_patient_id   = pid
            self.load_existing_flares()

            from timeline_visualization import build_timeline_html
            html   = build_timeline_html(self)
            info   = self.get_chart_info()
            status = f"Chart loaded for Patient {self.current_patient_id}: filter using the buttons above the chart"
            return html, status, info

        except Exception as e:
            err_html = f"<p style='color:#ef4444;padding:20px;'>Error: {str(e)}</p>"
            return err_html, f"Failed to load patient timeline: {str(e)}", ""

    # ========================================================================
    # UI HELPER METHODS (read-only) — power the stat tiles / cards / panels
    # in the redesigned UI. These do not change any loading/saving logic,
    # they just summarize data that is already loaded.
    # ========================================================================

    def get_overview_stats(self):
        """Aggregate stats across the whole loaded dataset, for the Data Overview tiles."""
        if self.combined_data is None or len(self.combined_data) == 0:
            return {"total_records": 0, "patients": 0, "ibd_pct": 0,
                    "date_range_years": 0, "avg_per_patient": 0,
                    "date_min": None, "date_max": None}
        df = self.combined_data
        total = len(df)
        patients = df['patient_id'].nunique()
        ibd_pct = round(100 * df['ibd_related'].mean()) if 'ibd_related' in df.columns else 0
        span_days = (df['end_date'].max() - df['start_date'].min()).days
        years = round(span_days / 365.25, 1) if span_days > 0 else 0
        avg = round(total / patients, 1) if patients else 0
        return {"total_records": total, "patients": patients, "ibd_pct": ibd_pct,
                "date_range_years": years, "avg_per_patient": avg,
                "date_min": df['start_date'].min().date(), "date_max": df['end_date'].max().date()}

    def get_event_breakdown(self, df=None):
        """Event-type counts (dataset-wide by default), using readable display names."""
        from timeline_visualization import get_label_mapping
        mapping = get_label_mapping()
        data = df if df is not None else self.combined_data
        if data is None or len(data) == 0:
            return []
        counts = data['event_type'].value_counts()
        return [(mapping.get(et, str(et).replace('_', ' ').title()), int(c)) for et, c in counts.items()]

    def get_patient_panel_stats(self):
        """Summary stats for the currently loaded patient, for the Timeline Viewer side panel."""
        if self.current_patient_data is None or len(self.current_patient_data) == 0:
            return None
        df = self.current_patient_data
        records = len(df)
        span_days = (df['end_date'].max() - df['start_date'].min()).days
        years = round(span_days / 365.25, 1) if span_days > 0 else 0
        ibd_pct = round(100 * df['ibd_related'].mean()) if 'ibd_related' in df.columns else 0
        monthly_labels = self.load_monthly_labels() if hasattr(self, 'load_monthly_labels') else {}
        monthly_flare_count = sum(1 for v in monthly_labels.values() if v.get('evidence') == 'Yes')
        flares = len(self.ranges) + monthly_flare_count
        return {"patient_id": self.current_patient_id, "records": records,
                "followup_years": years, "ibd_pct": ibd_pct, "flares": flares}

    def get_flare_periods_list(self):
        """Combine date-based flares + monthly 'Yes' flares into one sorted list for display."""
        entries = []
        for flare_data in self.ranges:
            if len(flare_data) == 3:
                start, end, reason = flare_data
                categories = []
            else:
                start, end, categories, reason = flare_data
            start_ts = pd.to_datetime(start)
            label = categories[0].replace('_', ' ').title() if categories else (reason or "Flare")
            entries.append({"sort": start_ts, "date_str": start_ts.strftime('%b %Y'), "label": label})

        monthly_labels = self.load_monthly_labels() if hasattr(self, 'load_monthly_labels') else {}
        for month_period_str, label_data in monthly_labels.items():
            if label_data.get('evidence') != 'Yes':
                continue
            try:
                period = pd.Period(month_period_str)
                cats = label_data.get('categories', [])
                label = cats[0].replace('_', ' ').title() if cats else "Flare"
                entries.append({"sort": period.to_timestamp(), "date_str": period.strftime('%b %Y'), "label": label})
            except Exception:
                continue

        entries.sort(key=lambda e: e["sort"])
        return entries

    def get_labelling_progress(self):
        """Labelling completion stats for the current patient, for the sidebar session card."""
        if self.current_patient_data is None:
            return {"labelled": 0, "total": 0, "flares": 0, "no_flare": 0}
        total = len(self.get_all_patient_months())
        monthly_labels = self.load_monthly_labels() if hasattr(self, 'load_monthly_labels') else {}
        labelled = len(monthly_labels)
        flares = sum(1 for v in monthly_labels.values() if v.get('evidence') == 'Yes')
        no_flare = labelled - flares
        return {"labelled": labelled, "total": total, "flares": flares, "no_flare": no_flare}