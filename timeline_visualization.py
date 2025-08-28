import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import textwrap
from monthly_labelling import load_monthly_labels


def get_fixed_event_order():
    """
    Get the fixed order for event types on the y-axis.
    
    This ensures consistent ordering across all patients and views.
    Order from top to bottom:
    1. Imaging (top)
    2. Prescription
    3. Ambulatory Visit
    4. Physician Claim
    5. Hospital Admission
    6. Lab Test (bottom)
    
    Returns:
        list: Event types in the order they should appear (top to bottom)
    """
    return [
        'imaging',
        'prescription',
        'ambulatory_visit',
        'physician_claim',
        'hospital_admission',
        'lab_test'
    ]

def ensure_all_event_types(data):
    """
    Ensure all event types are present in the data for consistent y-axis.
    
    This function adds dummy (invisible) entries for any missing event types
    to maintain consistent y-axis ordering across all patients.
    
    Args:
        data (pd.DataFrame): Event data
        
    Returns:
        pd.DataFrame: Data with all event types present (real or dummy)
    """
    fixed_order = get_fixed_event_order()
    existing_types = data['event_type'].unique()
    
    # Find missing event types
    missing_types = [et for et in fixed_order if et not in existing_types]
    
    if missing_types:
        # Create dummy entries for missing types
        dummy_rows = []
        # Use the earliest date from the data for dummy entries
        dummy_date = data['start_date'].min() if not data.empty else pd.Timestamp.now()
        
        for event_type in missing_types:
            dummy_rows.append({
                'start_date': dummy_date,
                'end_date': dummy_date,  # Same date = invisible
                'event_type': event_type,
                'patient_id': data['patient_id'].iloc[0] if not data.empty else 0,
                'ibd_related': False,
                'is_dummy': True,
                'event_info': json.dumps({'dummy': True})
            })
        
        # Add dummy rows to data
        dummy_df = pd.DataFrame(dummy_rows)
        data = pd.concat([data, dummy_df], ignore_index=True)
    
    # Mark real data
    if 'is_dummy' not in data.columns:
        data['is_dummy'] = False
    
    return data





def get_label_mapping():
    """
    Get the label mapping dictionary for converting internal event names to display names.
    
    This function provides a centralized mapping between the internal event type names
    (used in the database/CSV) and the human-readable names displayed in the UI.
    
    Returns:
        dict: Mapping from internal names to display names
        
    Example:
        'ambulatory_visit' -> 'Ambulatory Visit'
        'lab_test' -> 'Lab Test'
    """
    return {
        'ambulatory_visit': 'Ambulatory Visit',
        'lab_test': 'Lab Test',
        'prescription': 'Prescription',
        'physician_claim': 'Physician Claim',
        'hospital_admission': 'Hospital Admission',
        'imaging': 'Imaging',
        'hospitalization': 'Hospitalization',
        'medication_change': 'Medication Change'
    }


def create_hover_data(data):
    """
    Create hover data for timeline (extracted for reuse).
    
    This function processes the event_info JSON data and creates formatted HTML
    hover text for each event in the timeline. It handles JSON parsing errors
    gracefully and formats long text with line wrapping.
    
    Args:
        data (pd.DataFrame): DataFrame containing event data with potential event_info column
        
    Returns:
        list: List of HTML-formatted hover text strings, one per row in data
        
    Processing:
        - Parses JSON from event_info column
        - Wraps long text values to prevent wide hover boxes
        - Includes source_dataset and ibd_related info if available
        - Falls back to basic info if JSON parsing fails
    """
    hover_data = []
    if 'event_info' in data.columns:
        try:
            # === Process Each Row ===
            for idx, row in data.iterrows():
                if row.get('is_dummy', False):
                    hover_data.append("")
                    continue
                try:
                    # === Parse JSON Event Info ===
                    # Handle both string JSON and already-parsed dict objects
                    info = json.loads(row['event_info']) if isinstance(row['event_info'], str) else row['event_info']
                    
                    # === Build Hover Text with Basic Info ===
                    hover_text = f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br>"
                    hover_text += f"<b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br>"
                    
                    # === Add Event Info Details ===
                    for key, value in info.items():
                        if key == 'dummy':
                            continue
                        if isinstance(value, str) and len(str(value)) > 40:
                            # Wrap long text values to prevent wide hover boxes
                            wrapped_value = "<br>".join(textwrap.wrap(str(value), width=40))
                            hover_text += f"<b>{key}:</b><br>{wrapped_value}<br>"
                        else:
                            hover_text += f"<b>{key}:</b> {value}<br>"
                    
                    # === Add Additional Row Data ===
                    if 'source_dataset' in row:
                        hover_text += f"<b>source_dataset:</b> {row['source_dataset']}<br>"
                    if 'ibd_related' in row:
                        hover_text += f"<b>ibd_related:</b> {row['ibd_related']}<br>"
                    
                    # Remove trailing <br> tag
                    hover_data.append(hover_text.rstrip('<br>'))
                    
                except (json.JSONDecodeError, TypeError):
                    # === Fallback for JSON Parse Errors ===
                    # Create basic hover text when JSON parsing fails
                    hover_text = f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br>"
                    hover_text += f"<b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br>"
                    hover_text += f"<b>event_type:</b> {row['event_type']}"
                    hover_data.append(hover_text)
                    
        except Exception as e:
            print(f"Error processing event info: {e}")
            # === Complete Fallback ===
            # Create basic hover data for all rows if processing completely fails
            hover_data = [f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br><b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br><b>event_type:</b> {row['event_type']}" 
                         for _, row in data.iterrows()]
    else:
        # === No Event Info Column ===
        # Create basic hover data when event_info column is missing
        hover_data = [f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br><b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br><b>event_type:</b> {row['event_type']}" 
                     for _, row in data.iterrows()]
    return hover_data


def process_lab_test_data(data):
    """
    Handle multiple lab tests on the same day with time offsets.
    
    When multiple lab tests occur on the same day, they would overlap in the
    timeline visualization. This function adds small time offsets (2 hours each)
    to separate them visually while maintaining their original date.
    
    Args:
        data (pd.DataFrame): Event data containing lab tests
        
    Returns:
        pd.DataFrame: Modified data with time offsets applied to lab tests
        
    Process:
        1. Filter to lab_test events only
        2. Group by date (ignoring time)
        3. For groups with multiple tests, add 2-hour incremental offsets
        4. Modify both start_date and end_date consistently
    """
    lab_data = data[(data['event_type'] == 'lab_test') & (data.get('is_dummy', False) == False)].copy()
    if not lab_data.empty:
        # === Group Lab Tests by Date ===
        # Create date-only column for grouping (ignoring time component)
        lab_data['date_only'] = lab_data['start_date'].dt.date
        
        # === Add Time Offsets for Same-Day Tests ===
        # For each date, add incremental hour offsets to lab tests
        for date, group in lab_data.groupby('date_only'):
            if len(group) > 1:  # Multiple lab tests on same day
                indices = group.index.tolist()
                for i, idx in enumerate(indices):
                    # === Apply 2-Hour Offset ===
                    # Add 2-hour offset for each subsequent lab test (0, 2, 4, 6 hours...)
                    hour_offset = i * 2
                    data.loc[idx, 'start_date'] = data.loc[idx, 'start_date'] + pd.Timedelta(hours=hour_offset)
                    data.loc[idx, 'end_date'] = data.loc[idx, 'start_date'] + pd.Timedelta(hours=hour_offset)
    
    return data


def handle_same_day_events(data):
    """
    Handle same-day events (extend end date by 1 day if start == end).
    
    In timeline visualizations, events with identical start and end dates
    appear as zero-width bars and are invisible. This function extends
    the end date by 1 day to make these events visible.
    
    Args:
        data (pd.DataFrame): Event data
        
    Returns:
        pd.DataFrame: Modified data with extended end dates for same-day events
        
    Note:
        This is applied after lab test processing to avoid interfering
        with the time offset calculations.
    """
    # === Identify Same-Day Events ===
    mask = (data['start_date'] == data['end_date']) & (data.get('is_dummy', False) == False)
    
    # === Extend End Date by 1 Day ===
    data.loc[mask, 'end_date'] += pd.Timedelta(days=1)
    return data


def add_flares_to_chart(app, fig, data):
    """
    Add flare periods to the chart.
    
    This function adds visual indicators for date-based flare periods that were
    manually marked by users. It creates red semi-transparent rectangles and
    triangle markers to show flare periods on the timeline.
    
    Args:
        app: Application instance containing flare data (app.ranges)
        fig: Plotly figure object to modify
        data: Event data for determining y-axis positioning
        
    Visual Elements Added:
        - Red semi-transparent rectangles spanning flare periods
        - Triangle markers at the top with hover information
        - Hover text showing flare details, categories, and reasons
    """
    if not app.ranges:
        return
    
    # === Get Label Mapping for Display ===
    label_mapping = get_label_mapping()
    
    # === Add Each Flare Period ===
    for i, flare_data in enumerate(app.ranges):
        # === Handle Both Old and New Flare Formats ===
        if len(flare_data) == 3:  # Old format: (start, end, reason)
            start_date, end_date, reason = flare_data
            categories = []
        else:  # New format: (start, end, categories, reason)
            start_date, end_date, categories, reason = flare_data
        
        # === Convert to Datetime Objects ===
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        
        # === Add Background Rectangle ===
        fig.add_vrect(
            x0=start_date, x1=end_date,
            fillcolor="red", opacity=0.3,
            layer="below", line_width=0,
        )
        
        # === Position Markers Above Event Types ===
        y_pos = len(data['event_type'].unique()) - 0.75
        
        # === Create Hover Text with Categories ===
        hover_text_parts = [f"<b>Flare:</b> {start_date.date()} to {end_date.date()}"]
        
        if categories:
            # Convert internal category names to readable labels
            readable_categories = [label_mapping.get(cat, cat.replace('_', ' ').title()) for cat in categories]
            hover_text_parts.append(f"<b>Categories:</b><br>{'<br>'.join(readable_categories)}")
        
        if reason:
            # Wrap long reasons to prevent wide hover boxes
            wrapped_reason = "<br>".join(textwrap.wrap(reason, width=50))
            hover_text_parts.append(f"<b>Reason:</b><br>{wrapped_reason}")
        
        hover_text = "<br><br>".join(hover_text_parts)
        
        # === Add Triangle Markers ===
        fig.add_trace(
            go.Scatter(
                x=[start_date, end_date], 
                y=[y_pos, y_pos],
                mode='markers',
                marker=dict(size=10, color='LightSeaGreen', symbol='triangle-down'),
                hoverinfo='text',
                hovertext=[hover_text, hover_text],
                showlegend=False,
                name=f'Flare {i+1} Boundaries'
            )
        )
    
    # === Update Y-Axis Range to Accommodate Flare Markers ===
    unique_event_types = data['event_type'].unique()
    fig.update_layout(
        yaxis=dict(
            categoryorder='array',
            categoryarray=list(unique_event_types),
            range=[-0.75, len(unique_event_types)+0.06],
            # Preserve the custom tick labels that were set earlier
            tickvals=list(unique_event_types),
            ticktext=[fig.layout.yaxis.ticktext[i] if fig.layout.yaxis.ticktext else event_type 
                     for i, event_type in enumerate(unique_event_types)]
        )
    )


def add_monthly_flares_to_timeline(app, fig, data):
    """
    Add monthly flares from labelling mode to the timeline.
    
    This function adds visual indicators for monthly flare labels created
    in the labelling mode. These are distinct from date-based flares and
    represent entire months marked as having flare evidence.
    
    Args:
        app: Application instance with current patient ID
        fig: Plotly figure object to modify
        data: Event data for determining y-axis positioning
        
    Visual Elements Added:
        - Red semi-transparent rectangles spanning entire months
        - Triangle markers with hover information
        - Different y-position from date-based flares for distinction
    """
    if app.current_patient_id is None:
        return
    
    # === Load Monthly Labels ===
    monthly_labels = load_monthly_labels(app)
    
    if not monthly_labels:
        return
    
    # === Get Label Mapping for Display ===
    label_mapping = get_label_mapping()
    
    # === Add Each Monthly Flare ===
    for month_period_str, label_data in monthly_labels.items():
        if label_data.get('evidence') != 'Yes':
            continue  # Skip months without flare evidence
        
        try:
            # === Convert Period String to Date Range ===
            period = pd.Period(month_period_str)
            start_date = period.start_time
            end_date = period.end_time
            
            # === Add Background Rectangle for Entire Month ===
            fig.add_vrect(
                x0=start_date, 
                x1=end_date,
                fillcolor="red",  # Same color as date-based flares
                opacity=0.3,
                layer="below", 
                line_width=0,
            )
            
            # === Position Markers (Different from Date-Based Flares) ===
            y_pos = len(data['event_type'].unique()) - 0.5
            
            # === Create Hover Text for Monthly Flares ===
            hover_text_parts = [f"<b>Monthly Flare:</b> {period.strftime('%B %Y')}"]
            
            categories = label_data.get('categories', [])
            if categories:
                # Convert internal category names to readable labels
                readable_categories = [label_mapping.get(cat, cat.replace('_', ' ').title()) for cat in categories]
                hover_text_parts.append(f"<b>Categories:</b><br>{'<br>'.join(readable_categories)}")
            
            reason = label_data.get('reason', '')
            if reason:
                # Wrap long reasons to prevent wide hover boxes
                wrapped_reason = "<br>".join(textwrap.wrap(reason, width=50))
                hover_text_parts.append(f"<b>Reason:</b><br>{wrapped_reason}")
            
            hover_text = "<br><br>".join(hover_text_parts)
            
            # === Add Marker at the Start of the Month ===
            fig.add_trace(
                go.Scatter(
                    x=[start_date], 
                    y=[y_pos],
                    mode='markers',
                    marker=dict(size=12, color='LightSeaGreen', symbol='triangle-down'),
                    hoverinfo='text',
                    hovertext=[hover_text],
                    showlegend=False,
                    name=f'Monthly Flare {period.strftime("%B %Y")}'
                )
            )
            
        except Exception as e:
            print(f"Error adding monthly flare for {month_period_str}: {e}")
            continue
    
    # === Update Y-Axis Range to Accommodate Both Types of Flare Markers ===
    unique_event_types = data['event_type'].unique()
    fig.update_layout(
        yaxis=dict(
            categoryorder='array',
            categoryarray=list(unique_event_types),
            range=[-0.75, len(unique_event_types)+0.06],
            # Preserve the custom tick labels that were set earlier
            tickvals=list(unique_event_types),
            ticktext=[fig.layout.yaxis.ticktext[i] if fig.layout.yaxis.ticktext else event_type 
                     for i, event_type in enumerate(unique_event_types)]
        )
    )


def create_main_timeline(app):
    """
    Create the main plotly timeline figure for the Timeline Viewer tab.
    
    This is the primary timeline visualization function that creates a comprehensive
    view of all events for a patient. It processes the data, creates hover information,
    and adds both types of flare indicators.
    
    Args:
        app: Application instance containing current patient data and flare information
        
    Returns:
        plotly.graph_objects.Figure: Complete timeline figure with events and flares
        
    Features:
        - Processes lab test overlaps with time offsets
        - Handles same-day events by extending duration
        - Creates rich hover information from event_info JSON
        - Adds date-based and monthly flare indicators
        - Uses readable event type labels
        - Larger height (800px) for comprehensive view
    """
    if app.current_patient_data is None:
        return None
    
    # === Prepare Data Copy for Processing ===
    data = app.current_patient_data.copy()
    data = ensure_all_event_types(data)
    
    # === Process Lab Tests ===
    # Handle multiple lab tests on same day with time offsets
    data = process_lab_test_data(data)
    
    # === Handle Same-Day Events ===
    # Extend end dates for zero-duration events to make them visible
    data = handle_same_day_events(data)
    
    # === Create Hover Information ===
    # Parse event_info JSON and create formatted hover text
    hover_data = create_hover_data(data)
    fixed_order = get_fixed_event_order()
    label_mapping = get_label_mapping()
    
    # === Create Base Timeline Figure ===
    fig = px.timeline(
        data,
        x_start="start_date",
        x_end="end_date",
        y="event_type",
        color="event_type",
        hover_name=None,
        category_orders={"event_type": fixed_order}  # *** ADD THIS LINE ***
    )
    
    
    # === Update Traces with Custom Hover Info ===
    for i, trace in enumerate(fig.data):
        # === Get Hover Data for This Event Type ===
        event_type = trace.name
        event_mask = data['event_type'] == event_type
        trace_hover_data = [hover_data[j] for j, mask_val in enumerate(event_mask) if mask_val]

        trace_data = data[event_mask]
        is_all_dummy = trace_data.get('is_dummy', False).all() if not trace_data.empty else False

        
        if is_all_dummy:
            # *** ADD THIS BLOCK - make dummy traces invisible ***
            trace.update(
                hovertemplate='<extra></extra>',
                hovertext=[],
                width=0,
                opacity=0,
                showlegend=False
            )
        else:
            trace.update(
                hovertemplate='%{hovertext}<extra></extra>',
                hovertext=trace_hover_data,
                width=0.9,
            )
    
    # === Create Custom Y-Axis Labels ===
    # unique_event_types = data['event_type'].unique()
    label_mapping = get_label_mapping()
    
    # Convert internal event names to readable display names
    custom_labels = [label_mapping.get(event_type, event_type.replace('_', ' ').title()) 
                    for event_type in fixed_order]
    
    # === Update Layout with Comprehensive Settings ===
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Event",
        showlegend=False,
        xaxis=dict(
            # Add padding around the data range for better visualization
            range=[
                data['start_date'].min() - pd.Timedelta(days=10),
                data['end_date'].max() + pd.Timedelta(days=10)
            ]
        ),
        bargap=0.1,
        bargroupgap=0.0,
        autosize=True,
        margin=dict(l=50, r=50, t=50, b=50),
        height=800,  # Increased height for comprehensive timeline view
        hovermode='closest',
        yaxis=dict(
            ticktext=custom_labels,
            tickvals=fixed_order,
            categoryorder='array',
            categoryarray=fixed_order,
            range=[-0.75, len(fixed_order) + 0.06]
        )
    )
    
    # === Add Flare Visualizations ===
    # Add original flare periods (date-based flares from manual selection)
    add_flares_to_chart(app, fig, data)
    
    # Add monthly flares from labelling mode
    add_monthly_flares_to_timeline(app, fig, data)
    
    # === Store Figure in App Instance ===
    app.fig = fig
    return fig


def create_monthly_timeline(app, selected_month, view_offset=0):
    """
    Create timeline for a specific month with navigation offset.
    
    This function creates a focused monthly view for the labelling mode.
    It shows one month at a time with consistent y-axis layout and
    handles months with no events by using dummy data.
    
    Args:
        app: Application instance containing current patient data
        selected_month (str): Month being labeled in "Month YYYY" format
        view_offset (int): Offset from selected month for viewing (-1, 0, +1, etc.)
        
    Returns:
        plotly.graph_objects.Figure: Monthly timeline figure with flare highlighting
        
    Features:
        - Consistent y-axis across all months (using dummy data for missing event types)
        - Month highlighting with blue background
        - Red highlighting for months with flare evidence
        - Navigation between months while maintaining labeling context
        - Smaller height (600px) for focused monthly view
    """
    if app.current_patient_data is None:
        return None
    
    # === Parse Selected Month and Calculate View Period ===
    try:
        selected_period = pd.to_datetime(selected_month, format='%B %Y').to_period('M')
        
        # === Apply View Offset for Navigation ===
        # This allows viewing different months while keeping the same month selected for labeling
        view_period = selected_period + view_offset
        
        # === Define Month Date Range ===
        start_date = view_period.start_time
        end_date = view_period.end_time
        
        # === Filter Data for View Period ===
        filtered_data = app.current_patient_data[
            (app.current_patient_data['start_date'] <= end_date) & 
            (app.current_patient_data['end_date'] >= start_date)
        ].copy()
        
        # === Ensure Consistent Y-Axis Across All Months ===
        # Always show all event types even if not present in this month
        fixed_order = get_fixed_event_order()
        
        # === Create Dummy Data for Missing Event Types ===
        dummy_data = []
        for event_type in fixed_order:
            if event_type not in filtered_data['event_type'].values:
                dummy_data.append({
                    'start_date': start_date,
                    'end_date': start_date,
                    'event_type': event_type,
                    'is_dummy': True,
                    'patient_id': app.current_patient_id,
                    'ibd_related': False,
                    'event_info': json.dumps({'dummy': True})
                })
        
        # === Combine Real and Dummy Data ===
        if dummy_data:
            dummy_df = pd.DataFrame(dummy_data)
            if not filtered_data.empty:
                filtered_data['is_dummy'] = False
                data = pd.concat([filtered_data, dummy_df], ignore_index=True)
            else:
                data = dummy_df
        else:
            if not filtered_data.empty:
                filtered_data['is_dummy'] = False
                data = filtered_data
            else:
                # === Create Completely Empty Dataset ===
                # For months with no events at all
                data = pd.DataFrame({
                    'start_date': [start_date] * len(all_event_types),
                    'end_date': [start_date] * len(all_event_types),
                    'event_type': all_event_types,
                    'is_dummy': [True] * len(all_event_types)
                })
        
        # === Process Real Data Only ===
        real_data = data[data.get('is_dummy', False) == False]
        if not real_data.empty:
            # Process lab tests with time offsets
            data = process_lab_test_data(data)
            
            # === Handle Same-Day Events (Real Data Only) ===
            real_mask = (data['start_date'] == data['end_date']) & (data.get('is_dummy', False) == False)
            data.loc[real_mask, 'end_date'] += pd.Timedelta(days=1)
        
        # === Create Hover Data ===
        hover_data = []
        for idx, row in data.iterrows():
            if row.get('is_dummy', False):
                # Empty hover for dummy data (invisible elements)
                hover_data.append("")
            else:
                # === Create Hover Text for Real Events ===
                if 'event_info' in row and pd.notna(row['event_info']):
                    try:
                        # Parse and format event_info JSON
                        info = json.loads(row['event_info']) if isinstance(row['event_info'], str) else row['event_info']
                        hover_text = f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br>"
                        hover_text += f"<b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br>"
                        
                        for key, value in info.items():
                            if isinstance(value, str) and len(str(value)) > 40:
                                wrapped_value = "<br>".join(textwrap.wrap(str(value), width=40))
                                hover_text += f"<b>{key}:</b><br>{wrapped_value}<br>"
                            else:
                                hover_text += f"<b>{key}:</b> {value}<br>"
                        
                        hover_data.append(hover_text.rstrip('<br>'))
                    except:
                        # Fallback for JSON parsing errors
                        hover_text = f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br>"
                        hover_text += f"<b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br>"
                        hover_text += f"<b>event_type:</b> {row['event_type']}"
                        hover_data.append(hover_text)
                else:
                    # Basic hover text when no event_info available
                    hover_text = f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br>"
                    hover_text += f"<b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br>"
                    hover_text += f"<b>event_type:</b> {row['event_type']}"
                    hover_data.append(hover_text)
        
        # === Create Timeline Figure ===
        fig = px.timeline(
            data,
            x_start="start_date",
            x_end="end_date",
            y="event_type",
            color="event_type",
            hover_name=None,
            category_orders={"event_type": fixed_order} 
        )
        
        # === Update Traces - Handle Dummy vs Real Data ===
        for i, trace in enumerate(fig.data):
            event_type = trace.name
            event_mask = data['event_type'] == event_type
            trace_hover_data = [hover_data[j] for j, mask_val in enumerate(event_mask) if mask_val]
            
            # === Check Data Composition ===
            trace_data = data[event_mask]
            has_dummy = trace_data.get('is_dummy', False).any()
            has_real = (~trace_data.get('is_dummy', True)).any()
            
            if has_dummy and not has_real:
                # === Make Completely Dummy Traces Invisible ===
                trace.update(
                    hovertemplate='<extra></extra>',
                    hovertext=[],
                    width=0,
                    opacity=0,
                    showlegend=False
                )
            else:
                # === Style Real Data Traces ===
                trace.update(
                    hovertemplate='%{hovertext}<extra></extra>',
                    hovertext=trace_hover_data,
                    width=0.9,
                )
        
        # === Create Custom Labels for Consistent Y-Axis ===
        label_mapping = get_label_mapping()
        all_custom_labels = [label_mapping.get(event_type, event_type.replace('_', ' ').title()) 
                           for event_type in fixed_order]
        
        # === Update Layout for Monthly View ===
        fig.update_layout(
            xaxis_title="Time",
            yaxis_title="Event",
            showlegend=False,
            xaxis=dict(
                # Focus on the single month with small padding
                range=[
                    start_date - pd.Timedelta(days=2),
                    end_date + pd.Timedelta(days=2)
                ]
            ),
            bargap=0.1,
            bargroupgap=0.0,
            autosize=True,
            margin=dict(l=50, r=50, t=50, b=50),
            height=600,  # Smaller height for focused monthly view
            hovermode='closest',
            yaxis=dict(
                ticktext=all_custom_labels,
                tickvals=fixed_order, 
                categoryorder='array',
                categoryarray=fixed_order 
            )
        )
        
        # === Add Month Highlighting ===
        # Blue background to highlight the current view month
        fig.add_vrect(
            x0=start_date,
            x1=end_date,
            fillcolor="lightblue",
            opacity=0.1,
            layer="below",
            line_width=2,
            line_color="blue"
        )
        
        # === Add Monthly Flare Highlighting ===
        # Red background if this month has been marked as having flare evidence
        monthly_labels = load_monthly_labels(app)
        view_period_str = str(view_period)
        if view_period_str in monthly_labels and monthly_labels[view_period_str].get('evidence') == 'Yes':
            fig.add_vrect(
                x0=start_date,
                x1=end_date,
                fillcolor="red",
                opacity=0.3,
                layer="below",
                line_width=0,
            )
        
        return fig
        
    except Exception as e:
        print(f"Error creating monthly timeline: {e}")
        return None