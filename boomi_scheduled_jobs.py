import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import re
from collections import defaultdict
import pytz

def color_enabled(val):
    # Handle both boolean and string values
    if isinstance(val, str):
        color = 'green' if val.lower() == 'true' else 'red'
    else:
        color = 'green' if val == True else 'red'
    return f'background-color: {color}'

def clear_cache():
    st.cache_data.clear()

def parse_cron_time_range(time_str):
    """Parse time ranges like '7-7/1', '15-22', '0-59/30' etc."""
    times = []
    if time_str == '*':
        return list(range(24)) if 'hour' in str(time_str) else list(range(60))
    
    # Handle ranges with steps
    if '/' in time_str:
        base, step = time_str.split('/')
        step = int(step)
        if '-' in base:
            start, end = map(int, base.split('-'))
            times.extend(range(start, end + 1, step))
        else:
            start = int(base)
            times.append(start)
    elif '-' in time_str:
        start, end = map(int, time_str.split('-'))
        times.extend(range(start, end + 1))
    elif ',' in time_str:
        times.extend(map(int, time_str.split(',')))
    else:
        times.append(int(time_str))
    
    return times

def parse_job_schedule(job):
    """Parse job schedule and return execution times"""
    try:
        hours_str = str(job.get('hours', '*'))
        minutes_str = str(job.get('minutes', '0'))
        
        hours = parse_cron_time_range(hours_str)
        minutes = parse_cron_time_range(minutes_str)
        
        # Create all time combinations
        times = []
        for hour in hours:
            for minute in minutes:
                times.append((hour, minute))
        
        return times
    except:
        return [(0, 0)]  # Default fallback

def convert_utc_to_mst(hour, minute):
    """Convert UTC time to MST (UTC-7)"""
    utc_time = datetime(2025, 1, 1, hour, minute, tzinfo=pytz.UTC)
    mst_tz = pytz.timezone('US/Mountain')
    mst_time = utc_time.astimezone(mst_tz)
    return mst_time.hour, mst_time.minute

def format_time_12hour(hour, minute):
    """Format time in 12-hour format with AM/PM"""
    period = "AM" if hour < 12 else "PM"
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour}:{minute:02d} {period}"

def categorize_jobs(df):
    """Categorize jobs as recurring/continuous vs scheduled"""
    recurring_jobs = []
    scheduled_jobs = []
    
    for _, job in df.iterrows():
        times = parse_job_schedule(job)
        
        # Consider recurring if more than 8 executions per day or very frequent
        if len(times) > 8 or any('/' in str(job.get(col, '')) for col in ['hours', 'minutes']):
            recurring_jobs.append(job)
        else:
            scheduled_jobs.append(job)
    
    return recurring_jobs, scheduled_jobs

def create_timeline_view(jobs, job_type="Scheduled"):
    """Create timeline visualization for jobs"""
    if not jobs:
        return
    
    st.subheader(f"{job_type} Jobs Timeline (MST)")
    
    # Group jobs by time
    time_groups = defaultdict(list)
    
    for job in jobs:
        times = parse_job_schedule(job)
        for hour, minute in times:
            mst_hour, mst_minute = convert_utc_to_mst(hour, minute)
            time_key = (mst_hour, mst_minute)
            time_groups[time_key].append(job)
    
    # Sort times chronologically
    sorted_times = sorted(time_groups.keys())
    
    for hour, minute in sorted_times:
        time_str = format_time_12hour(hour, minute)
        jobs_at_time = time_groups[(hour, minute)]
        
        st.write(f"**{time_str}**")
        
        # Create columns for job status boxes
        cols = st.columns(min(len(jobs_at_time), 3))
        
        for idx, job in enumerate(jobs_at_time):
            col_idx = idx % 3
            with cols[col_idx]:
                status_color = "🟢" if is_job_enabled(job) else "🔴"
                job_name = job['Name'][:40] + "..." if len(job['Name']) > 40 else job['Name']
                # Add full name as tooltip using title attribute
                full_name = job['Name']
                st.markdown(f'<div title="{full_name}">{status_color} {job_name}</div>', unsafe_allow_html=True)
        
        st.write("---")

def parse_recurring_pattern_description(job):
    """Parse recurring job patterns into human-readable descriptions"""
    hours_str = str(job.get('hours', '*'))
    minutes_str = str(job.get('minutes', '0'))
    
    # Parse hour ranges - handle complex patterns like "7-7/1"
    if hours_str == '*' or hours_str == '0-23':
        hour_desc = "all day"
        start_hour = 0
        end_hour = 23
    elif '-' in hours_str:
        # Handle patterns like "7-7/1" or "15-22"
        base_part = hours_str.split('/')[0] if '/' in hours_str else hours_str
        parts = base_part.split('-')
        if len(parts) == 2:
            try:
                start_hour = int(parts[0])
                end_hour = int(parts[1])
                
                # Convert to 12-hour format for description
                start_12h = format_time_12hour(start_hour, 0).split(':')[0] + format_time_12hour(start_hour, 0)[-2:]
                end_12h = format_time_12hour(end_hour, 59).split(':')[0] + format_time_12hour(end_hour, 59)[-2:]
                hour_desc = f"from {start_12h} to {end_12h}"
            except ValueError:
                # Fallback for unparseable patterns
                hour_desc = f"during hours {hours_str}"
        else:
            hour_desc = f"during hours {hours_str}"
    else:
        try:
            hour_val = int(hours_str)
            hour_desc = f"at {hour_val} o'clock"
        except ValueError:
            hour_desc = f"during hours {hours_str}"
    
    # Parse minute patterns
    if minutes_str == '*':
        minute_desc = "every minute"
    elif '/' in minutes_str:
        # Handle patterns like "0-59/2", "0-59/30", etc.
        try:
            base, interval = minutes_str.split('/')
            interval = int(interval)
            
            if interval == 1:
                minute_desc = "once a minute"
            elif interval == 2:
                minute_desc = "once every two minutes"
            elif interval == 5:
                minute_desc = "once every five minutes"
            elif interval == 10:
                minute_desc = "once every ten minutes"
            elif interval == 15:
                minute_desc = "once every fifteen minutes"
            elif interval == 30:
                minute_desc = "once every thirty minutes"
            elif interval == 60:
                minute_desc = "once an hour"
            else:
                minute_desc = f"once every {interval} minutes"
        except ValueError:
            minute_desc = f"with pattern {minutes_str}"
    elif '-' in minutes_str:
        # Handle ranges like "0-30"
        minute_desc = f"every minute during {minutes_str}"
    elif ',' in minutes_str:
        # Handle specific minutes like "0,15,30,45"
        mins = minutes_str.split(',')
        if len(mins) <= 3:
            minute_desc = f"at minutes {minutes_str}"
        else:
            minute_desc = f"at {len(mins)} specific times"
    else:
        # Single minute value
        try:
            min_val = int(minutes_str)
            minute_desc = f"at minute {min_val}"
        except ValueError:
            minute_desc = f"with minute pattern {minutes_str}"
    
    # Combine descriptions intelligently
    if hour_desc == "all day":
        if minute_desc.startswith("once a minute"):
            return "Once a minute"
        elif minute_desc.startswith("once every"):
            return minute_desc.capitalize()
        else:
            return f"{minute_desc.capitalize()} {hour_desc}"
    else:
        if minute_desc.startswith("once a minute"):
            return f"Once a minute {hour_desc}"
        elif minute_desc.startswith("once every"):
            return f"{minute_desc.capitalize()} {hour_desc}"
        else:
            return f"{minute_desc.capitalize()} {hour_desc}"

def create_recurring_timeline_view(jobs):
    """Create timeline visualization for recurring jobs"""
    if not jobs:
        return
    
    st.subheader("Recurring/Continuous Jobs (MST)")
    st.write("*Jobs that run frequently (>8 times/day or with step intervals)*")
    
    # Group recurring jobs by their human-readable pattern
    pattern_groups = defaultdict(list)
    
    for job in jobs:
        pattern_desc = parse_recurring_pattern_description(job)
        pattern_groups[pattern_desc].append(job)
    
    # Sort patterns by frequency (more frequent first)
    def get_frequency_score(pattern):
        if "once a minute" in pattern.lower():
            return 1000
        elif "once every two minutes" in pattern.lower():
            return 500
        elif "once every" in pattern.lower() and "minutes" in pattern.lower():
            # Extract number for sorting
            import re
            numbers = re.findall(r'\d+', pattern)
            if numbers:
                return 1000 / int(numbers[0])
            return 100
        elif "once every" in pattern.lower() and "hour" in pattern.lower():
            return 10
        else:
            return 1
    
    sorted_patterns = sorted(pattern_groups.keys(), key=get_frequency_score, reverse=True)
    
    for pattern in sorted_patterns:
        jobs_in_pattern = pattern_groups[pattern]
        
        st.write(f"**{pattern}**")
        
        # Create columns for job status boxes
        cols = st.columns(min(len(jobs_in_pattern), 3))
        
        for idx, job in enumerate(jobs_in_pattern):
            col_idx = idx % 3
            with cols[col_idx]:
                status_color = "🟢" if is_job_enabled(job) else "🔴"
                job_name = job['Name'][:40] + "..." if len(job['Name']) > 40 else job['Name']
                # Add full name as tooltip
                full_name = job['Name']
                st.markdown(f'<div title="{full_name}">{status_color} {job_name}</div>', unsafe_allow_html=True)
        
        st.write("---")

def is_job_enabled(job):
    """Check if a job is enabled, handling both string and boolean values"""
    enabled_val = job.get('enabled', False)
    if isinstance(enabled_val, str):
        return enabled_val.lower() == 'true'
    return bool(enabled_val)

def show_job_statistics(df):
    """Display job statistics dashboard"""
    total_jobs = len(df)
    enabled_jobs = 0
    disabled_jobs = 0
    
    # Count enabled/disabled properly
    for _, job in df.iterrows():
        if is_job_enabled(job):
            enabled_jobs += 1
        else:
            disabled_jobs += 1
    
    recurring_jobs, scheduled_jobs = categorize_jobs(df)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Jobs", total_jobs)
    with col2:
        st.metric("Enabled", enabled_jobs, delta=f"{(enabled_jobs/total_jobs*100):.1f}%")
    with col3:
        st.metric("Disabled", disabled_jobs, delta=f"{(disabled_jobs/total_jobs*100):.1f}%")
    with col4:
        st.metric("Recurring", len(recurring_jobs))
    with col5:
        st.metric("Scheduled", len(scheduled_jobs))



@st.cache_data
def getJobs(atomId, label):
    """Fetch jobs from API and display both table and timeline views"""
    r = requests.get('https://api.qa.trellis.arizona.edu/ws/rest/v1/util/getScheduledJobs/' + atomId) 

    st.header(f"📋 {label}")
    
    if len(r.content) > 5:
        # Create DataFrame
        df = pd.DataFrame.from_dict(r.json())
        
        # Show statistics dashboard
        show_job_statistics(df)
        st.write("---")
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["📊 Timeline View", "📋 Table View", "🔄 Recurring Jobs"])
        
        with tab1:
            st.write("*All times displayed in Mountain Standard Time (MST)*")
            
            # Categorize jobs
            recurring_jobs, scheduled_jobs = categorize_jobs(df)
            
            # Timeline for scheduled jobs
            if scheduled_jobs:
                create_timeline_view(scheduled_jobs, "Scheduled")
            else:
                st.info("No scheduled jobs found")
        
        with tab2:
            # Original table view
            st.subheader("Complete Job Table")
            st.dataframe(
                data=df.style.applymap(color_enabled, subset=['enabled']), 
                column_order=('Name','enabled','id','hours','minutes','daysOfWeek','daysOfMonth','months','years','cron'), 
                use_container_width=True, 
                height=600
            )
        
        with tab3:
            # Recurring jobs timeline view
            if recurring_jobs:
                create_recurring_timeline_view(recurring_jobs)
                
                with st.expander("📋 Recurring Jobs Table View"):
                    recurring_df = pd.DataFrame(recurring_jobs)
                    st.dataframe(
                        data=recurring_df.style.applymap(color_enabled, subset=['enabled']),
                        column_order=('Name','enabled','hours','minutes','cron'),
                        use_container_width=True,
                        height=400
                    )
            else:
                st.info("No recurring jobs found")

    else:
        st.warning('⚠️ No jobs scheduled')

    return df if len(r.content) > 5 else pd.DataFrame()

# Streamlit App Layout
st.set_page_config(page_title="Boomi Job Scheduler", page_icon="⚙️", layout="wide")

st.title("⚙️ Boomi Scheduled Jobs Dashboard")
st.sidebar.title('🎛️ Environment Controls')

# Environment buttons
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.sidebar.button('🏭 Production', type="primary", use_container_width=True):
        st.session_state.selected_env = 'prod'

with col2:
    if st.sidebar.button('🧪 QA', type="secondary", use_container_width=True):
        st.session_state.selected_env = 'qa'

if st.sidebar.button('🏖️ Sandbox', type="secondary", use_container_width=True):
    st.session_state.selected_env = 'sandbox'

st.sidebar.write("---")
if st.sidebar.button('🗑️ Clear Cache', help="Clear cached API responses"):
    clear_cache()
    st.sidebar.success("Cache cleared!")

# Help section
with st.sidebar.expander("ℹ️ Help & Info"):
    st.write("""
    **Timeline View**: Shows job execution times in MST
    **Table View**: Original detailed job table
    **Recurring Jobs**: High-frequency jobs and continuous processes
    
    **Status Indicators**:
    - 🟢 Enabled jobs
    - 🔴 Disabled jobs
    
    **Time Format**: 12-hour format (AM/PM) in MST
    """)

# Main content area - Display jobs based on selected environment
if 'selected_env' not in st.session_state:
    st.session_state.selected_env = None

if st.session_state.selected_env == 'prod':
    getJobs('3d78acc2-9f2b-41ff-bbfd-a3f2ed30c89e', 'Production Molecule')
elif st.session_state.selected_env == 'qa':
    getJobs('58e8640c-7dcd-44fc-8308-a1f0239fc789', 'QA Atom')
elif st.session_state.selected_env == 'sandbox':
    getJobs('4e7219c4-fb66-40b5-ab23-0a5c9a32b5b1', 'Sandbox Atom')
else:
    st.info("👆 Select an environment from the sidebar to view scheduled jobs")
    
    # Show sample from CSV if available
    try:
        sample_df = pd.read_csv('boomijobschedule.csv')
        if not sample_df.empty:
            st.subheader("📄 Sample Data Preview")
            show_job_statistics(sample_df)
            
            with st.expander("View Sample Jobs"):
                st.dataframe(sample_df.head(10), use_container_width=True)
    except:
        pass
