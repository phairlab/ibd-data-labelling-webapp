import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import textwrap
from datetime import datetime, timedelta
import numpy as np
import random


class PatientTimelineApp:
    def __init__(self, patient_range=None, group_name="Default"):
        # Data storage
        self.combined_data = None
        self.current_patient_data = None
        self.current_patient_id = None
        self.ranges = []  # Store flare periods
        self.fig = None
        
        # State for editing flares
        self.editing_flare_index = None
        
        # Patient filtering settings
        self.patient_range = patient_range
        self.group_name = group_name
        
        # Navigation state
        self.current_view_offset = 0
        
        # Auto-load data on initialization
        self.auto_load_data()
    
    def auto_load_data(self):
        """Automatically load data from the specified directory"""
        try:
            # Set the repository path and data directory
            repo_path = '/data/external_ps/baumgart/BAUMGART_SHARED/Baumgart_IBD/Sacha/ibd_activity_viewer'
            data_dir = os.path.join(repo_path, 'data')
            
            # Specific file to load
            target_file = 'selected_events_mia_patients.csv'
            file_path = os.path.join(data_dir, target_file)
            
            # Check if the specific file exists
            if not os.path.exists(file_path):
                print(f"Target file not found: {file_path}")
                print("Falling back to sample data generation...")
                self.combined_data = self.generate_fake_data(1000)
                self.apply_patient_filter()
                return
            
            try:
                # Load the specific CSV file
                print(f"Loading: {target_file}")
                df = pd.read_csv(file_path)
                df['start_date'] = pd.to_datetime(df['start_date'])
                df['end_date'] = pd.to_datetime(df['end_date'])
                
                self.combined_data = df
                print(f"Successfully loaded {len(self.combined_data)} records from {target_file}")
                
                # Apply patient filtering based on command line arguments
                self.apply_patient_filter()
                
            except Exception as e:
                print(f"Error loading {target_file}: {e}")
                print("Falling back to sample data generation...")
                self.combined_data = self.generate_fake_data(1000)
                self.apply_patient_filter()
                
        except Exception as e:
            print(f"Error auto-loading data: {e}")
            print("Falling back to sample data generation...")
            self.combined_data = self.generate_fake_data(1000)
            self.apply_patient_filter()
    
    def apply_patient_filter(self):
        """Apply patient range filtering based on command line arguments"""
        if self.combined_data is not None and self.patient_range is not None:
            start_id, end_id = self.patient_range
            original_count = len(self.combined_data)
            original_patients = len(self.combined_data['patient_id'].unique())
            
            # Filter to only include patients in the specified range
            self.combined_data = self.combined_data[
                (self.combined_data['patient_id'] >= start_id) & 
                (self.combined_data['patient_id'] <= end_id)
            ].copy()
            
            filtered_count = len(self.combined_data)
            filtered_patients = len(self.combined_data['patient_id'].unique()) if filtered_count > 0 else 0
            
            print(f"Patient filtering applied ({self.group_name}):")
            print(f"  Range: Patient IDs {start_id} to {end_id}")
            print(f"  Records: {original_count} → {filtered_count}")
            print(f"  Patients: {original_patients} → {filtered_patients}")
    
    def get_data_status(self):
        """Get current data loading status"""
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
        """Get list of available patient IDs"""
        if self.combined_data is not None:
            patient_ids = sorted(self.combined_data['patient_id'].unique())
            return [str(pid) for pid in patient_ids]
        else:
            return []
    
    def generate_fake_data(self, num_rows=1000):
        """Generate fake patient data for testing/demonstration"""
        # Generate unique patient IDs
        unique_patient_ids = np.random.randint(1, 1000, size=num_rows // 50)
        
        # Generate random number of events per patient (between 50 and 100)
        patient_event_counts = {patient_id: random.randint(50, 100) for patient_id in unique_patient_ids}
        
        # Generate data for each patient
        data = []
        for patient_id, event_count in patient_event_counts.items():
            # Generate random start and end dates within 2010-2022 range
            start_date_2010 = datetime(2010, 1, 1)
            end_date_2022 = datetime(2022, 12, 31)
            date_range_days = (end_date_2022 - start_date_2010).days

            start_dates = [start_date_2010 + timedelta(days=random.randint(0, date_range_days)) for _ in range(event_count)]
            end_dates = [start_date + timedelta(days=random.randint(0, 10)) for start_date in start_dates]

            # Ensure end dates don't exceed 2022
            for i, end_date in enumerate(end_dates):
                if end_date > end_date_2022:
                    end_dates[i] = end_date_2022
            
            # Generate random event types
            event_types = random.choices(
                ['imaging', 'ambulatory_visit', 'hospitalization', 'medication_change', 'lab_test'], 
                k=event_count
            )
            
            # Generate random ibd_related flags
            ibd_related = random.choices([True, False], k=event_count)
            
            # Generate random event_info as JSON strings
            event_info = [
                json.dumps({
                    "Patient Age": random.randint(1, 100),
                    "Patient Sex": random.choice(["Male", "Female"]),
                    "Additional Info": f"Info {i}"
                }) for i in range(event_count)
            ]
            
            # Generate random source datasets
            source_datasets = random.choices(['DI', 'DAD', 'CLAIMS', 'PIN', 'LAB', 'NACRS'], k=event_count)
            
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
        
        # Create a DataFrame
        fake_data = pd.DataFrame(data)
        return fake_data
    
    def reload_data(self):
        """Reload data from the directory"""
        import gradio as gr
        self.auto_load_data()
        patient_choices = self.get_patient_choices()
        status = self.get_data_status()
        return status, gr.update(choices=patient_choices, value=patient_choices[0] if patient_choices else None), status
    
    def export_data(self, format_choice):
        """Export current data"""
        if self.combined_data is None:
            return "No data to export"
        
        try:
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
        """Load timeline for selected patient with IBD filtering"""
        if self.combined_data is None:
            return None, "Please load patient data first", ""
        
        if not patient_id:
            return None, "Please select a patient ID", ""
        
        try:
            # Filter data for selected patient
            patient_data = self.combined_data[
                self.combined_data['patient_id'] == int(patient_id)
            ].copy()
            
            # Apply IBD filtering
            if ibd_filter == "IBD Related Only":
                patient_data = patient_data[patient_data['ibd_related'] == True]
            elif ibd_filter == "Non-IBD Related Only":
                patient_data = patient_data[patient_data['ibd_related'] == False]
            
            self.current_patient_data = patient_data
            self.current_patient_id = int(patient_id)
            
            # Load existing flares
            self.load_existing_flares()
            
            # Create timeline
            fig = self.create_timeline()
            info = self.get_chart_info()
            
            status_msg = f"Chart loaded for Patient {self.current_patient_id} ({ibd_filter})"
            
            return fig, status_msg, info
            
        except Exception as e:
            return None, f"Failed to load patient timeline: {str(e)}", ""
    
    def load_existing_flares(self):
        """Load existing flares from JSON file"""
        save_file = f'patient_{self.current_patient_id}_flares.json'
        self.ranges = []
        
        if os.path.exists(save_file):
            try:
                with open(save_file, 'r') as f:
                    saved_ranges = json.load(f)
                    for flare in saved_ranges:
                        flare_start = pd.to_datetime(flare['start_date'])
                        flare_end = pd.to_datetime(flare['end_date'])
                        # Handle both old and new format
                        if 'categories' in flare:
                            categories = flare['categories']
                            reason = flare.get('reason', '')
                            self.ranges.append((flare_start, flare_end, categories, reason))
                        else:
                            # Old format compatibility
                            reason = flare.get('reason', '')
                            self.ranges.append((flare_start, flare_end, [], reason))
            except Exception as e:
                print(f"Error loading flares: {e}")
    
    def load_patient_for_labelling(self, patient_id):
        """Load patient for labelling mode"""
        import gradio as gr
        if self.combined_data is None:
            return "Please load patient data first", gr.update(choices=[]), "", ""
        
        if not patient_id:
            return "Please select a patient ID", gr.update(choices=[]), "", ""
        
        try:
            # Filter data for selected patient (all events for labelling)
            patient_data = self.combined_data[
                self.combined_data['patient_id'] == int(patient_id)
            ].copy()
            
            self.current_patient_data = patient_data
            self.current_patient_id = int(patient_id)
            
            # Reset view offset
            self.current_view_offset = 0
            
            # Get available months
            month_choices = self.get_patient_months()
            
            status_msg = f"Patient {self.current_patient_id} loaded for labelling"
            
            return status_msg, gr.update(choices=month_choices, value=month_choices[0] if month_choices else None), "", ""
            
        except Exception as e:
            return f"Failed to load patient: {str(e)}", gr.update(choices=[]), "", ""
    
    def get_patient_months(self):
        """Get list of available months for selected patient - ONLY months with events"""
        if self.current_patient_data is None or len(self.current_patient_data) == 0:
            return []
        
        # Get all months that have actual events
        months_with_events = set()
        
        for _, row in self.current_patient_data.iterrows():
            # Add the month of the start date
            start_month = row['start_date'].to_period('M')
            months_with_events.add(start_month)
            
            # Add the month of the end date (if different)
            end_month = row['end_date'].to_period('M')
            months_with_events.add(end_month)
            
            # For events spanning multiple months, add all months in between
            if start_month != end_month:
                current_month = start_month
                while current_month <= end_month:
                    months_with_events.add(current_month)
                    current_month += 1
        
        # Sort the months
        months_sorted = sorted(months_with_events)
        
        # Format as readable strings
        month_strings = [f"{month.strftime('%B %Y')}" for month in months_sorted]
        return month_strings
    
    def get_all_patient_months(self):
        """Get list of ALL available months for selected patient - including empty months"""
        if self.current_patient_data is None or len(self.current_patient_data) == 0:
            return []
        
        # Get the full date range from first to last event
        min_date = self.current_patient_data['start_date'].min()
        max_date = self.current_patient_data['end_date'].max()
        
        # Generate all months between min and max dates
        start_month = min_date.to_period('M')
        end_month = max_date.to_period('M')
        
        all_months = []
        current_month = start_month
        while current_month <= end_month:
            all_months.append(current_month)
            current_month += 1
        
        # Format as readable strings
        month_strings = [f"{month.strftime('%B %Y')}" for month in all_months]
        return month_strings
    
    def navigate_month(self, current_month, direction):
        """Navigate to previous or next month - ONLY months with events"""
        if not current_month:
            return current_month
        
        try:
            # Get only months with events
            month_choices = self.get_patient_months()
            if current_month not in month_choices:
                # If current month is not in the filtered list, return the first available month
                return month_choices[0] if month_choices else None
            
            current_index = month_choices.index(current_month)
            
            if direction == "back" and current_index > 0:
                return month_choices[current_index - 1]
            elif direction == "forward" and current_index < len(month_choices) - 1:
                return month_choices[current_index + 1]
            else:
                return current_month
                
        except Exception as e:
            print(f"Error navigating month: {e}")
            return current_month
    
    def update_monthly_view(self, selected_month, view_offset=0):
        """Update the monthly timeline view - can show empty months"""
        if not selected_month:
            return None, "No month selected", ""
        
        try:
            from timeline_visualization import create_monthly_timeline
            fig = create_monthly_timeline(self, selected_month, view_offset)
            
            # Calculate current view month
            selected_period = pd.to_datetime(selected_month, format='%B %Y').to_period('M')
            view_period = selected_period + view_offset
            view_month_str = view_period.strftime('%B %Y')
            
            if fig:
                # Check if the view month has events
                event_months = self.get_patient_months()
                
                if view_month_str in event_months:
                    status_msg = f"Showing timeline for {view_month_str} (Labelling: {selected_month})"
                else:
                    status_msg = f"Showing timeline for {view_month_str} (NO EVENTS - Labelling: {selected_month})"
                
                return fig, status_msg, view_month_str
            else:
                return None, f"No data available for {view_month_str}", view_month_str
                
        except Exception as e:
            return None, f"Failed to update view: {str(e)}", ""
    
    def navigate_view(self, selected_month, direction):
        """Navigate the view forward or backward - can view ALL months including empty ones"""
        if direction == "back":
            self.current_view_offset -= 1
        elif direction == "forward":
            self.current_view_offset += 1
        
        return self.update_monthly_view(selected_month, self.current_view_offset)
    
    def create_timeline(self):
        """Create the plotly timeline figure"""
        from timeline_visualization import create_main_timeline
        return create_main_timeline(self)
    
    def get_chart_info(self):
        """Get chart information text"""
        if self.current_patient_data is None:
            return "No patient data loaded"
        
        from timeline_visualization import get_label_mapping
        label_mapping = get_label_mapping()
        
        info = f"Patient ID: {self.current_patient_id}\n"
        info += f"Total Events: {len(self.current_patient_data)}\n"
        info += f"Date Range: {self.current_patient_data['start_date'].min().date()} to {self.current_patient_data['end_date'].max().date()}\n\n"
        
        # Event type summary
        info += "Event Types:\n"
        event_counts = self.current_patient_data['event_type'].value_counts()
        for event_type, count in event_counts.items():
            readable_name = label_mapping.get(event_type, event_type.replace('_', ' ').title())
            info += f"  {readable_name}: {count}\n"
        
        # Original flare periods
        info += f"\nDate-based Flares: {len(self.ranges)}\n"
        for i, flare_data in enumerate(self.ranges):
            # Handle both old and new format
            if len(flare_data) == 3:  # Old format: (start, end, reason)
                start_date, end_date, reason = flare_data
                categories = []
            else:  # New format: (start, end, categories, reason)
                start_date, end_date, categories, reason = flare_data
            
            info += f"  {i+1}. {pd.to_datetime(start_date).date()} to {pd.to_datetime(end_date).date()}"
            
            if categories:
                readable_categories = [label_mapping.get(cat, cat.replace('_', ' ').title()) for cat in categories]
                info += f" ({', '.join(readable_categories)})"
            
            if reason:
                info += f": {reason}"
            
            info += "\n"
        
        # Monthly flares from labelling mode
        monthly_labels = self.load_monthly_labels()
        monthly_flares = {k: v for k, v in monthly_labels.items() if v.get('evidence') == 'Yes'}
        
        info += f"\nMonthly Flares: {len(monthly_flares)}\n"
        for month_period_str, label_data in sorted(monthly_flares.items()):
            try:
                period = pd.Period(month_period_str)
                month_str = period.strftime('%B %Y')
                info += f"  • {month_str}"
                
                categories = label_data.get('categories', [])
                if categories:
                    readable_categories = [label_mapping.get(cat, cat.replace('_', ' ').title()) for cat in categories]
                    info += f" ({', '.join(readable_categories)})"
                
                reason = label_data.get('reason', '')
                if reason:
                    info += f": {reason}"
                
                info += "\n"
                
            except Exception as e:
                print(f"Error formatting monthly flare: {e}")
                continue
        
        return info