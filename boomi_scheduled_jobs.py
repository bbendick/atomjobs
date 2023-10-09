import streamlit as st
import pandas as pd
import numpy as np
import requests
from cron_descriptor import get_description, ExpressionDescriptor


#prod-trellis-molecule: eea33c78-01ad-4ebb-a511-b9c8bd0ea16a
#prod-trellis-atom: cdcca9c9-0797-4934-9b83-6e127385ef7f
#nonprod-qa-atom: 81b83d93-cdcc-4801-ad79-d3557295b960
#nonprod-qa-molecule: 76a40e65-b51a-4378-a48f-8ff4f7a90674

def color_enabled(val):
    color = 'green' if val=='true' else 'yellow' if val==False else 'red'
    return f'background-color: {color}'

@st.cache_resource
def getJobs(atomId):
    r = requests.get('https://api.qa.trellis.arizona.edu/ws/rest/v1/util/getScheduledJobs/' + atomId) 
    
    if len(r.content) > 5:
        # Create a database session object that points to the URL.
        df = pd.DataFrame.from_dict(r.json())
        #st.table(df)
        st.dataframe(data=df.style.applymap(color_enabled, subset=['enabled']), column_order=('Name','enabled','minutes','hours,','daysOfWeek','daysOfMonth','months','years','cron'), use_container_width=True, height=None)

        ##st.dataframe(df.style.applymap(color_enabled, subset=['enabled']))


    else:
        st.text('No jobs scheduled')

    return

st.sidebar.title('Boomi - Scheduled Jobs')
st.sidebar.button('prod-trellis-molecule', on_click=getJobs, args=['eea33c78-01ad-4ebb-a511-b9c8bd0ea16a'])
st.sidebar.button('prod-trellis-atom', on_click=getJobs, args=['cdcca9c9-0797-4934-9b83-6e127385ef7f'])
st.sidebar.button('nonprod-qa-atom', on_click=getJobs, args=['81b83d93-cdcc-4801-ad79-d3557295b960'])
st.sidebar.button('nonprod-qa-molecule', on_click=getJobs, args=['76a40e65-b51a-4378-a48f-8ff4f7a90674'])

#r = getJobs('81b83d93-cdcc-4801-ad79-d3557295b960')

#if r:

    #df = pd.DataFrame.from_dict(r.json())
#
    #st.table(df)


