import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import re
from collections import defaultdict
import pytz

def color_enabled(val):
    color = 'green' if val=='true' else 'yellow' if val==False else 'red'
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
        cols = st.columns(min(len(jobs_at_time), 4))
        
        for idx, job in enumerate(jobs_at_time):
            col_idx = idx % 4
            with cols[col_idx]:
                status_color = "🟢" if job['enabled'] else "🔴"
                job_name = job['Name'][:30] + "..." if len(job['Name']) > 30 else job['Name']
                # Add full name as tooltip using title attribute
                full_name = job['Name']
                st.markdown(f'<div title="{full_name}">{status_color} {job_name}</div>', unsafe_allow_html=True)
        
        st.write("---")

def create_recurring_timeline_view(jobs):
    """Create timeline visualization for recurring jobs"""
    if not jobs:
        return
    
    st.subheader("Recurring/Continuous Jobs (MST)")
    st.write("*Jobs that run frequently (>8 times/day or with step intervals)*")
    
    # Group recurring jobs by their pattern
    pattern_groups = defaultdict(list)
    
    for job in jobs:
        # Group by hour pattern for recurring jobs
        hours_str = str(job.get('hours', '*'))
        minutes_str = str(job.get('minutes', '0'))
        pattern = f"{hours_str} (every {minutes_str} min)" if '/' in minutes_str else f"Hours: {hours_str}"
        pattern_groups[pattern].append(job)
    
    # Sort patterns
    for pattern in sorted(pattern_groups.keys()):
        jobs_in_pattern = pattern_groups[pattern]
        
        st.write(f"**{pattern}**")
        
        # Create columns for job status boxes
        cols = st.columns(min(len(jobs_in_pattern), 3))
        
        for idx, job in enumerate(jobs_in_pattern):
            col_idx = idx % 3
            with cols[col_idx]:
                status_color = "🟢" if job['enabled'] else "🔴"
                job_name = job['Name'][:40] + "..." if len(job['Name']) > 40 else job['Name']
                # Add full name as tooltip
                full_name = job['Name']
                st.markdown(f'<div title="{full_name}">{status_color} {job_name}</div>', unsafe_allow_html=True)
        
        st.write("---")

def show_job_statistics(df):
    """Display job statistics dashboard"""
    total_jobs = len(df)
    enabled_jobs = len(df[df['enabled'] == True])
    disabled_jobs = total_jobs - enabled_jobs
    
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
