import streamlit as st
import pandas as pd
import requests

def color_enabled(val):
    color = 'green' if val=='true' else 'yellow' if val==False else 'red'
    return f'background-color: {color}'


def clear_cache():
    st.cache_data.clear()

@st.cache_data
def getJobs(atomId, label):
    r = requests.get('https://api.qa.trellis.arizona.edu/ws/rest/v1/util/getScheduledJobs/' + atomId) 

    st.text(label)
    
    if len(r.content) > 5:
        # Create a database session object that points to the URL.
        df = pd.DataFrame.from_dict(r.json())
        st.dataframe(data=df.style.applymap(color_enabled, subset=['enabled']), column_order=('Name','enabled','id','hours','minutes','daysOfWeek','daysOfMonth','months','years','cron'), use_container_width=True, height=None)

    else:
        st.text('No jobs scheduled')

    return

st.sidebar.title('Boomi - Scheduled Jobs')
st.sidebar.button('prod-trellis-molecule', on_click=getJobs, type="primary", args=['3d78acc2-9f2b-41ff-bbfd-a3f2ed30c89e', 'Prod Molecule'])
st.sidebar.button('nonprod-qa-molecule', on_click=getJobs, type="primary", args=['76a40e65-b51a-4378-a48f-8ff4f7a90674', 'QA Molecule'])
st.sidebar.button('nonprod-qa-atom', on_click=getJobs, type="primary", args=['208de5f1-9e58-4eb6-ad4f-9d778af8ac2c', 'QA Atom'])
st.sidebar.button('sandbox-molecule', on_click=getJobs, type="primary", args=['c0ce5484-2ade-4689-9fa1-ce1304d8cdd1', 'Sandbox Molecule'])
st.sidebar.button('Clear Cache', on_click=clear_cache)

