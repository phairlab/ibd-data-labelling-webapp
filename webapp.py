import gradio as gr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import tempfile
import textwrap
from datetime import datetime, timedelta
import numpy as np
import random

class PatientTimelineApp:
    def __init__(self):
        # Data storage
        self.combined_data = None
        self.current_patient_data = None
        self.current_patient_id = None
        self.ranges = []  # Store flare periods
        self.fig = None
        
        # State for editing flares
        self.editing_flare_index = None
    
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
    
    def load_data_from_file(self, file):
        """Load data from uploaded file"""
        if file is None:
            return "No file uploaded", gr.update(choices=[]), "No data loaded"
        
        try:
            if file.name.endswith('.csv'):
                self.combined_data = pd.read_csv(file.name)
            elif file.name.endswith('.xlsx'):
                self.combined_data = pd.read_excel(file.name)
            else:
                return "Unsupported file format", gr.update(choices=[]), "Error loading data"
            
            # Convert date columns
            date_columns = ['start_date', 'end_date']
            for col in date_columns:
                if col in self.combined_data.columns:
                    self.combined_data[col] = pd.to_datetime(self.combined_data[col])
            
            # Update patient dropdown
            patient_ids = sorted(self.combined_data['patient_id'].unique())
            patient_choices = [str(pid) for pid in patient_ids]
            
            status_msg = f"Loaded {len(self.combined_data)} records for {len(patient_ids)} patients"
            
            return status_msg, gr.update(choices=patient_choices, value=patient_choices[0] if patient_choices else None), status_msg
            
        except Exception as e:
            return f"Failed to load data: {str(e)}", gr.update(choices=[]), "Error loading data"
    
    def generate_sample_data(self, num_records):
        """Generate sample data"""
        try:
            num_records = int(num_records)
            if num_records < 100:
                return "Minimum 100 records recommended", gr.update(choices=[]), "Error generating data"
            if num_records > 10000:
                return "Maximum 10,000 records recommended", gr.update(choices=[]), "Error generating data"
            
            self.combined_data = self.generate_fake_data(num_records)
            
            # Convert date columns
            date_columns = ['start_date', 'end_date']
            for col in date_columns:
                if col in self.combined_data.columns:
                    self.combined_data[col] = pd.to_datetime(self.combined_data[col])
            
            # Update patient dropdown
            patient_ids = sorted(self.combined_data['patient_id'].unique())
            patient_choices = [str(pid) for pid in patient_ids]
            
            status_msg = f"Generated {len(self.combined_data)} records for {len(patient_ids)} patients"
            
            return status_msg, gr.update(choices=patient_choices, value=patient_choices[0] if patient_choices else None), status_msg
            
        except Exception as e:
            return f"Failed to generate data: {str(e)}", gr.update(choices=[]), "Error generating data"
    
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
    
    def load_patient_timeline(self, patient_id):
        """Load timeline for selected patient"""
        if self.combined_data is None:
            return None, "Please load patient data first", "", gr.update(choices=[]), "", "", "", gr.update(visible=False)
        
        if not patient_id:
            return None, "Please select a patient ID", "", gr.update(choices=[]), "", "", "", gr.update(visible=False)
        
        try:
            # Filter data for selected patient
            self.current_patient_data = self.combined_data[
                self.combined_data['patient_id'] == int(patient_id)
            ].copy()
            self.current_patient_id = int(patient_id)
            
            # Reset editing state
            self.editing_flare_index = None
            
            # Load existing flares
            self.load_existing_flares()
            
            # Create timeline
            fig = self.create_timeline()
            info = self.get_chart_info()
            flare_choices = gr.update(choices=self.get_flare_list())
            
            return fig, f"Chart loaded for Patient {self.current_patient_id}", info, flare_choices, "", "", "", gr.update(visible=False)
            
        except Exception as e:
            return None, f"Failed to load patient timeline: {str(e)}", "", gr.update(choices=[]), "", "", "", gr.update(visible=False)
    
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
                        flare_reason = flare['reason']
                        self.ranges.append((flare_start, flare_end, flare_reason))
            except Exception as e:
                print(f"Error loading flares: {e}")
    
    def create_timeline(self):
        """Create the plotly timeline figure"""
        if self.current_patient_data is None:
            return None
        
        # Handle same-day events
        data = self.current_patient_data.copy()
        mask = data['start_date'] == data['end_date']
        data.loc[mask, 'end_date'] += pd.Timedelta(days=1)
        data['end_date'] += pd.Timedelta(days=2)  # Add 2 days to all bars
        
        # Parse event_info for hover data
        hover_data = []
        if 'event_info' in data.columns:
            try:
                for idx, row in data.iterrows():
                    try:
                        info = json.loads(row['event_info']) if isinstance(row['event_info'], str) else row['event_info']
                        hover_text = f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br>"
                        hover_text += f"<b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br>"
                        
                        # Add all fields from event_info
                        for key, value in info.items():
                            hover_text += f"<b>{key}:</b> {value}<br>"
                        
                        # Add other columns if they exist
                        if 'source_dataset' in row:
                            hover_text += f"<b>source_dataset:</b> {row['source_dataset']}<br>"
                        if 'ibd_related' in row:
                            hover_text += f"<b>ibd_related:</b> {row['ibd_related']}<br>"
                        
                        hover_data.append(hover_text.rstrip('<br>'))
                    except (json.JSONDecodeError, TypeError):
                        # Fallback if JSON parsing fails
                        hover_text = f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br>"
                        hover_text += f"<b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br>"
                        hover_text += f"<b>event_type:</b> {row['event_type']}"
                        hover_data.append(hover_text)
            except Exception as e:
                print(f"Error processing event info: {e}")
                # Fallback hover data
                hover_data = [f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br><b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br><b>event_type:</b> {row['event_type']}" 
                             for _, row in data.iterrows()]
        else:
            # Default hover data if no event_info
            hover_data = [f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br><b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br><b>event_type:</b> {row['event_type']}" 
                         for _, row in data.iterrows()]
        
        # Create timeline figure with custom hover data
        fig = px.timeline(
            data,
            x_start="start_date",
            x_end="end_date",
            y="event_type",
            color="event_type",
            hover_name=None  # Disable default hover
        )
        
        # Update traces with custom hover info and thicker bars
        for i, trace in enumerate(fig.data):
            # Get hover data for this trace (by event type)
            event_type = trace.name
            event_mask = data['event_type'] == event_type
            trace_hover_data = [hover_data[j] for j, mask_val in enumerate(event_mask) if mask_val]
            
            trace.update(
                hovertemplate='%{hovertext}<extra></extra>',
                hovertext=trace_hover_data,
                width=0.9,  # Make bars thicker
            )
        
        # Update layout
        fig.update_layout(
            xaxis_title="Time",
            yaxis_title="Event",
            showlegend=False,
            xaxis=dict(
                range=[
                    data['start_date'].min() - pd.Timedelta(days=10),
                    data['end_date'].max() + pd.Timedelta(days=10)
                ]
            ),
            bargap=0.1,
            bargroupgap=0.0,
            autosize=True,
            margin=dict(l=50, r=50, t=50, b=50),
            height=600
        )
        
        # Add flare periods
        self.add_flares_to_chart(fig, data)
        
        self.fig = fig
        return fig
    
    def add_flares_to_chart(self, fig, data):
        """Add flare periods to the chart"""
        if not self.ranges:
            return
        
        # Add flare periods
        for i, (start_date, end_date, reason) in enumerate(self.ranges):
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)
            
            # Add rectangle
            fig.add_vrect(
                x0=start_date, x1=end_date,
                fillcolor="red", opacity=0.3,
                layer="below", line_width=0,
            )
            
            # Add markers
            y_pos = len(data['event_type'].unique()) - 0.75
            wrapped_reason = "<br>".join(textwrap.wrap(reason, width=100))
            
            fig.add_trace(
                go.Scatter(
                    x=[start_date, end_date], 
                    y=[y_pos, y_pos],
                    mode='markers',
                    marker=dict(size=10, color='LightSeaGreen', symbol='triangle-down'),
                    hoverinfo='text',
                    hovertext=[
                        f"<b>Flare Start:</b><br>{start_date.date()}<br><b>Reason:</b><br>{wrapped_reason}",
                        f"<b>Flare End:</b><br>{end_date.date()}<br><b>Reason:</b><br>{wrapped_reason}"
                    ],
                    showlegend=False,
                    name=f'Flare {i+1} Boundaries'
                )
            )
        
        # Update y-axis to accommodate flare markers
        y_categories = list(data['event_type'].unique())
        fig.update_layout(
            yaxis=dict(
                categoryorder='array',
                categoryarray=y_categories,
                range=[-0.75, len(y_categories)+0.06],
                tickvals=list(range(len(y_categories))),
                ticktext=y_categories,
            )
        )
    
    def add_flare(self, start_date, end_date, reason):
        """Add a new flare period"""
        if self.current_patient_data is None:
            return None, "Please load a patient timeline first", start_date, end_date, reason, gr.update(choices=[]), gr.update(visible=False)
        
        if not start_date or not end_date:
            return None, "Please enter both start and end dates", start_date, end_date, reason, gr.update(choices=self.get_flare_list()), gr.update(visible=False)
        
        try:
            start_date_parsed = pd.to_datetime(start_date)
            end_date_parsed = pd.to_datetime(end_date)
            reason = reason or "No reason provided"
            
            if end_date_parsed < start_date_parsed:
                return None, "End date must be after start date", start_date, end_date, reason, gr.update(choices=self.get_flare_list()), gr.update(visible=False)
            
            self.ranges.append((start_date_parsed, end_date_parsed, reason))
            
            # Recreate chart with new flare
            fig = self.create_timeline()
            
            return fig, f"Added flare: {start_date_parsed.date()} to {end_date_parsed.date()}", "", "", "", gr.update(choices=self.get_flare_list()), gr.update(visible=False)
            
        except Exception as e:
            return None, f"Failed to add flare: {str(e)}", start_date, end_date, reason, gr.update(choices=self.get_flare_list()), gr.update(visible=False)
    
    def edit_flare(self, flare_selection):
        """Load selected flare for editing"""
        if not flare_selection or not self.ranges:
            return "", "", "", "Please select a flare to edit", gr.update(visible=False)
        
        try:
            # Parse the selection to get the index
            flare_list = self.get_flare_list()
            if flare_selection not in flare_list:
                return "", "", "", "Selected flare not found", gr.update(visible=False)
            
            flare_index = flare_list.index(flare_selection)
            self.editing_flare_index = flare_index
            
            # Get flare details
            start_date, end_date, reason = self.ranges[flare_index]
            start_date_str = pd.to_datetime(start_date).strftime('%Y-%m-%d')
            end_date_str = pd.to_datetime(end_date).strftime('%Y-%m-%d')
            
            return start_date_str, end_date_str, reason, f"Editing flare: {start_date_str} to {end_date_str}", gr.update(visible=True)
            
        except Exception as e:
            return "", "", "", f"Failed to load flare for editing: {str(e)}", gr.update(visible=False)
    
    def update_flare(self, start_date, end_date, reason):
        """Update the currently editing flare"""
        if self.editing_flare_index is None:
            return None, "No flare selected for editing", start_date, end_date, reason, gr.update(choices=self.get_flare_list()), gr.update(visible=False)
        
        if self.current_patient_data is None:
            return None, "Please load a patient timeline first", start_date, end_date, reason, gr.update(choices=self.get_flare_list()), gr.update(visible=False)
        
        if not start_date or not end_date:
            return None, "Please enter both start and end dates", start_date, end_date, reason, gr.update(choices=self.get_flare_list()), gr.update(visible=True)
        
        try:
            start_date_parsed = pd.to_datetime(start_date)
            end_date_parsed = pd.to_datetime(end_date)
            reason = reason or "No reason provided"
            
            if end_date_parsed < start_date_parsed:
                return None, "End date must be after start date", start_date, end_date, reason, gr.update(choices=self.get_flare_list()), gr.update(visible=True)
            
            # Update the flare
            old_flare = self.ranges[self.editing_flare_index]
            self.ranges[self.editing_flare_index] = (start_date_parsed, end_date_parsed, reason)
            
            # Reset editing state
            self.editing_flare_index = None
            
            # Recreate chart with updated flare
            fig = self.create_timeline()
            
            return fig, f"Updated flare: {start_date_parsed.date()} to {end_date_parsed.date()}", "", "", "", gr.update(choices=self.get_flare_list()), gr.update(visible=False)
            
        except Exception as e:
            return None, f"Failed to update flare: {str(e)}", start_date, end_date, reason, gr.update(choices=self.get_flare_list()), gr.update(visible=True)
    
    def cancel_edit_flare(self):
        """Cancel editing the current flare"""
        self.editing_flare_index = None
        return "", "", "", "Edit cancelled", gr.update(visible=False)
    
    def delete_flare(self, flare_selection):
        """Delete selected flare"""
        if not flare_selection or not self.ranges:
            return None, "Please select a flare to delete", gr.update(choices=self.get_flare_list()), gr.update(visible=False)
        
        try:
            # Parse the selection to get the index
            flare_list = self.get_flare_list()
            if flare_selection not in flare_list:
                return None, "Selected flare not found", gr.update(choices=flare_list), gr.update(visible=False)
                
            flare_index = flare_list.index(flare_selection)
            deleted_flare = self.ranges.pop(flare_index)
            
            # Reset editing state if we deleted the flare being edited
            if self.editing_flare_index == flare_index:
                self.editing_flare_index = None
            elif self.editing_flare_index is not None and self.editing_flare_index > flare_index:
                self.editing_flare_index -= 1
            
            # Recreate chart without deleted flare
            fig = self.create_timeline() if self.current_patient_data is not None else None
            
            return fig, f"Deleted flare: {pd.to_datetime(deleted_flare[0]).date()} to {pd.to_datetime(deleted_flare[1]).date()}", gr.update(choices=self.get_flare_list()), gr.update(visible=False)
            
        except Exception as e:
            return None, f"Failed to delete flare: {str(e)}", gr.update(choices=self.get_flare_list()), gr.update(visible=False)
    
    def save_flares(self):
        """Save flares to JSON file"""
        if self.current_patient_id is None:
            return "No patient selected"
        
        try:
            flares_to_save = [
                {
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "reason": reason
                }
                for start_date, end_date, reason in self.ranges
            ]
            
            save_file = f'patient_{self.current_patient_id}_flares.json'
            with open(save_file, 'w') as f:
                json.dump(flares_to_save, f, indent=2)
            
            return f"Saved {len(flares_to_save)} flares to {save_file}"
            
        except Exception as e:
            return f"Failed to save flares: {str(e)}"
    
    def get_flare_list(self):
        """Get list of flares for dropdown"""
        return [f"{pd.to_datetime(start_date).date()} to {pd.to_datetime(end_date).date()}: {reason}" 
                for start_date, end_date, reason in self.ranges]
    
    def get_chart_info(self):
        """Get chart information text"""
        if self.current_patient_data is None:
            return "No patient data loaded"
        
        info = f"Patient ID: {self.current_patient_id}\n"
        info += f"Total Events: {len(self.current_patient_data)}\n"
        info += f"Date Range: {self.current_patient_data['start_date'].min().date()} to {self.current_patient_data['end_date'].max().date()}\n\n"
        
        # Event type summary
        info += "Event Types:\n"
        event_counts = self.current_patient_data['event_type'].value_counts()
        for event_type, count in event_counts.items():
            info += f"  {event_type}: {count}\n"
        
        info += f"\nFlare Periods: {len(self.ranges)}\n"
        for i, (start_date, end_date, reason) in enumerate(self.ranges):
            info += f"  {i+1}. {pd.to_datetime(start_date).date()} to {pd.to_datetime(end_date).date()}: {reason}\n"
        
        return info
    
    def refresh_chart(self):
        """Refresh the chart display"""
        if self.current_patient_data is not None:
            fig = self.create_timeline()
            info = self.get_chart_info()
            return fig, "Chart refreshed", info
        else:
            return None, "No patient data loaded", ""

# Initialize the app
app = PatientTimelineApp()

def create_interface():
    """Create the Gradio interface"""
    
    with gr.Blocks(title="Patient Timeline Viewer", theme=gr.themes.Soft(font=[gr.themes.GoogleFont("Inter"), "Arial", "Roboto"], primary_hue = "blue" )) as demo:
        gr.Markdown("# Patient Timeline Viewer")
        gr.Markdown("A comprehensive tool for visualizing patient timelines and managing flare periods.")
        
        with gr.Tab("Data Loading"):
            gr.Markdown("### Load or Generate Patient Data")
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("**Upload Data File**")
                    file_input = gr.File(label="Upload CSV or Excel file", file_types=[".csv", ".xlsx"])
                    load_btn = gr.Button("Load Data", variant="primary")
                
                with gr.Column():
                    gr.Markdown("**Generate Sample Data**")
                    num_records = gr.Number(label="Number of records", value=1000, minimum=100, maximum=10000)
                    generate_btn = gr.Button("Generate Sample Data", variant="secondary")
                
                with gr.Column():
                    gr.Markdown("**Export Current Data**")
                    export_format = gr.Radio(["CSV", "Excel"], label="Export format", value="CSV")
                    export_btn = gr.Button("Export Data")
            
            data_status = gr.Textbox(label="Status", value="No data loaded", interactive=False)
        
        with gr.Tab("Timeline Viewer"):
            with gr.Row():
                with gr.Column(scale=1, min_width=300):
                    gr.Markdown("### Patient Selection")
                    patient_dropdown = gr.Dropdown(label="Patient ID", choices=[], interactive=True)
                    load_timeline_btn = gr.Button("Load Timeline", variant="primary")
                    
                    gr.Markdown("### Flare Management")
                    with gr.Group():
                        gr.Markdown("**Add/Edit Flare Period**")
                        start_date_input = gr.Textbox(label="Start Date (YYYY-MM-DD)", placeholder="YYYY-MM-DD")
                        end_date_input = gr.Textbox(label="End Date (YYYY-MM-DD)", placeholder="YYYY-MM-DD")
                        reason_input = gr.Textbox(label="Reason", placeholder="Enter reason for flare")
                        
                        with gr.Row():
                            add_flare_btn = gr.Button("Add Flare", variant="secondary")
                        
                        # Edit mode controls - initially hidden
                        with gr.Group(visible=False) as edit_group:
                            gr.Markdown("**Edit Mode Active**")
                            with gr.Row():
                                update_flare_btn = gr.Button("Update Flare", variant="primary")
                                cancel_edit_btn = gr.Button("Cancel Edit", variant="secondary")
                    
                    with gr.Group():
                        gr.Markdown("**Manage Existing Flares**")
                        flare_dropdown = gr.Dropdown(label="Existing Flares", choices=[], interactive=True)
                        with gr.Row():
                            edit_flare_btn = gr.Button("Edit Selected", variant="secondary")
                            delete_flare_btn = gr.Button("Delete Selected", variant="stop")
                        save_flares_btn = gr.Button("Save Flares", variant="secondary")
                    
                    flare_status = gr.Textbox(label="Flare Status", value="", interactive=False, visible=False)
                    chart_info = gr.Textbox(label="Chart Information", value="No patient data loaded", 
                                          lines=8, interactive=False, max_lines=12)
                
                with gr.Column(scale=3):
                    gr.Markdown("### Timeline Chart")
                    chart_status = gr.Textbox(label="Chart Status", value="No chart loaded", interactive=False)
                    refresh_chart_btn = gr.Button("Refresh Chart", variant="secondary")
                    timeline_plot = gr.Plot(label="Patient Timeline")
        
        with gr.Tab("User Guide"):
            gr.Markdown("""
            ## Patient Timeline Viewer - User Guide
            
            ### 1. Data Loading
            - **Load Patient Data**: Upload a CSV or Excel file containing patient data with columns: patient_id, start_date, end_date, event_type
            - **Generate Sample Data**: Create realistic sample data for testing (100-10,000 records)
            - **Export Current Data**: Save the currently loaded data to CSV or Excel format
            
            ### 2. Timeline Viewer
            - **Patient Selection**: Choose a patient from the dropdown and load their timeline
            - **Add Flare Period**: Enter start date, end date, and reason to mark flare periods
            - **Edit Flare Period**: Select an existing flare and click "Edit Selected" to modify its details
            - **Manage Flares**: Delete existing flares or save all flares to a JSON file
            - **Interactive Chart**: Hover over events for detailed information, zoom and pan as needed
            
            ### 3. Flare Editing Workflow
            - Select a flare from the "Existing Flares" dropdown
            - Click "Edit Selected" to load the flare details into the form
            - Modify the start date, end date, or reason as needed
            - Click "Update Flare" to save changes or "Cancel Edit" to discard changes
            
            ### 4. Features
            - **Rich Hover Information**: View detailed event information including patient demographics
            - **Flare Visualization**: Red shaded regions and triangular markers show flare periods
            - **Persistent Storage**: Flare data is saved per patient and reloaded automatically
            - **Export Capabilities**: Save charts as images using Plotly's built-in tools
            
            ### 5. Data Format
            Required columns:
            - `patient_id`: Unique identifier for each patient
            - `start_date`: Event start date (YYYY-MM-DD format)
            - `end_date`: Event end date (YYYY-MM-DD format)  
            - `event_type`: Type of medical event
            
            Optional columns:
            - `event_info`: JSON string with additional details
            - `source_dataset`: Data source identifier
            - `ibd_related`: Boolean flag for IBD-related events
            """)
        
        # Event handlers
        load_btn.click(
            app.load_data_from_file,
            inputs=[file_input],
            outputs=[data_status, patient_dropdown, chart_info]
        )
        
        generate_btn.click(
            app.generate_sample_data,
            inputs=[num_records],
            outputs=[data_status, patient_dropdown, chart_info]
        )
        
        export_btn.click(
            app.export_data,
            inputs=[export_format],
            outputs=[data_status]
        )
        
        load_timeline_btn.click(
            app.load_patient_timeline,
            inputs=[patient_dropdown],
            outputs=[timeline_plot, chart_status, chart_info, flare_dropdown, start_date_input, end_date_input, reason_input, edit_group]
        )
        
        add_flare_btn.click(
            app.add_flare,
            inputs=[start_date_input, end_date_input, reason_input],
            outputs=[timeline_plot, chart_status, start_date_input, end_date_input, reason_input, flare_dropdown, edit_group]
        ).then(
            lambda: app.get_chart_info(),
            outputs=[chart_info]
        )
        
        edit_flare_btn.click(
            app.edit_flare,
            inputs=[flare_dropdown],
            outputs=[start_date_input, end_date_input, reason_input, chart_status, edit_group]
        )
        
        update_flare_btn.click(
            app.update_flare,
            inputs=[start_date_input, end_date_input, reason_input],
            outputs=[timeline_plot, chart_status, start_date_input, end_date_input, reason_input, flare_dropdown, edit_group]
        ).then(
            lambda: app.get_chart_info(),
            outputs=[chart_info]
        )
        
        cancel_edit_btn.click(
            app.cancel_edit_flare,
            outputs=[start_date_input, end_date_input, reason_input, chart_status, edit_group]
        )
        
        delete_flare_btn.click(
            app.delete_flare,
            inputs=[flare_dropdown],
            outputs=[timeline_plot, chart_status, flare_dropdown, edit_group]
        ).then(
            lambda: app.get_chart_info(),
            outputs=[chart_info]
        )
        
        save_flares_btn.click(
            app.save_flares,
            outputs=[chart_status]
        )
        
        refresh_chart_btn.click(
            app.refresh_chart,
            outputs=[timeline_plot, chart_status, chart_info]
        )
    
    return demo

if __name__ == "__main__":
    demo = create_interface()
    demo.launch(share=True, debug=True)