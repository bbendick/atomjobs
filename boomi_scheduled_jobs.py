import streamlit as st
import pandas as pd
import requests

def color_enabled(val):
    color = 'green' if val=='true' else 'yellow' if val==False else 'red'
    return f'background-color: {color}'

@st.cache_resource
def getJobs(atomId):
    r = requests.get('https://api.qa.trellis.arizona.edu/ws/rest/v1/util/getScheduledJobs/' + atomId) 
    
    if len(r.content) > 5:
        # Create a database session object that points to the URL.
        df = pd.DataFrame.from_dict(r.json())
        st.dataframe(data=df.style.applymap(color_enabled, subset=['enabled']), column_order=('Name','enabled','hours','minutes','daysOfWeek','daysOfMonth','months','years','cron'), use_container_width=True, height=None)

    else:
        st.text('No jobs scheduled')

    return

st.sidebar.title('PAT Boomi - Scheduled Jobs')
st.sidebar.button('prod-trellis-molecule', on_click=getJobs, args=['eea33c78-01ad-4ebb-a511-b9c8bd0ea16a'])
st.sidebar.button('prod-trellis-atom', on_click=getJobs, args=['cdcca9c9-0797-4934-9b83-6e127385ef7f'])
st.sidebar.button('nonprod-qa-atom', on_click=getJobs, args=['81b83d93-cdcc-4801-ad79-d3557295b960'])
st.sidebar.button('nonprod-qa-molecule', on_click=getJobs, args=['76a40e65-b51a-4378-a48f-8ff4f7a90674'])
