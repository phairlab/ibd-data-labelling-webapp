import gradio as gr
import argparse
import sys
from patient_timeline_webapp import PatientTimelineApp
from monthly_labelling import add_monthly_labelling_methods
from timeline_visualization import create_main_timeline, create_monthly_timeline

# Initialize the app (will be created with command line arguments)
app = None

def parse_arguments():
    """Parse command line arguments to determine patient access"""
    parser = argparse.ArgumentParser(description='Patient Timeline Viewer with Patient Group Access Control')
    
    # Define different patient groups/commands
    subparsers = parser.add_subparsers(dest='command', help='Available patient groups')
    
    # Group A: Patients 1-100
    group_a = subparsers.add_parser('group-a', help='Access patients 1-100')
    group_a.add_argument('--start', type=int, default=1, help='Start patient ID (default: 1)')
    group_a.add_argument('--end', type=int, default=100, help='End patient ID (default: 100)')
    
    # Group B: Patients 101-200
    group_b = subparsers.add_parser('group-b', help='Access patients 101-200')
    group_b.add_argument('--start', type=int, default=101, help='Start patient ID (default: 101)')
    group_b.add_argument('--end', type=int, default=200, help='End patient ID (default: 200)')
    
    # Group C: Patients 201-300
    group_c = subparsers.add_parser('group-c', help='Access patients 201-300')
    group_c.add_argument('--start', type=int, default=201, help='Start patient ID (default: 201)')
    group_c.add_argument('--end', type=int, default=300, help='End patient ID (default: 300)')
    
    # Custom range
    custom = subparsers.add_parser('custom', help='Access custom patient range')
    custom.add_argument('--start', type=int, required=True, help='Start patient ID')
    custom.add_argument('--end', type=int, required=True, help='End patient ID')
    custom.add_argument('--name', type=str, default='Custom', help='Group name for display')
    
    # Admin access (all patients)
    admin = subparsers.add_parser('admin', help='Access all patients (admin mode)')
    
    # Development mode (sample data)
    dev = subparsers.add_parser('dev', help='Development mode with sample data')
    dev.add_argument('--patients', type=int, default=50, help='Number of sample patients (default: 50)')
    
    return parser.parse_args()

def create_app_with_args():
    """Create app instance based on command line arguments"""
    args = parse_arguments()
    
    if args.command == 'group-a':
        return PatientTimelineApp(patient_range=(args.start, args.end), group_name="Group A")
    elif args.command == 'group-b':
        return PatientTimelineApp(patient_range=(args.start, args.end), group_name="Group B")
    elif args.command == 'group-c':
        return PatientTimelineApp(patient_range=(args.start, args.end), group_name="Group C")
    elif args.command == 'custom':
        return PatientTimelineApp(patient_range=(args.start, args.end), group_name=args.name)
    elif args.command == 'admin':
        return PatientTimelineApp(patient_range=None, group_name="Admin (All Patients)")
    elif args.command == 'dev':
        app = PatientTimelineApp(patient_range=None, group_name="Development Mode")
        # Override with sample data
        app.combined_data = app.generate_fake_data(args.patients * 20)  # 20 events per patient average
        return app
    else:
        print("No command specified. Available commands:")
        print("  python main.py group-a    # Access patients 1-100")
        print("  python main.py group-b    # Access patients 101-200") 
        print("  python main.py group-c    # Access patients 201-300")
        print("  python main.py custom --start 1 --end 50 --name 'My Group'")
        print("  python main.py admin      # Access all patients")
        print("  python main.py dev        # Development mode with sample data")
        sys.exit(1)

def create_interface():
    """Create the Gradio interface"""
    
    with gr.Blocks(
        title=f"Patient Timeline Viewer - {app.group_name}", 
        theme=gr.themes.Soft(
            font=[gr.themes.GoogleFont("Inter"), "Arial", "Roboto"], 
            primary_hue="blue"
        )
    ) as demo:
        # Updated CSS styling for clean design
        gr.HTML("""
            <style>
            /* Section title styling with blue underline */
            .section-title {
                font-size: 16px !important;
                font-weight: 600 !important;
                color: #1f2937 !important;
                margin-bottom: 12px !important;
                padding-bottom: 6px !important;
                border-bottom: 2px solid #3b82f6 !important;
                display: block !important;
            }
            
            /* Clean control column - no boxes, just spacing */
            .clean-control-column {
                padding-right: 20px !important;
            }
            
            .clean-control-column > * {
                margin-bottom: 12px !important;
            }
            
            .clean-control-column .section-title {
                margin-top: 10px !important;
                margin-bottom: 8px !important;
            }
            
            .clean-control-column .section-title:first-child {
                margin-top: 0 !important;
            }
            
            /* Clean month dropdown styling */
            .clean-month-dropdown {
                margin-bottom: 12px !important;
            }
            
            .clean-month-dropdown .gr-form {
                background: white !important;
                border: 1px solid #d1d5db !important;
                border-radius: 8px !important;
                padding: 8px 12px !important;
            }
            
            .clean-month-dropdown .gr-form:focus-within {
                border-color: #3b82f6 !important;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
            }
            
            /* Month navigation row */
            .month-nav-row {
                display: flex !important;
                gap: 8px !important;
                margin-bottom: 16px !important;
            }
            
            .month-nav-button {
                flex: 1 !important;
                border-radius: 8px !important;
                padding: 8px 12px !important;
                font-size: 14px !important;
                font-weight: 500 !important;
            }
            
            .month-nav-button:hover {
                transform: translateY(-1px) !important;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
            }
            
            /* Timeline navigation styling */
            .timeline-nav {
                margin-bottom: 12px !important;
                padding: 8px 0 !important;
                display: flex !important;
                align-items: center !important;
                gap: 12px !important;
            }
            
            .timeline-nav button {
                border-radius: 8px !important;
                padding: 8px 16px !important;
                font-size: 14px !important;
                font-weight: 500 !important;
            }
            
            /* Better alignment for labelling top row */
            .labelling-top-row {
                align-items: flex-start !important;
                margin-bottom: 25px !important;
            }
            
            .labelling-top-row .section-title {
                margin-top: 0 !important;
            }
            
            /* Better button styling */
            .gradio-button {
                border-radius: 8px !important;
                font-weight: 500 !important;
                transition: all 0.2s ease !important;
            }
            
            .gradio-button:hover {
                transform: translateY(-1px) !important;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
            }
            
            /* Improve form elements */
            .gr-form {
                border-radius: 8px !important;
                border: 1px solid #d1d5db !important;
                transition: border-color 0.2s ease !important;
            }
            
            .gr-form:focus-within {
                border-color: #3b82f6 !important;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
            }
            
            /* Better spacing for radio buttons */
            .gr-radio {
                margin-bottom: 12px !important;
            }
            
            /* Improve textbox styling */
            .gr-textbox {
                border-radius: 8px !important;
            }
            
            /* Clean up dropdown appearance */
            .gr-dropdown {
                border-radius: 8px !important;
            }
            
            /* Better plot container */
            .gr-plot {
                border-radius: 10px !important;
                border: 1px solid #e5e7eb !important;
                overflow: hidden !important;
            }
            
            /* Remove default gradio group styling */
            .gradio-group {
                border: none !important;
                background: none !important;
                padding: 0 !important;
                margin: 0 !important;
            }
            
            /* Clean spacing for form elements */
            .gr-box {
                margin-bottom: 12px !important;
            }
            
            /* Better row spacing */
            .gr-row {
                margin-bottom: 8px !important;
            }
            
            /* Ensure consistent spacing between elements */
            .clean-control-column .gr-dropdown,
            .clean-control-column .gr-radio,
            .clean-control-column .gr-textbox {
                margin-bottom: 12px !important;
            }
            
            /* Button row spacing */
            .clean-control-column .gr-row {
                margin-bottom: 12px !important;
            }
            </style>
            """
        )
        
        gr.Markdown(f"# Patient Timeline Viewer - {app.group_name}")
        gr.Markdown("A comprehensive tool for visualizing patient timelines and managing flare periods.")
        
        with gr.Tab("Data Overview"):
            gr.Markdown("### Current Data Status")
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("**Data Information**")
                    data_status = gr.Textbox(label="Status", value=app.get_data_status(), interactive=False)
                    reload_data_btn = gr.Button("Reload Data", variant="primary")
                
                with gr.Column():
                    gr.Markdown("**Export Current Data**")
                    export_format = gr.Radio(["CSV", "Excel"], label="Export format", value="CSV")
                    export_btn = gr.Button("Export Data")
                    export_status = gr.Textbox(label="Export Status", value="", interactive=False)
        
        with gr.Tab("Timeline Viewer"):
            with gr.Column():
                # Top row with patient selection and filters
                with gr.Row():
                    with gr.Column(scale=1, min_width=200):
                        gr.Markdown("### Patient Selection")
                        patient_dropdown = gr.Dropdown(
                            label="Patient ID", 
                            choices=app.get_patient_choices(),
                            value=app.get_patient_choices()[0] if app.get_patient_choices() else None,
                            interactive=True
                        )
                        load_timeline_btn = gr.Button("Load Timeline", variant="primary")
                    
                    with gr.Column(scale=5):
                        gr.Markdown("### Timeline Chart")
                        
                        # IBD Filter controls above the chart
                        with gr.Row():
                            ibd_filter = gr.Radio(
                                choices=["All Events", "IBD Related Only", "Non-IBD Related Only"],
                                label="Event Filter",
                                value="All Events",
                                interactive=True
                            )
                            refresh_chart_btn = gr.Button("Refresh Chart", variant="secondary")
                        
                        chart_status = gr.Textbox(label="Chart Status", value="No chart loaded", interactive=False)
                
                # Full width timeline - increased height
                timeline_plot = gr.Plot(label="Patient Timeline")
                
                # Chart info below timeline - decreased height
                chart_info = gr.Textbox(label="Chart Information", value="No patient data loaded", 
                                      lines=3, interactive=False, max_lines=4)
        
        with gr.Tab("Labelling Mode"):
            # Top row with patient selection and chart status - ALIGNED HEADERS
            with gr.Row(elem_classes="labelling-top-row"):
                with gr.Column(scale=1):
                    gr.HTML("<h3 class='section-title'>Patient Selection</h3>")
                    patient_dropdown_label = gr.Dropdown(
                        label="Patient ID", 
                        choices=app.get_patient_choices(),
                        value=app.get_patient_choices()[0] if app.get_patient_choices() else None,
                        interactive=True
                    )
                    load_labelling_btn = gr.Button("Load Patient", variant="primary", size="lg")
                
                with gr.Column(scale=1):
                    gr.HTML("<h3 class='section-title'>Chart Status</h3>")
                    label_chart_status = gr.Textbox(
                        label="Status",
                        value="Select and load a patient to begin labelling",
                        interactive=False
                    )
            
            # Main content area
            with gr.Row():
                # LEFT COLUMN - Clean single column design
                with gr.Column(scale=1, min_width=320, elem_classes="clean-control-column"):
                    
                    # Generating Label For section - CLEAN, NO ARROWS
                    gr.HTML("<h3 class='section-title'>Generating Label For</h3>")
                    month_dropdown = gr.Dropdown(
                        label="Select Month",
                        choices=[],
                        interactive=True,
                        elem_classes="clean-month-dropdown"
                    )
                    
                    # Month navigation buttons - separate row
                    with gr.Row(elem_classes="month-nav-row"):
                        month_back_btn = gr.Button("◀ Previous Month", 
                                                 size="sm", 
                                                 variant="secondary", 
                                                 elem_classes="month-nav-button")
                        month_forward_btn = gr.Button("Next Month ▶", 
                                                    size="sm", 
                                                    variant="secondary", 
                                                    elem_classes="month-nav-button")
                    
                    # Flare Management section
                    gr.HTML("<h3 class='section-title'>Flare Management</h3>")
                    
                    flare_evidence = gr.Radio(
                        choices=["Yes", "No"],
                        label="Evidence of Flare",
                        value="No",
                        interactive=True
                    )
                    
                    category_dropdown_label = gr.Dropdown(
                        label="Category (Required if Yes)",
                        choices=[
                            "Ambulatory Visit",
                            "Lab Test", 
                            "Prescription",
                            "Physician Claim",
                            "Hospital Admission",
                            "Imaging"
                        ],
                        value=[],
                        multiselect=True,
                        interactive=True
                    )
                    
                    reason_input_label = gr.Textbox(
                        label="Reason (Optional)", 
                        placeholder="Enter reason for flare",
                        lines=2
                    )

                    with gr.Row():
                        save_label_btn = gr.Button("Save Label", variant="primary", scale=1)
                        clear_label_btn = gr.Button("Clear Label", variant="secondary", scale=1)

                    # Edit section
                    gr.HTML("<h3 class='section-title'>Edit Existing Label</h3>")
                    
                    edit_month_dropdown = gr.Dropdown(
                        label="Select Month to Edit",
                        choices=[],
                        interactive=True
                    )

                    with gr.Row():
                        load_edit_btn = gr.Button("Load for Edit", variant="secondary", scale=1)
                        delete_label_btn = gr.Button("Delete Label", variant="stop", scale=1)

                    # Saved labels section
                    gr.HTML("<h3 class='section-title'>Saved Labels</h3>")
                    labels_info = gr.Textbox(
                        label="Labels Summary",
                        value="No labels saved yet",
                        interactive=False,
                        lines=8,
                        max_lines=12
                    )

                # RIGHT COLUMN - Timeline Plot (3/4 width)
                with gr.Column(scale=3):
                    # Timeline navigation buttons at top of chart
                    with gr.Row(elem_classes="timeline-nav"):
                        view_back_btn_visible = gr.Button("◀ Previous Month", 
                                                        size="sm", 
                                                        variant="secondary")
                        gr.HTML("<div style='flex: 1;'></div>")  # Spacer
                        view_forward_btn_visible = gr.Button("Next Month ▶", 
                                                           size="sm", 
                                                           variant="secondary")
                    
                    monthly_timeline_plot = gr.Plot()
                    
            # Hidden element for current view info (needed for event handlers)
            current_view_info_visible = gr.Textbox(
                label="Current View",
                value="",
                interactive=False,
                visible=False
            )
        
        with gr.Tab("User Guide"):
            gr.Markdown("""
            ## Patient Timeline Viewer - User Guide
            
            ### 1. Data Loading & Access Control
            - **Command-Based Access**: Different commands provide access to different patient groups
            - **Available Commands**:
              - `python main.py group-a` - Access patients 1-100
              - `python main.py group-b` - Access patients 101-200  
              - `python main.py group-c` - Access patients 201-300
              - `python main.py custom --start X --end Y --name "Group Name"` - Custom range
              - `python main.py admin` - Access all patients (admin mode)
              - `python main.py dev` - Development mode with sample data
            - **Data Directory**: `/data/external_ps/baumgart/BAUMGART_SHARED/Baumgart_IBD/Sacha/ibd_activity_viewer/data`
            - **Reload Data**: Use the "Reload Data" button to refresh data from the directory
            - **Export Current Data**: Save the currently loaded data to CSV or Excel format
            
            ### 2. Timeline Viewer & Event Filtering
            - **Patient Selection**: Choose a patient from the dropdown (automatically populated from your assigned patient group)
            - **IBD Event Filtering**: Use the radio buttons above the chart to filter events:
              - **"All Events"** - Show all medical events (default)
              - **"IBD Related Only"** - Show only IBD-related events (`ibd_related = True`)
              - **"Non-IBD Related Only"** - Show only non-IBD events (`ibd_related = False`)
            - **Real-time Filtering**: Event filter changes apply immediately without reloading
            - **Interactive Chart**: Hover over events for detailed information, zoom and pan as needed
            - **Cross-Tab Flares**: Monthly flares created in Labelling Mode appear as orange highlights with star markers
            
            ### 3. Labelling Mode (Monthly Flare Labeling)
            - **Patient Selection**: Choose a patient for monthly labeling
            - **Month Navigation**: Select specific months using dropdown and navigation buttons
            - **Monthly View**: Timeline shows selected month with navigation to view adjacent months
            - **Evidence Classification**: Mark each month as having flare evidence (Yes/No)
            - **Category Selection**: If evidence exists, select relevant medical event categories
            - **Reason Documentation**: Optional text field for additional details
            - **Efficient Navigation**: Dropdown only shows months with events for faster labeling
            
            ### 4. Monthly Timeline Features
            - **Focused View**: Shows one month at a time with context from adjacent periods
            - **Navigation Controls**: Move view forward/backward while maintaining labeling target
            - **Visual Highlighting**: Selected month highlighted with blue background
            - **Persistent Labels**: All monthly labels saved automatically per patient
            - **Empty Month Indication**: Status shows "(NO EVENTS)" when viewing empty months
            
            ### 5. Flare Types & Visualization
            - **Date-based Flares**: Red rectangles with teal triangle markers (original functionality)
            - **Monthly Flares**: Orange rectangles with orange star markers (from labelling mode)
            - **Rich Hover Information**: All flare details available on hover in both tabs
            - **Cross-Tab Synchronization**: Monthly flares automatically appear in Timeline Viewer
            
            ### 6. Lab Test Visualization
            - **Multiple Same-Day Tests**: When multiple lab tests occur on the same day, they appear as separate adjacent bars with 2-hour time offsets
            - **Visual Separation**: Each lab test maintains its original duration but gets a small time offset for visibility
            - **Individual Hover Data**: Each lab test bar shows its own specific details in the hover tooltip
            
            ### 7. Advanced Features
            - **Command-Line Access Control**: Different teams can access different patient cohorts
            - **Automatic Data Loading**: No need to manually upload files - data is loaded from the specified directory
            - **Rich Hover Information**: View detailed event information with smart text wrapping for long descriptions
            - **Color-Coded Events**: Different event types (lab tests, prescriptions, visits, etc.) have distinct colors
            - **Colored Hover Tooltips**: Hover tooltips match the color of their corresponding event bars
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
            python main.py group-a
            
            # Clinical team accessing different cohort
            python main.py group-b
            
            # Custom analysis group
            python main.py custom --start 150 --end 250 --name "Cohort Study"
            
            # Administrator viewing all patients
            python main.py admin
            
            # Development/testing with sample data
            python main.py dev --patients 50
            ```
            
            ### 10. Troubleshooting
            - **No patients visible**: Check that your command provides access to patients in the data range
            - **Missing events**: Verify the IBD filter setting matches what you want to see
            - **Overlapping lab tests**: The app automatically separates same-day lab tests - if still overlapping, try refreshing the chart
            - **Flare not saving**: Ensure dates are in YYYY-MM-DD format and end date is after start date
            - **Data not loading**: Check that the data directory exists and contains CSV files with "events" in the filename
            - **Monthly flares not showing**: Ensure you're viewing the correct patient and the timeline is refreshed
            """)
        
        # Event handlers
        reload_data_btn.click(
            app.reload_data,
            outputs=[data_status, patient_dropdown, chart_info]
        )
        
        export_btn.click(
            app.export_data,
            inputs=[export_format],
            outputs=[export_status]
        )
        
        # Timeline Viewer event handlers - UPDATED TO INCLUDE AUTO-REFRESH
        load_timeline_btn.click(
            app.load_patient_timeline,
            inputs=[patient_dropdown, ibd_filter],
            outputs=[timeline_plot, chart_status, chart_info]
        )
        
        # IBD filter change handler
        ibd_filter.change(
            app.load_patient_timeline,
            inputs=[patient_dropdown, ibd_filter],
            outputs=[timeline_plot, chart_status, chart_info]
        )
        
        refresh_chart_btn.click(
            app.load_patient_timeline,
            inputs=[patient_dropdown, ibd_filter],
            outputs=[timeline_plot, chart_status, chart_info]
        )
        
        # Auto-refresh timeline when switching patients
        patient_dropdown.change(
            app.load_patient_timeline,
            inputs=[patient_dropdown, ibd_filter],
            outputs=[timeline_plot, chart_status, chart_info]
        )
        
        # Create hidden elements needed for event handlers
        current_view_info = gr.Textbox(label="Current View", value="", interactive=False, visible=False)
        view_back_btn = gr.Button("◀ Previous Month", variant="secondary", visible=False)
        view_forward_btn = gr.Button("Next Month ▶", variant="secondary", visible=False)
        
        # Labelling Mode event handlers
        load_labelling_btn.click(
            app.load_patient_for_labelling,
            inputs=[patient_dropdown_label],
            outputs=[label_chart_status, month_dropdown, current_view_info_visible, labels_info]
        )
        
        # Month navigation - simplified (keeps labeling month separate from view)
        def navigate_month_back(month):
            new_month = app.navigate_month(month, "back")
            edit_choices = app.get_monthly_labels_list()
            return new_month, gr.update(choices=edit_choices)
        
        def navigate_month_forward(month):
            new_month = app.navigate_month(month, "forward")
            edit_choices = app.get_monthly_labels_list()
            return new_month, gr.update(choices=edit_choices)
        
        def update_month_view(month):
            app.current_view_offset = 0  # Reset view offset
            if month:
                fig, status, view_info = app.update_monthly_view(month, 0)
                edit_choices = app.get_monthly_labels_list()
                return fig, status, view_info, gr.update(choices=edit_choices)
            return None, "No month selected", "", gr.update(choices=[])
        
        month_back_btn.click(
            navigate_month_back,
            inputs=[month_dropdown],
            outputs=[month_dropdown, edit_month_dropdown]
        )
        
        month_forward_btn.click(
            navigate_month_forward,
            inputs=[month_dropdown],
            outputs=[month_dropdown, edit_month_dropdown]
        )
        
        # Month dropdown change - updates view AND edit choices
        month_dropdown.change(
            update_month_view,
            inputs=[month_dropdown],
            outputs=[monthly_timeline_plot, label_chart_status, current_view_info_visible, edit_month_dropdown]
        )
        
        # View navigation for the visible buttons
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
        
        # Label management
        def save_label_and_refresh(month, evidence, categories, reason):
            status, labels_info = app.save_monthly_label(month, evidence, categories, reason)
            # Refresh the timeline to show new flare highlighting
            if month:
                fig, chart_status, view_info = app.update_monthly_view(month, app.current_view_offset)
                edit_choices = app.get_monthly_labels_list()
                return status, labels_info, fig, gr.update(choices=edit_choices)
            return status, labels_info, None, gr.update(choices=[])
        
        def clear_label_and_refresh(month):
            status, labels_info = app.clear_monthly_label(month)
            # Refresh the timeline to remove flare highlighting
            if month:
                fig, chart_status, view_info = app.update_monthly_view(month, app.current_view_offset)
                edit_choices = app.get_monthly_labels_list()
                return status, labels_info, fig, gr.update(choices=edit_choices)
            return status, labels_info, None, gr.update(choices=[])
        
        save_label_btn.click(
            save_label_and_refresh,
            inputs=[month_dropdown, flare_evidence, category_dropdown_label, reason_input_label],
            outputs=[label_chart_status, labels_info, monthly_timeline_plot, edit_month_dropdown]
        )
        
        clear_label_btn.click(
            clear_label_and_refresh,
            inputs=[month_dropdown],
            outputs=[label_chart_status, labels_info, monthly_timeline_plot, edit_month_dropdown]
        )
        
        # Edit functionality
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
        )
    
    return demo

if __name__ == "__main__":
    # Create app with command line arguments
    app = create_app_with_args()
    
    # Add monthly labelling methods to the app
    add_monthly_labelling_methods(PatientTimelineApp)
    
    # Create and launch the interface
    demo = create_interface()
    demo.launch()