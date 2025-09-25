import pandas as pd

import warnings
warnings.filterwarnings("ignore", message="Discarding nonzero nanoseconds in conversion.", category=UserWarning)

import plotly.express as px
import plotly.graph_objects as go
import json
import os
import textwrap
from datetime import datetime, timedelta
import numpy as np
import random


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
    
    def __init__(self, patient_range=None, group_name="Default"):
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
        
        # === UI State Management ===
        self.editing_flare_index = None    # Index of flare currently being edited (for future use)
        
        # === Patient Access Control ===
        # These settings control which patients this app instance can access
        self.patient_range = patient_range  # (start_id, end_id) tuple or None for all patients
        self.group_name = group_name       # Display name for this patient group
        
        # === Navigation State ===
        # Used in labeling mode to track view offset from selected month
        self.current_view_offset = 0       # Integer offset for month navigation
        
        # === Initialization ===
        # Automatically load data when app starts
        self.auto_load_data()
    
    def auto_load_data(self):
        """
        Automatically load patient data from the specified directory.
        
        This method attempts to load data from a predefined CSV file. If the file
        is not found or cannot be loaded, it falls back to generating sample data
        for testing purposes.
        
        File Location: /data/external_ps/baumgart/BAUMGART_SHARED/Baumgart_IBD/Sacha/ibd_activity_viewer/data/
        Target File: selected_events_mia_patients.csv
        
        Expected CSV Format:
        - patient_id: Integer patient identifier
        - start_date: Event start date (YYYY-MM-DD)
        - end_date: Event end date (YYYY-MM-DD)
        - event_type: Type of medical event (string)
        - ibd_related: Boolean flag for IBD-related events
        - event_info: JSON string with additional event details
        - source_dataset: Data source identifier
        """
        try:
            # === Define Data Location ===
            # Set the repository path and data directory
            # repo_path = '/data/external_ps/baumgart/BAUMGART_SHARED/Baumgart_IBD/Sacha/ibd_activity_viewer'
            data_dir =  "patient_data" # os.path.join(repo_path, 'data')
            
            # Specific file to load (can be modified to load different files)
            target_file = 'selected_patient_events.csv'
            file_path = os.path.join(data_dir, target_file)
            
            # === Check File Existence ===
            if not os.path.exists(file_path):
                print(f"Target file not found: {file_path}")
                print("Falling back to sample data generation...")
                # Generate fake data for testing if real data is not available
                self.combined_data = self.generate_fake_data(1000)
                self.apply_patient_filter()
                return
            
            # === Load Real Data ===
            try:
                print(f"Loading: {target_file}")
                df = pd.read_csv(file_path)
                
                # Convert date columns to pandas datetime objects for proper date handling
                df['start_date'] = pd.to_datetime(df['start_date'])
                df['end_date'] = pd.to_datetime(df['end_date'])
                
                self.combined_data = df
                print(f"Successfully loaded {len(self.combined_data)} records from {target_file}")
                
                # Apply patient filtering based on command line arguments
                self.apply_patient_filter()
                
            except Exception as e:
                print(f"Error loading {target_file}: {e}")
                print("Falling back to sample data generation...")
                # If CSV loading fails, generate sample data
                self.combined_data = self.generate_fake_data(1000)
                self.apply_patient_filter()
                
        except Exception as e:
            print(f"Error auto-loading data: {e}")
            print("Falling back to sample data generation...")
            # Final fallback to sample data
            self.combined_data = self.generate_fake_data(1000)
            self.apply_patient_filter()
    
    def apply_patient_filter(self):
        """
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
    
    def generate_fake_data(self, num_rows=1000):
        """
        Generate fake patient data for testing/demonstration purposes.
        
        This method creates realistic-looking medical event data when real data
        is not available. The generated data includes various event types,
        realistic date ranges, and JSON-formatted event information.
        
        Args:
            num_rows (int): Approximate number of total events to generate
        
        Returns:
            pd.DataFrame: Generated patient event data with required columns
        """
        # === Generate Patient IDs ===
        # Create unique patient IDs (about 50 events per patient on average)
        unique_patient_ids = np.random.randint(1, 1000, size=num_rows // 50)
        
        # === Generate Event Counts Per Patient ===
        # Each patient gets a random number of events between 50-100
        patient_event_counts = {patient_id: random.randint(50, 100) for patient_id in unique_patient_ids}
        
        # === Generate Events for Each Patient ===
        data = []
        for patient_id, event_count in patient_event_counts.items():
            # === Generate Random Dates ===
            # Create events within a realistic timeframe (2010-2022)
            start_date_2010 = datetime(2010, 1, 1)
            end_date_2022 = datetime(2022, 12, 31)
            date_range_days = (end_date_2022 - start_date_2010).days

            # Generate random start dates within the range
            start_dates = [start_date_2010 + timedelta(days=random.randint(0, date_range_days)) for _ in range(event_count)]
            # Generate end dates (0-10 days after start date)
            end_dates = [start_date + timedelta(days=random.randint(0, 10)) for start_date in start_dates]

            # === Ensure End Dates Don't Exceed Range ===
            for i, end_date in enumerate(end_dates):
                if end_date > end_date_2022:
                    end_dates[i] = end_date_2022
            
            # === Generate Random Event Types ===
            # These should match the real event types in your actual data
            event_types = random.choices(
                ['imaging', 'ambulatory_visit', 'hospitalization', 'medication_change', 'lab_test'], 
                k=event_count
            )
            
            # === Generate IBD-Related Flags ===
            # Random boolean flags for IBD-related events
            ibd_related = random.choices([True, False], k=event_count)
            
            # === Generate Event Information ===
            # Create JSON strings with additional event details (mimics real data structure)
            event_info = [
                json.dumps({
                    "Patient Age": random.randint(1, 100),
                    "Patient Sex": random.choice(["Male", "Female"]),
                    "Additional Info": f"Info {i}"
                }) for i in range(event_count)
            ]
            
            # === Generate Source Datasets ===
            # Random data source identifiers (should match your real data sources)
            source_datasets = random.choices(['DI', 'DAD', 'CLAIMS', 'PIN', 'LAB', 'NACRS'], k=event_count)
            
            # === Create Event Records ===
            # Append data for this patient
            for i in range(event_count):
                data.append({
                    'patient_id': patient_id,
                    'start_date': start_dates[i],
                    'end_date': end_dates[i],
                    'event_type': event_types[i],
                    'ibd_related': ibd_related[i],
                    'event_info': event_info[i],
                    'source_dataset': source_datasets[i]
                })
        
        # === Return DataFrame ===
        fake_data = pd.DataFrame(data)
        return fake_data
    
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
        Get chart information text for display in the UI.
        
        This method generates a comprehensive summary of the current patient's
        data, including event counts, date ranges, and flare information.
        It combines information from both date-based flares and monthly labels.
        
        Returns:
            str: Formatted information text for display
        """
        if self.current_patient_data is None:
            return "No patient data loaded"
        
        # === Import Label Mapping ===
        # Get the mapping from internal event names to readable display names
        from timeline_visualization import get_label_mapping
        label_mapping = get_label_mapping()
        
        # === Basic Patient Information ===
        info = f"Patient ID: {self.current_patient_id}\n"
        info += f"Total Events: {len(self.current_patient_data)}\n"
        info += f"Date Range: {self.current_patient_data['start_date'].min().date()} to {self.current_patient_data['end_date'].max().date()}\n\n"
        
        # === Event Type Summary ===
        info += "Event Types:\n"
        event_counts = self.current_patient_data['event_type'].value_counts()
        for event_type, count in event_counts.items():
            # Convert internal event names to readable format
            readable_name = label_mapping.get(event_type, event_type.replace('_', ' ').title())
            info += f"  {readable_name}: {count}\n"
        
        # === Date-Based Flare Periods ===
        # These are flares marked using the date range selection method
        info += f"\nDate-based Flares: {len(self.ranges)}\n"
        for i, flare_data in enumerate(self.ranges):
            # === Handle Both Old and New Flare Formats ===
            if len(flare_data) == 3:  # Old format: (start, end, reason)
                start_date, end_date, reason = flare_data
                categories = []
            else:  # New format: (start, end, categories, reason)
                start_date, end_date, categories, reason = flare_data
            
            # === Format Flare Information ===
            info += f"  {i+1}. {pd.to_datetime(start_date).date()} to {pd.to_datetime(end_date).date()}"
            
            # Add categories if available
            if categories:
                readable_categories = [label_mapping.get(cat, cat.replace('_', ' ').title()) for cat in categories]
                info += f" ({', '.join(readable_categories)})"
            
            # Add reason if available
            if reason:
                info += f": {reason}"
            
            info += "\n"
        
        # === Monthly Flares from Labelling Mode ===
        # These are flares marked using the monthly labelling interface
        monthly_labels = self.load_monthly_labels()
        # Filter to only show months marked as having evidence of flares
        monthly_flares = {k: v for k, v in monthly_labels.items() if v.get('evidence') == 'Yes'}
        
        info += f"\nMonthly Flares: {len(monthly_flares)}\n"
        for month_period_str, label_data in sorted(monthly_flares.items()):
            try:
                # === Format Monthly Flare Information ===
                period = pd.Period(month_period_str)
                month_str = period.strftime('%B %Y')
                info += f"  • {month_str}"
                
                # === Add Categories if Available ===
                categories = label_data.get('categories', [])
                if categories:
                    readable_categories = [label_mapping.get(cat, cat.replace('_', ' ').title()) for cat in categories]
                    info += f" ({', '.join(readable_categories)})"
                
                # === Add Reason if Available ===
                reason = label_data.get('reason', '')
                if reason:
                    info += f": {reason}"
                
                info += "\n"
                
            except Exception as e:
                print(f"Error formatting monthly flare: {e}")
                continue
        
        return info