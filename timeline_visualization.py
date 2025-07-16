import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import textwrap
from monthly_labelling import load_monthly_labels


def get_label_mapping():
    """Get the label mapping dictionary"""
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
    """Create hover data for timeline (extracted for reuse)"""
    hover_data = []
    if 'event_info' in data.columns:
        try:
            for idx, row in data.iterrows():
                try:
                    info = json.loads(row['event_info']) if isinstance(row['event_info'], str) else row['event_info']
                    hover_text = f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br>"
                    hover_text += f"<b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br>"
                    
                    for key, value in info.items():
                        if isinstance(value, str) and len(str(value)) > 40:
                            wrapped_value = "<br>".join(textwrap.wrap(str(value), width=40))
                            hover_text += f"<b>{key}:</b><br>{wrapped_value}<br>"
                        else:
                            hover_text += f"<b>{key}:</b> {value}<br>"
                    
                    if 'source_dataset' in row:
                        hover_text += f"<b>source_dataset:</b> {row['source_dataset']}<br>"
                    if 'ibd_related' in row:
                        hover_text += f"<b>ibd_related:</b> {row['ibd_related']}<br>"
                    
                    hover_data.append(hover_text.rstrip('<br>'))
                except (json.JSONDecodeError, TypeError):
                    hover_text = f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br>"
                    hover_text += f"<b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br>"
                    hover_text += f"<b>event_type:</b> {row['event_type']}"
                    hover_data.append(hover_text)
        except Exception as e:
            print(f"Error processing event info: {e}")
            hover_data = [f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br><b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br><b>event_type:</b> {row['event_type']}" 
                         for _, row in data.iterrows()]
    else:
        hover_data = [f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br><b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br><b>event_type:</b> {row['event_type']}" 
                     for _, row in data.iterrows()]
    return hover_data


def process_lab_test_data(data):
    """Handle multiple lab tests on the same day with time offsets"""
    lab_data = data[data['event_type'] == 'lab_test'].copy()
    if not lab_data.empty:
        # Group lab tests by date (ignoring time)
        lab_data['date_only'] = lab_data['start_date'].dt.date
        
        # For each date, add incremental hour offsets to lab tests
        for date, group in lab_data.groupby('date_only'):
            if len(group) > 1:  # Multiple lab tests on same day
                indices = group.index.tolist()
                for i, idx in enumerate(indices):
                    # Add 2-hour offset for each subsequent lab test
                    hour_offset = i * 2
                    data.loc[idx, 'start_date'] = data.loc[idx, 'start_date'] + pd.Timedelta(hours=hour_offset)
                    data.loc[idx, 'end_date'] = data.loc[idx, 'start_date'] + pd.Timedelta(hours=hour_offset)
    
    return data


def handle_same_day_events(data):
    """Handle same-day events (extend end date by 1 day if start == end)"""
    mask = data['start_date'] == data['end_date']
    data.loc[mask, 'end_date'] += pd.Timedelta(days=1)
    return data


def add_flares_to_chart(app, fig, data):
    """Add flare periods to the chart"""
    if not app.ranges:
        return
    
    # Create label mapping for display
    label_mapping = get_label_mapping()
    
    # Add flare periods
    for i, flare_data in enumerate(app.ranges):
        # Handle both old and new format
        if len(flare_data) == 3:  # Old format: (start, end, reason)
            start_date, end_date, reason = flare_data
            categories = []
        else:  # New format: (start, end, categories, reason)
            start_date, end_date, categories, reason = flare_data
        
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
        
        # Create hover text with categories
        hover_text_parts = [f"<b>Flare:</b> {start_date.date()} to {end_date.date()}"]
        
        if categories:
            # Convert categories to readable labels
            readable_categories = [label_mapping.get(cat, cat.replace('_', ' ').title()) for cat in categories]
            hover_text_parts.append(f"<b>Categories:</b><br>{'<br>'.join(readable_categories)}")
        
        if reason:
            wrapped_reason = "<br>".join(textwrap.wrap(reason, width=50))
            hover_text_parts.append(f"<b>Reason:</b><br>{wrapped_reason}")
        
        hover_text = "<br><br>".join(hover_text_parts)
        
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
    
    # Update y-axis range to accommodate flare markers, but preserve custom labels
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
    """Add monthly flares from labelling mode to the timeline"""
    if app.current_patient_id is None:
        return
    
    # Load monthly labels
    monthly_labels = load_monthly_labels(app)
    
    if not monthly_labels:
        return
    
    # Create label mapping for display
    label_mapping = get_label_mapping()
    
    # Add monthly flares
    for month_period_str, label_data in monthly_labels.items():
        if label_data.get('evidence') != 'Yes':
            continue
        
        try:
            # Convert period string back to period object
            period = pd.Period(month_period_str)
            start_date = period.start_time
            end_date = period.end_time
            
            # Add rectangle for monthly flare
            fig.add_vrect(
                x0=start_date, 
                x1=end_date,
                fillcolor="red",  # Different color from regular flares
                opacity=0.3,
                layer="below", 
                line_width=0,
            )
            
            # Add markers for monthly flares
            y_pos = len(data['event_type'].unique()) - 0.5
            
            # Create hover text for monthly flares
            hover_text_parts = [f"<b>Monthly Flare:</b> {period.strftime('%B %Y')}"]
            
            categories = label_data.get('categories', [])
            if categories:
                # Convert categories to readable labels
                readable_categories = [label_mapping.get(cat, cat.replace('_', ' ').title()) for cat in categories]
                hover_text_parts.append(f"<b>Categories:</b><br>{'<br>'.join(readable_categories)}")
            
            reason = label_data.get('reason', '')
            if reason:
                wrapped_reason = "<br>".join(textwrap.wrap(reason, width=50))
                hover_text_parts.append(f"<b>Reason:</b><br>{wrapped_reason}")
            
            hover_text = "<br><br>".join(hover_text_parts)
            
            # Add marker at the start of the month
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
    
    # Update y-axis range to accommodate both types of flare markers
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
    """Create the plotly timeline figure"""
    if app.current_patient_data is None:
        return None
    
    # Handle same-day events and lab tests
    data = app.current_patient_data.copy()
    
    # Process lab tests
    data = process_lab_test_data(data)
    
    # Handle same-day events
    data = handle_same_day_events(data)
    
    # Parse event_info for hover data
    hover_data = create_hover_data(data)
    
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
    
    # Get unique event types and create custom labels
    unique_event_types = data['event_type'].unique()
    
    # Create label mapping
    label_mapping = get_label_mapping()
    
    # Create custom labels for the event types present in data
    custom_labels = [label_mapping.get(event_type, event_type.replace('_', ' ').title()) 
                    for event_type in unique_event_types]
    
    # Update layout with larger height
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
        height=800,  # Increased height for larger timeline
        hovermode='closest',
        yaxis=dict(
            ticktext=custom_labels,
            tickvals=list(unique_event_types)
        )
    )
    
    # Add original flare periods (date-based flares)
    add_flares_to_chart(app, fig, data)
    
    # Add monthly flares from labelling mode
    add_monthly_flares_to_timeline(app, fig, data)
    
    app.fig = fig
    return fig


def create_monthly_timeline(app, selected_month, view_offset=0):
    """Create timeline for a specific month with navigation offset"""
    if app.current_patient_data is None:
        return None
    
    # Parse the selected month
    try:
        selected_period = pd.to_datetime(selected_month, format='%B %Y').to_period('M')
        
        # Apply view offset for navigation
        view_period = selected_period + view_offset
        
        # Filter data for just the view period (one month)
        start_date = view_period.start_time
        end_date = view_period.end_time
        
        filtered_data = app.current_patient_data[
            (app.current_patient_data['start_date'] <= end_date) & 
            (app.current_patient_data['end_date'] >= start_date)
        ].copy()
        
        # Always ensure all event types are represented for consistent y-axis
        all_event_types = ['ambulatory_visit', 'lab_test', 'prescription', 'physician_claim', 'hospital_admission', 'imaging']
        
        # Create dummy invisible data for missing event types
        dummy_data = []
        for event_type in all_event_types:
            if event_type not in filtered_data['event_type'].values:
                dummy_data.append({
                    'start_date': start_date,
                    'end_date': start_date,  # Zero-width invisible bar
                    'event_type': event_type,
                    'is_dummy': True
                })
        
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
                # Create completely empty dataset with all event types
                data = pd.DataFrame({
                    'start_date': [start_date] * len(all_event_types),
                    'end_date': [start_date] * len(all_event_types),
                    'event_type': all_event_types,
                    'is_dummy': [True] * len(all_event_types)
                })
        
        # Handle multiple lab tests on the same day with time offsets (only for real data)
        real_data = data[data.get('is_dummy', False) == False]
        if not real_data.empty:
            data = process_lab_test_data(data)
            
            # Handle same-day events (only for real data)
            real_mask = (data['start_date'] == data['end_date']) & (data.get('is_dummy', False) == False)
            data.loc[real_mask, 'end_date'] += pd.Timedelta(days=1)
        
        # Create hover data
        hover_data = []
        for idx, row in data.iterrows():
            if row.get('is_dummy', False):
                hover_data.append("")  # Empty hover for dummy data
            else:
                if 'event_info' in row and pd.notna(row['event_info']):
                    try:
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
                        hover_text = f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br>"
                        hover_text += f"<b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br>"
                        hover_text += f"<b>event_type:</b> {row['event_type']}"
                        hover_data.append(hover_text)
                else:
                    hover_text = f"<b>start_date:</b> {row['start_date'].strftime('%Y-%m-%d')}<br>"
                    hover_text += f"<b>end_date:</b> {row['end_date'].strftime('%Y-%m-%d')}<br>"
                    hover_text += f"<b>event_type:</b> {row['event_type']}"
                    hover_data.append(hover_text)
        
        # Create timeline figure
        fig = px.timeline(
            data,
            x_start="start_date",
            x_end="end_date",
            y="event_type",
            color="event_type",
            hover_name=None
        )
        
        # Update traces - make dummy data invisible
        for i, trace in enumerate(fig.data):
            event_type = trace.name
            event_mask = data['event_type'] == event_type
            trace_hover_data = [hover_data[j] for j, mask_val in enumerate(event_mask) if mask_val]
            
            # Check if this trace contains dummy data
            trace_data = data[event_mask]
            has_dummy = trace_data.get('is_dummy', False).any()
            has_real = (~trace_data.get('is_dummy', True)).any()
            
            if has_dummy and not has_real:
                # Make completely dummy traces invisible
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
        
        # Create custom labels for all event types (consistent y-axis)
        label_mapping = get_label_mapping()
        all_custom_labels = [label_mapping.get(event_type, event_type.replace('_', ' ').title()) 
                           for event_type in all_event_types]
        
        # Update layout to show only one month with all event types
        fig.update_layout(
            xaxis_title="Time",
            yaxis_title="Event",
            showlegend=False,
            xaxis=dict(
                range=[
                    start_date - pd.Timedelta(days=2),
                    end_date + pd.Timedelta(days=2)
                ]
            ),
            bargap=0.1,
            bargroupgap=0.0,
            autosize=True,
            margin=dict(l=50, r=50, t=50, b=50),
            height=600,
            hovermode='closest',
            yaxis=dict(
                ticktext=all_custom_labels,
                tickvals=all_event_types,
                categoryorder='array',
                categoryarray=all_event_types
            )
        )
        
        # Add month highlight for the view period
        fig.add_vrect(
            x0=start_date,
            x1=end_date,
            fillcolor="lightblue",
            opacity=0.1,
            layer="below",
            line_width=2,
            line_color="blue"
        )
        
        # Add monthly flare highlighting
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